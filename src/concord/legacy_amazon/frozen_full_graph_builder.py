"""Independent frozen five-view sparse retrieval graph builder for Modal.

All candidate products are bounded with sparse_dot_topn.  MODEL_SELECT truth is
not opened until the candidate graph plus manifests are written and hashed.
"""
from __future__ import annotations
import gc, hashlib, json, os, sqlite3, time, unicodedata
from pathlib import Path
import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import psutil
import scipy.sparse as sp
from sklearn.feature_extraction.text import TfidfVectorizer
from sparse_dot_topn import sp_matmul_topn

MOUNT=Path('/volume'); INPUT=MOUNT/'input'; OUT=MOUNT/'output'; COUNTRIES=('US','India'); SENTINEL=999
K={'name':5,'compact':5,'address':5,'combined':10,'reverse':8}; SEED=0; FIT_CAP=3_000_000; CHUNK=250_000

def fold(x): return ''.join(c for c in unicodedata.normalize('NFKD',str(x)) if not unicodedata.combining(c)).casefold() if x is not None else ''
def sha_file(path):
 h=hashlib.sha256()
 with path.open('rb') as f:
  for b in iter(lambda:f.read(8*1024*1024),b''): h.update(b)
 return h.hexdigest()
def commit(volume): volume.commit()
def vec(view):
 base=dict(min_df=2,max_df=.05,sublinear_tf=True,dtype=np.float32,lowercase=False,norm='l2',use_idf=True,smooth_idf=True)
 if view=='name': return TfidfVectorizer(analyzer='char_wb',ngram_range=(3,3),**base)
 if view=='compact': return TfidfVectorizer(analyzer='char',ngram_range=(3,3),**base)
 return TfidfVectorizer(analyzer='word',token_pattern=r'[a-z0-9]+',**base)
def write_json(x,p): p.parent.mkdir(parents=True,exist_ok=True); p.write_text(json.dumps(x,indent=2,sort_keys=True)+'\n')

def load_reference(country):
 ids=set()
 with (INPUT/'manifests/reference_query_ids.csv').open(newline='',encoding='utf-8') as f:
  for r in pd.read_csv(f,usecols=['country','s1_id'],chunksize=500000,dtype=str): ids.update(r.loc[r.country==country,'s1_id'])
 rows=[]
 for x in pd.read_csv(INPUT/'train/train_source1.tsv',sep='\t',usecols=['entity_id','business_name','business_address','country'],chunksize=250000,dtype=str,keep_default_na=False):
  z=x[x.entity_id.isin(ids)]
  if len(z):
   z=z.assign(name=z.business_name.map(fold),address=z.business_address.map(fold)).rename(columns={'entity_id':'s1_id'})
   rows.extend(z[['s1_id','country','name','address']].to_dict('records'))
 if len(rows)!=len(ids): raise RuntimeError(f'reference materialization mismatch {country}: {len(rows)} != {len(ids)}')
 return rows

def load_targets(country):
 rows=[]; counts={}
 for source in (2,3):
  n=0
  for x in pd.read_csv(INPUT/f'train/train_source{source}.tsv',sep='\t',usecols=['entity_id','business_name','business_address','country'],chunksize=250000,dtype=str,keep_default_na=False):
   z=x[x.country==country]
   if len(z):
    z=z.assign(name=z.business_name.map(fold),address=z.business_address.map(fold),source=source).rename(columns={'entity_id':'target_id'})
    rows.extend(z[['target_id','country','name','address','source']].to_dict('records')); n+=len(z)
  counts[f'S{source}']=n
 return rows,counts

def fit_transform(q,t,view,country,volume):
 field='name' if view in ('name','compact') else 'address'
 qa=[r[field].replace(' ','') if view=='compact' else r[field] for r in q]; ta=[r[field].replace(' ','') if view=='compact' else r[field] for r in t]
 ids=np.array(['q:'+r['s1_id'] for r in q]+['t:'+r['target_id'] for r in t],dtype=object); text=qa+ta
 rng=np.random.default_rng(SEED); selected=np.arange(len(text)) if len(text)<=FIT_CAP else np.sort(rng.choice(len(text),size=FIT_CAP,replace=False))
 sample=OUT/'vectorizer_samples'/f'{country}_{view}.txt'; sample.parent.mkdir(parents=True,exist_ok=True); sample.write_text('\n'.join(ids[selected])+'\n'); commit(volume)
 v=vec(view); v.fit([text[int(i)] for i in selected]); qm=v.transform(qa).astype(np.float32); tm=v.transform(ta).astype(np.float32)
 return qm,tm,{'view':view,'vocabulary':len(v.vocabulary_),'sample_path':str(sample.relative_to(MOUNT)),'sample_sha256':sha_file(sample),'shape_q':list(qm.shape),'shape_t':list(tm.shape),'nnz_q':int(qm.nnz),'nnz_t':int(tm.nnz)}

