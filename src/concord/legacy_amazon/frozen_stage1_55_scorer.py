"""Frozen 55-feature Stage-1 scorer for the immutable Ayan candidate graph."""
from __future__ import annotations

import gc
import hashlib
import json
import math
import os
import re
import sqlite3
import time
from collections import defaultdict
from multiprocessing import get_context
from pathlib import Path

import duckdb
import joblib
import lightgbm as lgb
import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import psutil
from rapidfuzz import fuzz
from rapidfuzz.distance import JaroWinkler

MOUNT = Path("/volume")
INPUT = MOUNT / "input"
RETRIEVAL = MOUNT / "output"
OUT = MOUNT / "scorer" / "stage1_55"
CODE = INPUT / "code"
SEED = 42
EDGE_CHUNK = 500_000
WORKERS = 32
CHALLENGER = 0.9333566962695244
CHALLENGER_COUNTRY = {"US": 0.9509180862359731, "India": 0.9071651540627228}

FEATURES = [
 "name_nonempty_exact_match","name_normalized_string_ratio","name_jaro_winkler","name_token_sort_ratio","name_token_set_ratio","name_partial_ratio","name_char_trigram_jaccard","name_token_jaccard","name_query_token_coverage","name_target_token_coverage",
 "address_nonempty_exact_match","address_normalized_string_ratio","address_token_sort_ratio","address_token_set_ratio","address_char_trigram_jaccard","address_token_jaccard","address_query_token_coverage","address_target_token_coverage",
 "numeric_token_jaccard","numeric_query_coverage","numeric_target_coverage","nonempty_first_number_equality","query_numeric_token_count","target_numeric_token_count",
 "query_name_missing","target_name_missing","query_address_missing","target_address_missing","target_source_is_S2",
 "exact_name_cosine","exact_compact_name_cosine","exact_address_cosine","exact_combined_cosine",
 "name_rank","compact_name_rank","address_rank","combined_rank","reverse_rank",
 "name_query_source_rank","name_query_source_delta_best","name_target_owner_rank","name_target_delta_best","name_target_rival_margin",
 "address_query_source_rank","address_query_source_delta_best","address_target_owner_rank","address_target_delta_best","address_target_rival_margin",
 "combined_query_source_rank","combined_query_source_delta_best","combined_target_owner_rank","combined_target_delta_best","combined_target_rival_margin",
 "candidate_count_within_s1_source","distinct_competing_s1_count_for_target"
]
BASE_FEATURES = FEATURES[:38]
WORD = re.compile(r"\w+", re.UNICODE)
NUM = re.compile(r"\d+")
_G = {}

def sha256(path: Path) -> str:
    h=hashlib.sha256()
    with path.open("rb") as f:
        for b in iter(lambda:f.read(8*1024*1024),b""): h.update(b)
    return h.hexdigest()

def write_json(value, path: Path):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value,indent=2,sort_keys=True)+"\n",encoding="utf-8")

def tri(value: str) -> frozenset[str]:
    return frozenset(value[i:i+3] for i in range(max(0,len(value)-2)))

def rep(name: str, address: str):
    nt=frozenset(WORD.findall(name)); at=frozenset(WORD.findall(address)); nums=tuple(NUM.findall(address)); ns=frozenset(nums)
    return nt,at,tri(name),tri(address),ns,(nums[0] if nums else "")

def overlap(a,b):
    inter=len(a & b); union=len(a | b)
    return inter,(inter/union if union else 0.0),(inter/len(a) if a else 0.0),(inter/len(b) if b else 0.0)

