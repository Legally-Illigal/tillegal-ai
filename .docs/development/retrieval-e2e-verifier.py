"""Verification-only launcher. Production service/adapters unchanged; RPC GET enforced."""
import asyncio
import contextlib
import hashlib
import io
import json
import logging
import math
import os
from pathlib import Path
import runpy
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
os.chdir(ROOT)
os.environ.update(HF_HUB_OFFLINE='1', TRANSFORMERS_OFFLINE='1', HF_DATASETS_OFFLINE='1',
                  PYTHONDONTWRITEBYTECODE='1', HF_HUB_DISABLE_TELEMETRY='1')
logging.disable(logging.CRITICAL)
from src.core.config import load_settings
settings = load_settings().supabase
from postgrest._sync.client import SyncPostgrestClient
import httpx

ALLOW = {'get_sparse_index','get_dense_index','get_retrieval_chunks','get_source_document',
         'search_sparse_legal_chunks','search_legal_chunks'}
trace = []
original_rpc = SyncPostgrestClient.rpc
def readonly_rpc(self, func, params, *args, **kwargs):
    if func not in ALLOW:
        raise RuntimeError('Non-allowlisted RPC blocked')
    trace.append(func)
    params = {k: ('{' + ','.join('"' + str(x).replace('\\','\\\\').replace('"','\\"') + '"' for x in v) + '}')
              if isinstance(v, (list, tuple)) else v for k,v in params.items()}
    return original_rpc(self, func, params, get=True)
SyncPostgrestClient.rpc = readonly_rpc
original_send = httpx.Client.send
def readonly_send(self, request, *args, **kwargs):
    if request.method != 'GET' or '/rpc/' not in request.url.path or request.url.path.rsplit('/',1)[-1] not in ALLOW:
        raise RuntimeError('Non-read-only HTTP request blocked')
    return original_send(self, request, *args, **kwargs)
httpx.Client.send = readonly_send

MODEL = Path.home()/'.cache/huggingface/hub/models--intfloat--multilingual-e5-small/snapshots/614241f622f53c4eeff9890bdc4f31cfecc418b3'
if len(sys.argv)>1 and sys.argv[1]=='--cli-child':
    sys.argv=['scripts/search_legal_chunks.py'] + sys.argv[2:]
    runpy.run_path(str(ROOT/'scripts/search_legal_chunks.py'), run_name='__main__')
    raise SystemExit()

import psycopg
from psycopg.rows import dict_row
from psycopg.conninfo import conninfo_to_dict
from urllib.parse import urlparse
from src.retrieval_bootstrap import create_retrieval_service
from src.applications.tillegal.retrieval.contracts import RetrievalRequest
from src.applications.tillegal.retrieval.hybrid_models import HybridConfig
from src.application.services.vbpl_markdown_indexing_service import tokenize_sparse_text

result={'tests':[], 'rpc_transport':'SDK get=True / HTTP GET only / PostgREST read-only transactions',
        'baseline':'legacy-data-live-evidence.json','model_revision':MODEL.name}
def compact(r):
    return {k:v for k,v in r.items() if k in ('status','mode','query_used','filters','index','warnings','error','fusion','request_id')} | {
      'evidence':[{k:v for k,v in e.items() if k in ('retrieval_chunk_id','source_document_id','document_structure_id',
        'chunk_key','rank','raw_score','score_kind','retrieval_method','content_sha256','hash_check','title',
        'effective_from','effective_to','usage_policy')} for e in r.get('evidence',[])]}
def save():
    (ROOT/'.docs/development/retrieval-e2e-evidence.json').write_text(json.dumps(result,ensure_ascii=False,indent=2,default=str),encoding='utf-8')