def retrieve(view,q,t,Q,T,country,volume):
 base=OUT/'checkpoints'/country/view; base.mkdir(parents=True,exist_ok=True); TT=T.T.tocsr(); items=[]; began=time.perf_counter()
 for start in range(0,Q.shape[0],CHUNK):
  dest=base/f'chunk_{start:09d}.parquet'
  if dest.exists(): continue
  C=sp_matmul_topn(Q[start:start+CHUNK],TT,top_n=K[view],threshold=0.0,sort=True,n_threads=32).tocoo(); qi=C.row.astype(np.int64)+start; ti=C.col.astype(np.int64); score=C.data.astype(np.float32); order=np.lexsort((-score,qi)); qi,ti,score=qi[order],ti[order],score[order]
  starts=np.r_[0,np.flatnonzero(np.diff(qi))+1] if len(qi) else np.empty(0,np.int64); rank=(np.arange(len(qi))-np.repeat(starts,np.diff(np.r_[starts,len(qi)]))).astype(np.int16) if len(qi) else np.empty(0,np.int16)
  if view=='reverse':
   s1=np.array([t[int(i)]['target_id'] for i in qi],dtype=object); target=np.array([q[int(i)]['s1_id'] for i in ti],dtype=object)
   # Reverse input is target queries × S1 targets: flip output to canonical s1,target.
   s1,target=target,s1
  else:
   s1=np.array([q[int(i)]['s1_id'] for i in qi],dtype=object); target=np.array([t[int(i)]['target_id'] for i in ti],dtype=object)
  col='combined' if view=='reverse' else view
  frame=pd.DataFrame({'s1_id':s1,'target_id':target,f'{col}_cosine':score,f'{view}_rank':rank})
  frame.to_parquet(dest,index=False); commit(volume); items.append({'chunk':start,'pairs':len(frame),'seconds':time.perf_counter()-began})
  del C,frame
 return items

def union_country(country,volume):
 # DuckDB performs disk-backed outer joins; no unrestricted similarity matrix is formed.
 import duckdb
 root=OUT/'checkpoints'/country; files={v:str(root/v/'*.parquet') for v in K}; dest=OUT/'candidate_graph'/f'{country}.parquet'; dest.parent.mkdir(parents=True,exist_ok=True)
 sql=f"""COPY (
 WITH n AS (SELECT s1_id,target_id,name_cosine,name_rank FROM read_parquet('{files['name']}')),
 c AS (SELECT s1_id,target_id,compact_cosine,compact_rank FROM read_parquet('{files['compact']}')),
 a AS (SELECT s1_id,target_id,address_cosine,address_rank FROM read_parquet('{files['address']}')),
 x AS (SELECT s1_id,target_id,combined_cosine,combined_rank FROM read_parquet('{files['combined']}')),
 r AS (SELECT s1_id,target_id,combined_cosine AS reverse_combined_cosine,reverse_rank FROM read_parquet('{files['reverse']}'))
 SELECT coalesce(n.s1_id,c.s1_id,a.s1_id,x.s1_id,r.s1_id) s1_id, coalesce(n.target_id,c.target_id,a.target_id,x.target_id,r.target_id) target_id,
 substr(coalesce(n.target_id,c.target_id,a.target_id,x.target_id,r.target_id),1,2) AS "source", '{country}' AS country,
 coalesce(name_cosine,0)::FLOAT name_cosine,coalesce(compact_cosine,0)::FLOAT compact_name_cosine,coalesce(address_cosine,0)::FLOAT address_cosine,coalesce(combined_cosine,reverse_combined_cosine,0)::FLOAT combined_cosine,
 coalesce(name_rank,{SENTINEL})::SMALLINT name_rank,coalesce(compact_rank,{SENTINEL})::SMALLINT compact_name_rank,coalesce(address_rank,{SENTINEL})::SMALLINT address_rank,coalesce(combined_rank,{SENTINEL})::SMALLINT combined_rank,coalesce(reverse_rank,{SENTINEL})::SMALLINT reverse_rank,
 ((name_rank IS NOT NULL)::INTEGER + 2*(compact_rank IS NOT NULL)::INTEGER + 4*(address_rank IS NOT NULL)::INTEGER + 8*(combined_rank IS NOT NULL)::INTEGER + 16*(reverse_rank IS NOT NULL)::INTEGER)::SMALLINT retrieval_view_mask
 FROM n FULL OUTER JOIN c USING(s1_id,target_id) FULL OUTER JOIN a USING(s1_id,target_id) FULL OUTER JOIN x USING(s1_id,target_id) FULL OUTER JOIN r USING(s1_id,target_id)
 ORDER BY s1_id,target_id) TO '{dest}' (FORMAT PARQUET, COMPRESSION ZSTD)"""
 duckdb.connect().execute(sql); commit(volume); return dest