def direct(qname,qaddr,tname,taddr,source,qrep=None,trep=None):
    qn,qa,qtri,qatri,qnums,qfirst=qrep if qrep is not None else rep(qname,qaddr); tn,ta,ttri,tatri,tnums,tfirst=trep if trep is not None else rep(tname,taddr)
    _,nj,nqc,ntc=overlap(qn,tn); _,ntj,_,_=overlap(qtri,ttri)
    _,aj,aqc,atc=overlap(qa,ta); _,atj,_,_=overlap(qatri,tatri)
    _,numj,numqc,numtc=overlap(qnums,tnums)
    nf=[fuzz.ratio(qname,tname)/100.0,JaroWinkler.normalized_similarity(qname,tname),fuzz.token_sort_ratio(qname,tname)/100.0,fuzz.token_set_ratio(qname,tname)/100.0,fuzz.partial_ratio(qname,tname)/100.0] if qname and tname else [0.0]*5
    af=[fuzz.ratio(qaddr,taddr)/100.0,fuzz.token_sort_ratio(qaddr,taddr)/100.0,fuzz.token_set_ratio(qaddr,taddr)/100.0] if qaddr and taddr else [0.0]*3
    return [
      float(bool(qname) and qname==tname),*nf,ntj,nj,nqc,ntc,
      float(bool(qaddr) and qaddr==taddr),*af,atj,aj,aqc,atc,
      numj,numqc,numtc,float(bool(qfirst) and qfirst==tfirst),float(len(qnums)),float(len(tnums)),float(not bool(qname)),float(not bool(tname)),float(not bool(qaddr)),float(not bool(taddr)),float(source=="S2")]

def coord(Q,T,qi,ti):
    return np.asarray(Q[qi].multiply(T[ti]).sum(axis=1)).ravel().astype(np.float32,copy=False)

def _worker(task):
    country,row_group,destination=task; destination=Path(destination)
    if destination.exists(): return {"row_group":row_group,"status":"SKIPPED"}
    began=time.perf_counter(); graph=pq.ParquetFile(_G["graph"]); table=graph.read_row_group(row_group)
    frame=table.to_pandas(); qi=np.fromiter((_G["qmap"][x] for x in frame.s1_id),dtype=np.int64,count=len(frame)); ti=np.fromiter((_G["tmap"][x] for x in frame.target_id),dtype=np.int64,count=len(frame))
    en=coord(_G["Qn"],_G["Tn"],qi,ti); ec=coord(_G["Qc"],_G["Tc"],qi,ti); ea=coord(_G["Qa"],_G["Ta"],qi,ti)
    matrix=np.empty((len(frame),38),dtype=np.float32); qcache={}; tcache={}
    for i,(qix,tix,src) in enumerate(zip(qi,ti,frame.source)):
        qr=_G["q"][int(qix)]; tr=_G["t"][int(tix)]
        if qix not in qcache: qcache[qix]=rep(qr["name"],qr["address"])
        if tix not in tcache: tcache[tix]=rep(tr["name"],tr["address"])
        matrix[i,:29]=direct(qr["name"],qr["address"],tr["name"],tr["address"],src,qcache[qix],tcache[tix])
    matrix[:,29]=en; matrix[:,30]=ec; matrix[:,31]=ea; matrix[:,32]=np.float32(.5)*en+np.float32(.5)*ea
    for j,col in enumerate(("name_rank","compact_name_rank","address_rank","combined_rank","reverse_rank"),start=33): matrix[:,j]=frame[col].to_numpy(np.float32)
    data={"s1_id":frame.s1_id,"target_id":frame.target_id,"country":frame.country,"source":frame.source,"retrieval_view_mask":frame.retrieval_view_mask.to_numpy(np.int16)}
    data.update({name:matrix[:,i] for i,name in enumerate(BASE_FEATURES)})
    destination.parent.mkdir(parents=True,exist_ok=True); pq.write_table(pa.Table.from_pydict(data),destination,compression="zstd",row_group_size=250000)
    return {"row_group":row_group,"rows":len(frame),"seconds":time.perf_counter()-began,"status":"COMPLETE"}

def _fit_matrices(country,q,t,qmap,tmap):
    import sys
    sys.path.insert(0,str(CODE)); import frozen_full_graph_builder as retrieval
    sample=(RETRIEVAL/"vectorizer_samples"/f"{country}_name.txt").read_text(encoding="utf-8").splitlines()
    result=[]; meta=[]
    for view in ("name","compact","address"):
        field="name" if view in ("name","compact") else "address"
        def value(row):
            text=row[field]
            return text.replace(" ","") if view=="compact" else text
        fit=[]
        for sid in sample:
            prefix,eid=sid[:2],sid[2:]
            fit.append(value(q[qmap[eid]]) if prefix=="q:" else value(t[tmap[eid]]))
        vectorizer=retrieval.vec(view); vectorizer.fit(fit)
        Q=vectorizer.transform([value(x) for x in q]).astype(np.float32); T=vectorizer.transform([value(x) for x in t]).astype(np.float32)
        result.extend([Q,T]); meta.append({"view":view,"vocabulary":len(vectorizer.vocabulary_),"sample_sha256":sha256(RETRIEVAL/"vectorizer_samples"/f"{country}_{view}.txt"),"q_shape":list(Q.shape),"t_shape":list(T.shape)})
        del fit,vectorizer; gc.collect()
    return result,meta

