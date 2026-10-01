"""Exact four-feature generator from the accepted ASMI cross-script qualifier.

The feature bodies intentionally preserve the qualifying implementation's
empty-value behavior, lowercasing, Unicode script selection, trigram/token
sets, RapidFuzz calls, and float32 conversion.
"""

import re
import unicodedata

import numpy as np
import unidecode
from rapidfuzz import fuzz


QUALIFIER_SOURCE_SHA256 = "53f07f5645a1cad132aa6761b10bae49ba767ddc479945d8a89804e6c1175565"


def get_script(text):
    if not isinstance(text, str) or not text: return 'UNKNOWN'
    counts = {}
    for char in text:
        if char.isalpha():
            try:
                script = unicodedata.name(char, '').split()[0]
                counts[script] = counts.get(script, 0) + 1
            except:
                pass
    if not counts: return 'UNKNOWN'
    return max(counts.items(), key=lambda x: x[1])[0]


def tri(value):
    if not isinstance(value, str): return frozenset()
    return frozenset(value[i:i+3] for i in range(max(0, len(value)-2)))


def toks(value):
    if not isinstance(value, str): return frozenset()
    return frozenset(re.findall(r'[a-z0-9]+', value))


def jaccard(a, b):
    if not a and not b: return 0.0
    u = len(a | b)
    return len(a & b) / u if u else 0.0


def compute_4_features(df, q_map, t_map):
    f1, f2, f3, f4 = [], [], [], []
    for s1, tid in zip(df['s1_id'], df['target_id']):
        q = q_map.get(s1, {"business_name": "", "business_address": ""})
        t = t_map.get(tid, {"business_name": "", "business_address": ""})
        
        qn = str(q['business_name']) if q['business_name'] else ""
        tn = str(t['business_name']) if t['business_name'] else ""
        qa = str(q['business_address']) if q['business_address'] else ""
        ta = str(t['business_address']) if t['business_address'] else ""
        
        qn_trans = unidecode.unidecode(qn).lower()
        tn_trans = unidecode.unidecode(tn).lower()
        qa_trans = unidecode.unidecode(qa).lower()
        ta_trans = unidecode.unidecode(ta).lower()
        
        # 1. transliterated-name char-ngram similarity
        f1.append(jaccard(tri(qn_trans), tri(tn_trans)))
        
        # 2. original-vs-transliterated maximum name similarity
        if not qn and not tn:
            f2.append(0.0)
        else:
            s_oo = fuzz.ratio(qn.lower(), tn.lower()) / 100.0
            s_ot = fuzz.ratio(qn.lower(), tn_trans) / 100.0
            s_to = fuzz.ratio(qn_trans, tn.lower()) / 100.0
            s_tt = fuzz.ratio(qn_trans, tn_trans) / 100.0
            f2.append(max(s_oo, s_ot, s_to, s_tt))
            
        # 3. cross-script disjoint indicator
        qs = get_script(qn)
        ts = get_script(tn)
        f3.append(1.0 if qs != ts and qs != 'UNKNOWN' and ts != 'UNKNOWN' else 0.0)
        
        # 4. transliterated-address token overlap
        f4.append(jaccard(toks(qa_trans), toks(ta_trans)))
        
    return np.array(f1, dtype=np.float32), np.array(f2, dtype=np.float32), np.array(f3, dtype=np.float32), np.array(f4, dtype=np.float32)