def verify_inputs():
 manifests={name:json.loads((INPUT/'manifests'/name).read_text()) for name in ('reference_query_manifest.json','target_manifest.json','vectorizer_manifest.json')}
 ref=manifests['reference_query_manifest.json']
 if sha_file(INPUT/'manifests/reference_query_ids.csv') != ref['reference_query_ids_sha256']: raise RuntimeError('reference_query_ids.csv checksum mismatch')
 expected={item['country']:item['total_reference_s1'] for item in ref['countries']}
 targets=manifests['target_manifest.json']['countries']
 for country in COUNTRIES:
  if expected[country] <= 0 or sum(targets[country].values()) <= 0: raise RuntimeError(f'invalid frozen manifest for {country}')
 return {'manifest_sha256':{name:sha_file(INPUT/'manifests'/name) for name in manifests},'reference_query_ids_sha256':sha_file(INPUT/'manifests/reference_query_ids.csv')}

def post_freeze_evaluate(graphs, freeze, volume):
 # This is the first and only point at which MODEL_SELECT metadata and truth are read.
 db=sqlite3.connect(INPUT/'manifests/splits.sqlite')
 split=pd.read_sql_query("SELECT s1_id, country FROM splits WHERE split='MODEL_SELECT'",db,dtype={'s1_id':'string','country':'string'}); db.close()
 if len(split)!=15113: raise RuntimeError(f'MODEL_SELECT count mismatch: {len(split)} != 15113')
 allowed=set(split.s1_id.astype(str))
 truth=pd.read_csv(INPUT/'evaluation/model_select_truth_links.tsv',sep='\t',dtype=str)
 truth=truth[truth.s1_id.isin(allowed)][['s1_id','target_id']].drop_duplicates()
 if len(truth)!=52358: raise RuntimeError(f'MODEL_SELECT truth count mismatch: {len(truth)} != 52358')
 import duckdb
 con=duckdb.connect(); con.register('eval_split',split); con.register('truth',truth)
 glob=', '.join("'"+str(p)+"'" for p in graphs)
 con.execute(f"CREATE TEMP VIEW candidates AS SELECT g.* FROM read_parquet([{glob}]) g JOIN eval_split e USING(s1_id)")
 con.execute("CREATE TEMP VIEW candidate_pairs AS SELECT DISTINCT s1_id,target_id,retrieval_view_mask,country FROM candidates")
 def metrics(where='TRUE'):
  prefix=f'WHERE {where}' if where!='TRUE' else ''
  counts=con.execute(f"SELECT e.s1_id,e.country,coalesce(count(p.target_id),0)::BIGINT candidates FROM eval_split e LEFT JOIN (SELECT * FROM candidate_pairs {prefix}) p USING(s1_id) GROUP BY e.s1_id,e.country").fetchdf()
  hits=con.execute(f"SELECT t.s1_id,t.target_id,e.country FROM truth t JOIN eval_split e USING(s1_id) JOIN (SELECT s1_id,target_id FROM candidate_pairs {prefix}) p USING(s1_id,target_id)").fetchdf()
  truth_counts=truth.groupby('s1_id').size().rename('truth').reset_index()
  hit_counts=hits.groupby('s1_id').size().rename('hit').reset_index()
  per=split.merge(truth_counts,on='s1_id',how='left').merge(hit_counts,on='s1_id',how='left').merge(counts,on=['s1_id','country'],how='left').fillna({'truth':0,'hit':0,'candidates':0})
  # Frozen qualification oracle is the established macro F0.5 transform of
  # per-S1 truth recall; candidate density is reported as a separate gate.
  recall=np.divide(per.hit,per.truth,out=np.ones(len(per),dtype=float),where=per.truth.to_numpy()!=0)
  per['f05']=np.where(per.truth==0,1.0,np.where(recall>0,(1.25*recall)/(.25+recall),0.0))
  overall={'oracle':float(per.f05.mean()),'truth_recall':float(per.hit.sum()/len(truth)),'all_truth_s1':float((per.hit==per.truth).mean()),'candidate_pairs':int(per.candidates.sum()),'mean_candidates':float(per.candidates.mean()),'p50':float(per.candidates.quantile(.5)),'p90':float(per.candidates.quantile(.9)),'p99':float(per.candidates.quantile(.99)),'p999':float(per.candidates.quantile(.999)),'max':int(per.candidates.max()),'hits':int(per.hit.sum()),'country_oracle':{c:float(per.loc[per.country==c,'f05'].mean()) for c in COUNTRIES}}
  return overall,per,hits
 full,per,hits=metrics(); without,_,without_hits=metrics('(retrieval_view_mask & 16) = 0')
 reverse_only=len(set(map(tuple,hits[['s1_id','target_id']].to_numpy()))-set(map(tuple,without_hits[['s1_id','target_id']].to_numpy())))
 reverse_pairs=full['candidate_pairs']-without['candidate_pairs']
 result={'status':'COMPLETE','full':full,'oracle_without_reverse':without['oracle'],'reverse_only_truths':int(reverse_only),'reverse_added_pairs':int(reverse_pairs),'model_select_s1':int(len(split)),'truth_links':int(len(truth)),'labels_accessed_after_freeze':True,'peak_rss_mib':psutil.Process().memory_info().rss/2**20}
 write_json(result,OUT/'full_result.json'); commit(volume); return result