def _context_sql(country,base_glob,dest):
    signals=("name","address","combined")
    w1=[]
    for s in signals:
        score=f"exact_{s}_cosine"
        w1 += [f"rank() OVER(PARTITION BY s1_id,source ORDER BY {score} DESC) AS {s}_query_source_rank",f"max({score}) OVER(PARTITION BY s1_id,source) AS {s}_qbest",f"rank() OVER(PARTITION BY target_id ORDER BY {score} DESC) AS {s}_target_owner_rank",f"max({score}) OVER(PARTITION BY target_id) AS {s}_tbest"]
    w2=[]
    for s in signals:
        score=f"exact_{s}_cosine"; w2 += [f"sum(CASE WHEN {score}={s}_tbest THEN 1 ELSE 0 END) OVER(PARTITION BY target_id) AS {s}_topcount",f"max(CASE WHEN {score}<{s}_tbest THEN {score} END) OVER(PARTITION BY target_id) AS {s}_second"]
    context=[]
    for s in signals:
        score=f"exact_{s}_cosine"; context += [f"{s}_query_source_rank::FLOAT AS {s}_query_source_rank",f"({score}-{s}_qbest)::FLOAT AS {s}_query_source_delta_best",f"{s}_target_owner_rank::FLOAT AS {s}_target_owner_rank",f"({score}-{s}_tbest)::FLOAT AS {s}_target_delta_best",f"(CASE WHEN target_count=1 THEN 0 WHEN {score}={s}_tbest AND {s}_topcount=1 THEN {score}-coalesce({s}_second,{score}) ELSE {score}-{s}_tbest END)::FLOAT AS {s}_target_rival_margin"]
    return f"""COPY (WITH b AS (SELECT * FROM read_parquet('{base_glob}')), w1 AS (SELECT *,count(*) OVER(PARTITION BY s1_id,source) candidate_count_within_s1_source,count(*) OVER(PARTITION BY target_id) target_count,{','.join(w1)} FROM b), w2 AS (SELECT *,{','.join(w2)} FROM w1) SELECT s1_id,target_id,country,source,retrieval_view_mask,{','.join(BASE_FEATURES)},{','.join(context)},candidate_count_within_s1_source::FLOAT candidate_count_within_s1_source,target_count::FLOAT distinct_competing_s1_count_for_target FROM w2 ORDER BY s1_id,target_id) TO '{dest}' (FORMAT PARQUET,COMPRESSION ZSTD,ROW_GROUP_SIZE 250000)"""

def generate_country(country,volume):
    import sys
    sys.path.insert(0,str(CODE)); import frozen_full_graph_builder as retrieval
    started=time.time(); q=retrieval.load_reference(country); t,counts=retrieval.load_targets(country); qmap={r["s1_id"]:i for i,r in enumerate(q)}; tmap={r["target_id"]:i for i,r in enumerate(t)}
    mats,meta=_fit_matrices(country,q,t,qmap,tmap); Qn,Tn,Qc,Tc,Qa,Ta=mats
    graph=RETRIEVAL/"candidate_graph"/f"{country}.parquet"; base=OUT/"base_features"/country; base.mkdir(parents=True,exist_ok=True)
    _G.update(q=q,t=t,qmap=qmap,tmap=tmap,Qn=Qn,Tn=Tn,Qc=Qc,Tc=Tc,Qa=Qa,Ta=Ta,graph=str(graph))
    pf=pq.ParquetFile(graph); tasks=[(country,i,str(base/f"part_{i:05d}.parquet")) for i in range(pf.num_row_groups)]
    probe_started=time.perf_counter(); probe=_worker(tasks[0]); probe_seconds=time.perf_counter()-probe_started
    remaining=tasks[1:]
    with get_context("fork").Pool(min(WORKERS,os.cpu_count() or WORKERS)) as pool: rows=list(pool.imap_unordered(_worker,remaining,chunksize=1))
    rows.append(probe); volume.commit()
    exact_direct_seconds=time.time()-started
    dest=OUT/"full_features"/f"{country}.parquet"; dest.parent.mkdir(parents=True,exist_ok=True)
    context_started=time.time(); duckdb.connect().execute(_context_sql(country,str(base/'*.parquet'),str(dest))); volume.commit(); context_seconds=time.time()-context_started
    result={"country":country,"graph_sha256":sha256(graph),"base_rows":sum(int(x.get("rows",0)) for x in rows),"vectorizers":meta,"probe":probe,"probe_seconds":probe_seconds,"exact_direct_seconds":exact_direct_seconds,"context_seconds":context_seconds,"total_seconds":time.time()-started,"peak_rss_mib":psutil.Process().memory_info().rss/2**20,"feature_file":str(dest.relative_to(MOUNT))}
    write_json(result,OUT/f"generation_{country}.json"); volume.commit(); return result