try:
 info=conninfo_to_dict(settings.database_url.get_secret_value())
 ref=(urlparse(str(settings.url)).hostname or '').split('.')[0]
 assert info.get('host')==f'db.{ref}.supabase.co' or info.get('user','').endswith('.'+ref)
 result['project_matches_existing_config']=True
 with psycopg.connect(settings.database_url.get_secret_value(),connect_timeout=15,
     options='-c default_transaction_read_only=on -c statement_timeout=45000',row_factory=dict_row) as db:
  db.execute('BEGIN TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY')
  result['sql_read_only']=db.execute("SELECT current_setting('transaction_read_only') AS value").fetchone()['value']
  assert result['sql_read_only']=='on'
  result['indexes']=db.execute("SELECT index_name,status,updated_at FROM public.sparse_indexes WHERE index_name='vbpl-bm25-unicode-v1' UNION ALL SELECT index_name,status,updated_at FROM public.dense_indexes WHERE index_name='vbpl-multilingual-e5-small-v1'").fetchall()
  assert len(result['indexes'])==2 and all(i['status']=='READY' for i in result['indexes'])
  seed=db.execute("SELECT c.id, c.content FROM public.retrieval_chunks c JOIN public.source_documents s ON s.id=c.source_document_id JOIN public.sparse_chunk_documents sd ON sd.retrieval_chunk_id=c.id JOIN public.sparse_indexes i ON i.id=sd.sparse_index_id WHERE i.index_name='vbpl-bm25-unicode-v1' AND sd.status='INDEXED' AND s.usage_policy='EXPERIMENTAL_ONLY' AND (s.effective_from IS NULL OR s.effective_from<=DATE '2026-11-14') AND (s.effective_to IS NULL OR s.effective_to>=DATE '2026-11-14') AND EXISTS(SELECT 1 FROM public.sparse_postings p WHERE p.sparse_chunk_document_id=sd.id) ORDER BY c.id LIMIT 1").fetchone()
  query=' '.join(tokenize_sparse_text(seed['content'])[:8])
  result['seed_chunk_id']=str(seed['id']); result['query']=query
  result['as_of_date']='2026-11-14'; result['allowed_policies']=['EXPERIMENTAL_ONLY']
  result['checkpoint_files_present']=all((MODEL/p).exists() for p in ['model.safetensors','config.json','modules.json','tokenizer.json'])
  cfg=HybridConfig(bm25_candidates=5,dense_candidates=5,rrf_k=60)
  service=create_retrieval_service(settings,dense_model_path=MODEL,hybrid_config=cfg)
  # Warm actual local encoder separately so inference/load does not exhaust service deadline.
  model_ready=False
  try:
   with contextlib.redirect_stdout(io.StringIO()),contextlib.redirect_stderr(io.StringIO()):
    vector=asyncio.run(service._query_embedder.encode_query(query))
   result['encoder']={'dimension':len(vector),'finite':all(math.isfinite(x) for x in vector),'norm':math.sqrt(sum(x*x for x in vector)), 'prefix':'query: ','actual_local_inference':True}
   model_ready=True
  except Exception as e: result['encoder']={'error_type':type(e).__name__,'code':getattr(getattr(e,'detail',None),'code',None)}
  responses={}
  for mode in ['bm25','dense','hybrid']:
   if mode!='bm25' and not model_ready: continue
   for scenario,policies in [('hits',['EXPERIMENTAL_ONLY']),('filter_no_match',['AUDIT_NONEXISTENT_POLICY'])]:
    trace.clear(); started=time.monotonic()
    req=RetrievalRequest(query=query,mode=mode,top_k=5,as_of_date='2026-11-14',allowed_usage_policies=policies)
    response=asyncio.run(service.search(req)); raw=response.model_dump(mode='json')
    item={'id':f'{mode}_{scenario}','kind':'actual_service','response':compact(raw),'rpc_calls':list(trace),'elapsed_seconds':time.monotonic()-started}
    item['expected_status_match']=raw['status']==('OK' if scenario=='hits' else 'NO_MATCH')
    checks=[]
    for e in response.evidence:
     row=db.execute('SELECT content,content_sha256,source_document_id,document_structure_id,metadata FROM public.retrieval_chunks WHERE id=%s',(e.retrieval_chunk_id,)).fetchone()
     checks.append(bool(row and row['content']==e.content and row['content_sha256']==e.content_sha256 and row['source_document_id']==e.source_document_id and row['document_structure_id']==e.document_structure_id and row['metadata']==e.chunk_metadata and hashlib.sha256(e.content.encode()).hexdigest()==e.content_sha256))
    item['sql_hydration_identity_matches']=all(checks)
    result['tests'].append(item); save()
    if scenario=='hits': responses[mode]=response
    print(json.dumps({'test':item['id'],'status':raw['status'],'hits':len(response.evidence)}),flush=True)
  if 'bm25' in responses:
   direct=db.execute('SELECT * FROM public.search_sparse_legal_chunks(%s,%s,%s,%s,%s)',(list(dict.fromkeys(tokenize_sparse_text(query))),'vbpl-bm25-unicode-v1',5,'2026-11-14',['EXPERIMENTAL_ONLY'])).fetchall()
   result['bm25_sql_compare']=[(str(x['retrieval_chunk_id']),x['score']) for x in direct]==[(str(x.retrieval_chunk_id),x.raw_score) for x in responses['bm25'].evidence]
  if all(m in responses and responses[m].status=='OK' for m in ['bm25','dense','hybrid']):
   scores={}
   for mode in ['bm25','dense']:
    for e in responses[mode].evidence: scores[str(e.retrieval_chunk_id)]=scores.get(str(e.retrieval_chunk_id),0)+1/(60+e.rank)
   expected=sorted(scores,key=lambda k:(-scores[k],k))[:5]
   result['independent_rrf_match']=expected==[str(e.retrieval_chunk_id) for e in responses['hybrid'].evidence] and all(abs(e.raw_score-scores[str(e.retrieval_chunk_id)])<1e-12 for e in responses['hybrid'].evidence)
  for mode in ['bm25','dense','hybrid']:
   if mode!='bm25' and not model_ready: continue
   args=['--query',query,'--mode',mode,'--top-k','5','--as-of-date','2026-11-14','--allowed-policy','EXPERIMENTAL_ONLY','--bm25-candidates','5','--dense-candidates','5']
   if mode!='bm25': args+=['--dense-model-path',str(MODEL)]
   try:
    proc=subprocess.run([sys.executable,str(Path(__file__).resolve()),'--cli-child',*args],capture_output=True,text=True,encoding='utf-8',timeout=100)
    raw=json.loads(proc.stdout)
    same=mode in responses and [(e['retrieval_chunk_id'],e['raw_score']) for e in raw.get('evidence',[])]==[(str(e.retrieval_chunk_id),e.raw_score) for e in responses[mode].evidence]
    result['tests'].append({'id':f'cli_{mode}','kind':'actual_cli_entrypoint_secure_dotenv_launcher','command':['.venv/Scripts/python.exe','.docs/development/retrieval-e2e-verifier.py','--cli-child',*args],'exit_code':proc.returncode,'response':compact(raw),'service_ids_scores_match':same})
   except Exception as e: result['tests'].append({'id':f'cli_{mode}','error_type':type(e).__name__})
   save(); print(json.dumps({'test':f'cli_{mode}','completed':True}),flush=True)
  db.rollback()
except Exception as e:
 result['fatal']={'error_type':type(e).__name__,'sqlstate':getattr(e,'sqlstate',None)}
finally:
 save()