def run(volume):
 OUT.mkdir(parents=True,exist_ok=True); started=time.time(); runtime={'countries':{},'started':started}; vector={}; targets={}
 integrity=verify_inputs()
 # No truth file is opened in this phase.
 for country in COUNTRIES:
  t0=time.time(); q=load_reference(country); t,counts=load_targets(country); targets[country]=counts
  Qn,Tn,mn=fit_transform(q,t,'name',country,volume); Qc,Tc,mc=fit_transform(q,t,'compact',country,volume); Qa,Ta,ma=fit_transform(q,t,'address',country,volume)
  Qx=sp.hstack([Qn.multiply(np.float32(np.sqrt(.5))),Qa.multiply(np.float32(np.sqrt(.5)))]).tocsr(); Tx=sp.hstack([Tn.multiply(np.float32(np.sqrt(.5))),Ta.multiply(np.float32(np.sqrt(.5)))]).tocsr()
  stages={v:retrieve(v,q,t,A,B,country,volume) for v,A,B in [('name',Qn,Tn),('compact',Qc,Tc),('address',Qa,Ta),('combined',Qx,Tx),('reverse',Tx,Qx)]}
  graph=union_country(country,volume); runtime['countries'][country]={'queries':len(q),'targets':len(t),'target_sources':counts,'stages':stages,'graph':str(graph.relative_to(MOUNT)),'seconds':time.time()-t0}; vector[country]=[mn,mc,ma]
  del q,t,Qn,Tn,Qc,Tc,Qa,Ta,Qx,Tx; gc.collect(); commit(volume)
 # Graph freeze: hashes and all label-free provenance are written before truth is opened.
 graphs=[OUT/'candidate_graph'/f'{c}.parquet' for c in COUNTRIES]; freeze={'input_integrity':integrity,'frozen_builder_sha256':sha_file(Path(__file__)),'vectorizer':vector,'candidate_graph_sha256':{p.name:sha_file(p) for p in graphs},'candidate_ordering':'country,s1_id,target_id ascending','model_select_truth_accessed':False,'targets':targets}; write_json(freeze,OUT/'freeze_manifest.json'); commit(volume)
 evaluated=post_freeze_evaluate(graphs,freeze,volume); runtime['ended']=time.time(); runtime['total_seconds']=runtime['ended']-started; write_json(runtime,OUT/'runtime.json'); commit(volume)
 return {'status':evaluated['status'],'runtime':runtime,'freeze':freeze,'evaluation':evaluated}