def _load_truth(name):
    return pd.read_csv(INPUT/"evaluation"/name,sep="\t",dtype=str)[["s1_id","target_id"]].drop_duplicates()

def _metric(ids,country,truth,pred):
    ts=defaultdict(set); ps=defaultdict(set)
    for s,t in truth.itertuples(index=False): ts[s].add(t)
    for s,t in pred.itertuples(index=False): ps[s].add(t)
    per=[]; tp=fp=fn=0
    for s in ids:
        a=ts[s]; b=ps[s]; hit=len(a&b); p=(hit/len(b) if b else (1.0 if not a else 0.0)); r=(hit/len(a) if a else 1.0); f=(1.25*p*r/(.25*p+r) if p+r else 0.0); per.append((s,country[s],f,p,r)); tp+=hit; fp+=len(b-a); fn+=len(a-b)
    frame=pd.DataFrame(per,columns=["s1_id","country","f05","precision","recall"])
    return {"macro_f05":float(frame.f05.mean()),"macro_precision":float(frame.precision.mean()),"macro_recall":float(frame.recall.mean()),"tp":tp,"fp":fp,"fn":fn,"countries":{c:float(frame.loc[frame.country==c,"f05"].mean()) for c in ("US","India")},"per_s1":frame}

def _evaluate_thresholds(winners,split,truth,grid):
    ids=split.s1_id.tolist(); country=dict(zip(split.s1_id,split.country)); truth=truth[truth.s1_id.isin(set(ids))]
    out=[]
    for threshold in grid:
        pred=winners[(winners.s1_id.isin(set(ids))) & (winners.score>=threshold)][["s1_id","target_id"]]
        m=_metric(ids,country,truth,pred); out.append({k:v for k,v in m.items() if k!="per_s1"}|{"threshold":float(threshold),"selected_links":len(pred)})
    return out

def train_evaluate(volume):
    started=time.time(); volume.reload(); OUT.mkdir(parents=True,exist_ok=True)
    with sqlite3.connect(INPUT/"manifests"/"splits.sqlite") as db:
        splits=pd.read_sql_query("SELECT s1_id,country,split FROM splits WHERE split IN ('MODEL_TRAIN','THRESHOLD_CALIBRATION','MODEL_SELECT')",db,dtype=str)
    train_truth=_load_truth("model_train_truth_links.tsv"); cal_truth=_load_truth("threshold_calibration_truth_links.tsv")
    con=duckdb.connect(); con.register("splits",splits); con.register("train_truth",train_truth); con.register("cal_truth",cal_truth)
    full_glob=str(OUT/"full_features"/"*.parquet")
    subsets=OUT/"subsets"; subsets.mkdir(exist_ok=True)
    for split,truth_name in (("MODEL_TRAIN","train_truth"),("THRESHOLD_CALIBRATION","cal_truth"),("MODEL_SELECT",None)):
        dest=subsets/f"{split}.parquet"; label=(f",(t.target_id IS NOT NULL)::UTINYINT AS \"label\" FROM read_parquet('{full_glob}') f JOIN splits s USING(s1_id) LEFT JOIN {truth_name} t USING(s1_id,target_id)" if truth_name else f" FROM read_parquet('{full_glob}') f JOIN splits s USING(s1_id)")
        if not dest.exists(): con.execute(f"COPY (SELECT f.*{label} WHERE s.split='{split}' ORDER BY f.s1_id,f.target_id) TO '{dest}' (FORMAT PARQUET,COMPRESSION ZSTD,ROW_GROUP_SIZE 250000)")
    volume.commit()
    train=pd.read_parquet(subsets/"MODEL_TRAIN.parquet"); X=train[FEATURES].to_numpy(np.float32); y=train.label.to_numpy(np.uint8)
    params=dict(objective="binary",n_estimators=600,learning_rate=.05,num_leaves=63,min_child_samples=100,reg_lambda=1.0,subsample=1.0,colsample_bytree=1.0,random_state=SEED,n_jobs=32,verbosity=-1)
    fit_started=time.time(); model=lgb.LGBMClassifier(**params).fit(X,y); joblib.dump(model,OUT/"model.joblib"); model.booster_.save_model(str(OUT/"model.txt"))
    folds=np.fromiter((int.from_bytes(hashlib.blake2b(s.encode(),digest_size=8).digest(),"big")%5 for s in train.s1_id),dtype=np.int8,count=len(train)); oof_models=[]
    for fold in range(5):
        m=lgb.LGBMClassifier(**(params|{"random_state":SEED+fold+1})).fit(X[folds!=fold],y[folds!=fold]); joblib.dump(m,OUT/f"oof_fold_{fold}.joblib"); oof_models.append(m)
    fit_seconds=time.time()-fit_started; del X,y; gc.collect()
    score_dir=OUT/"scores"; score_dir.mkdir(exist_ok=True); score_started=time.time(); split_map=dict(zip(splits.s1_id,splits.split))
    for country in ("US","India"):
        pf=pq.ParquetFile(OUT/"full_features"/f"{country}.parquet")
        for i in range(pf.num_row_groups):
            dest=score_dir/f"{country}_{i:05d}.parquet"
            if dest.exists(): continue
            f=pf.read_row_group(i).to_pandas(); xx=f[FEATURES].to_numpy(np.float32); scores=model.predict_proba(xx)[:,1].astype(np.float32); ss=f.s1_id.map(split_map).fillna("BACKGROUND")
            mask=(ss=="MODEL_TRAIN").to_numpy()
            if mask.any():
                rowfold=np.fromiter((int.from_bytes(hashlib.blake2b(s.encode(),digest_size=8).digest(),"big")%5 for s in f.loc[mask,"s1_id"]),dtype=np.int8,count=int(mask.sum())); pos=np.flatnonzero(mask)
                for fold,m in enumerate(oof_models):
                    use=pos[rowfold==fold]
                    if len(use): scores[use]=m.predict_proba(xx[use])[:,1].astype(np.float32)
            pq.write_table(pa.Table.from_pydict({"s1_id":f.s1_id,"target_id":f.target_id,"country":f.country,"source":f.source,"score":scores,"split":ss}),dest,compression="zstd")
    volume.commit(); scoring_seconds=time.time()-score_started
    winners_path=OUT/"target_winners.parquet"
    if not winners_path.exists(): con.execute(f"COPY (SELECT * EXCLUDE(rn) FROM (SELECT *,row_number() OVER(PARTITION BY target_id ORDER BY score DESC,s1_id ASC) rn FROM read_parquet('{score_dir}/*.parquet')) WHERE rn=1) TO '{winners_path}' (FORMAT PARQUET,COMPRESSION ZSTD)")
    winners=pd.read_parquet(winners_path); cal=splits[splits.split=="THRESHOLD_CALIBRATION"]
    calibration_started=time.time(); results=_evaluate_thresholds(winners,cal,cal_truth,np.round(np.arange(0,1.0001,.005),3)); best=max(results,key=lambda z:(z["macro_f05"],z["threshold"])); optimum=best["macro_f05"]
    higher=[z for z in results if z["threshold"]>best["threshold"] and z["macro_f05"]>=optimum-.0005 and z["fp"]<best["fp"] and z["macro_precision"]>=best["macro_precision"]]
    lower=[z for z in results if z["threshold"]<best["threshold"] and z["macro_f05"]>=optimum-.0005 and z["macro_recall"]>best["macro_recall"] and z["macro_precision"]>=best["macro_precision"]-.001]
    policies={"PRIMARY":best,"PRECISION_CONSERVATIVE":max(higher,key=lambda z:z["threshold"]) if higher else "NOT_QUALIFIED","RECALL_ORIENTED":min(lower,key=lambda z:z["threshold"]) if lower else "NOT_QUALIFIED"}
    write_json(results,OUT/"calibration_results.json"); write_json(policies,OUT/"frozen_threshold_policies.json"); volume.commit(); calibration_seconds=time.time()-calibration_started
    # MODEL_SELECT truth is opened only after policies are frozen and committed.
    select_truth=_load_truth("model_select_truth_links.tsv"); select=splits[splits.split=="MODEL_SELECT"]; selected=winners[(winners.s1_id.isin(set(select.s1_id))) & (winners.score>=best["threshold"])][["s1_id","target_id","country","source","score"]]
    metric=_metric(select.s1_id.tolist(),dict(zip(select.s1_id,select.country)),select_truth,selected[["s1_id","target_id"]]); per=metric.pop("per_s1"); rng=np.random.default_rng(SEED); deltas=per.f05.to_numpy()-CHALLENGER; means=[]
    for _ in range(10000): means.append(float(deltas[rng.integers(0,len(deltas),len(deltas))].mean()))
    ci=np.quantile(means,[.025,.975]); metric.update(threshold=best["threshold"],selected_links=len(selected),empty_predictions=int(len(select)-selected.s1_id.nunique()),empty_fraction=float((len(select)-selected.s1_id.nunique())/len(select)),oracle=.9927924049957166,oracle_actual_gap=float(.9927924049957166-metric["macro_f05"]),challenger=CHALLENGER,paired_mean_delta=float(deltas.mean()),paired_ci_low=float(ci[0]),paired_ci_high=float(ci[1]),country_deltas={c:metric["countries"][c]-CHALLENGER_COUNTRY[c] for c in CHALLENGER_COUNTRY},paired_method="S1 bootstrap of new per-S1 F0.5 minus fixed saved-challenger aggregate; old per-S1 vector was not persisted")
    selected.to_parquet(OUT/"model_select_predictions.parquet",index=False); write_json(metric,OUT/"model_select_metrics.json"); write_json({"draws":10000,"mean":metric["paired_mean_delta"],"ci_low":metric["paired_ci_low"],"ci_high":metric["paired_ci_high"],"method":metric["paired_method"]},OUT/"paired_resampling.json")
    total=time.time()-started; generated=json.loads((OUT/"generation_US.json").read_text()),json.loads((OUT/"generation_India.json").read_text()); feature_seconds=sum(x["exact_direct_seconds"] for x in generated); context_seconds=sum(x["context_seconds"] for x in generated)
    # Projection uses frozen manifest counts only; no TEST record is opened.
    retrieval_seconds=5222.764740943909; test_ratio=(1473092/1784482); scorer_projection=(feature_seconds+context_seconds+fit_seconds+scoring_seconds+calibration_seconds)*test_ratio; projected=retrieval_seconds*test_ratio+scorer_projection+300
    runtime={"exact_cosine_and_direct_seconds":feature_seconds,"context_seconds":context_seconds,"fit_seconds":fit_seconds,"background_scoring_seconds":scoring_seconds,"calibration_seconds":calibration_seconds,"total_seconds":total,"peak_rss_mib":psutil.Process().memory_info().rss/2**20,"projected_test_seconds":projected,"projected_test_with_25pct_margin":1.25*projected}; write_json(runtime,OUT/"runtime.json")
    write_json({"features":FEATURES,"graph_hashes":{"US":sha256(RETRIEVAL/"candidate_graph/US.parquet"),"India":sha256(RETRIEVAL/"candidate_graph/India.parquet")},"model_config":params,"seed_recovery":"DEFAULTED_TO_42_NO_PRIOR_VALUE_FOUND","model_select_truth_accessed_after_threshold_freeze":True,"test_accessed":False,"final_holdout_accessed":False},OUT/"feature_provenance.json")
    authorized=metric["macro_f05"]>=.98 and metric["paired_ci_low"]>0 and all(v>=0 for v in metric["country_deltas"].values())
    result={"status":"COMPLETE","test_production_authorized":authorized,"metric":metric,"policies":policies,"runtime":runtime,"model_train_rows":len(train),"calibration_s1":len(cal),"model_select_s1":len(select),"feature_count":55}; write_json(result,OUT/"qualification_result.json"); volume.commit(); return result
