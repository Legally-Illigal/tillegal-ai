"""Retrieval comparison without paid generation or implicit gold approval."""
import argparse
from copy import deepcopy
import json
from pathlib import Path
from time import perf_counter
from ai_core.basic_rag import BasicRAG
from ai_core.bm25_retrieval import load_index
from ai_core.evidence_builder import EvidenceBudget, EvidenceBuilder
from ai_core.retrieval_evaluation import EvaluationCorpus
from ai_core.retrieval_runtime import ROOT, make_retriever
from ai_core.rag_generation import MockProvider
from ai_core.data_contracts import file_hash


def compare(index, retrievers, questions, top_k=10):
    corpus = EvaluationCorpus(index)
    builder = EvidenceBuilder(index,EvidenceBudget(24,8000))
    rows = []
    for number, question in enumerate(questions):
        results = {}
        for mode, retriever in retrievers.items():
            started = perf_counter()
            retrieval = retriever.search(question,top_k)
            elapsed = (perf_counter()-started)*1000
            # Demo seed selection is distinct from the retrieval comparison pool.
            selected = deepcopy(retrieval)
            selected['results'] = selected['results'][:3]
            bundle = builder.build(selected,request_id=f'compare-{number}-{mode}')
            results[mode] = {'retrieval':retrieval,'ranked_units':corpus.ranked_units(retrieval['results']),
                             'latency_ms':elapsed,'retrieved_count':len(retrieval['results']),
                             'selected_seed_count':len(selected['results']),
                             'expanded_evidence_count':len(bundle['evidence']), 'evidence_bundle':bundle}
        baseline = {h['chunk']['chunk_id'] for h in results.get('bm25',{}).get('retrieval',{}).get('results',[])}
        for value in results.values():
            ids = {h['chunk']['chunk_id'] for h in value['retrieval']['results']}
            value['added_vs_bm25'] = sorted(ids-baseline)
            value['absent_vs_bm25'] = sorted(baseline-ids)
        rows.append({'question':question,'methods':results})
    return {'kind':'technical_retrieval_comparison','index_id':index.index_id,'source':index.to_dict()['source'],
            'status':'TECHNICAL_ONLY_NO_APPROVED_GOLD','metrics':None,'missed_relevant_units':None,
            'limitations':['NOT_A_RECALL_MRR_BENCHMARK','ARTICLE_DISCOVERY_NOT_LEGAL_SUPPORT',
                           'TOP_K_CHUNKS_NOT_T5_POOL_100','NO_SEMANTIC_VERIFICATION'],
            'top_k':top_k,'results':rows}


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument('--question',action='append',required=True)
    parser.add_argument('--output',type=Path,required=True,help='New directory')
    parser.add_argument('--rerank',action='store_true')
    parser.add_argument('--mock-e2e',action='store_true',help='Local real retrieval with mock generation only')
    parser.add_argument('--top-k',type=int,default=10)
    args = parser.parse_args(argv)
    if args.output.exists():
        raise ValueError('output already exists')
    index = load_index(ROOT/'data/indexes/labor-pilot-3-t4-bm25/manifest.json')
    dense = make_retriever(index,'dense')
    from ai_core.hybrid_retrieval import HybridRetriever
    methods = {'bm25':index,'dense':dense,'hybrid':HybridRetriever(index,dense)}
    if args.rerank:
        from ai_core.reranking import LocalReranker
        from ai_core.retrieval_runtime import model_lock
        methods['hybrid_rerank'] = HybridRetriever(index,dense,reranker=LocalReranker(*model_lock('reranker')))
    report = compare(index,methods,args.question,args.top_k)
    report['latency_scope'] = 'one observation per query/method; excludes model/index load; no warmup or SLA'
    report['code_hashes'] = {p.name:file_hash(p) for p in (ROOT/'ai_core').glob('*.py')}
    report['dependency_lock_sha256'] = file_hash(ROOT/'requirements-lock.txt')
    dense_dir = ROOT/'data/indexes/labor-pilot-3-t7-dense'
    report['dense_index_bytes'] = sum(p.stat().st_size for p in dense_dir.iterdir() if p.is_file())
    report['reranker_status'] = 'REAL_LOCAL' if args.rerank else 'DISABLED_NOT_MEASURED'
    if args.mock_e2e:
        report['mock_e2e'] = {name:BasicRAG(index,MockProvider(),EvidenceBudget(24,8000),retriever=retriever).answer(
            args.question[0],request_id='technical-e2e-'+name,top_k=3) for name,retriever in methods.items()}
    args.output.mkdir(parents=True)
    (args.output/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    lines = ['# Technical retrieval comparison','', 'No approved gold; Recall/MRR and missed relevant units are not measured.',
             '', '| Question | Mode | Latency ms | Retrieved | Expanded evidence |', '|---|---|---:|---:|---:|']
    for row in report['results']:
        for name,value in row['methods'].items():
            lines.append(f"| {row['question'].replace('|','/')} | {name} | {value['latency_ms']:.1f} | {value['retrieved_count']} | {value['expanded_evidence_count']} |")
    for row in report['results']:
        lines.extend(['','## '+row['question'],''])
        for name,value in row['methods'].items():
            lines.extend(['### '+name,''])
            for hit in value['retrieval']['results']:
                c, d = hit['chunk'], hit['document']
                lines.append(f"- Rank {hit['rank']} / score {hit.get('bm25_score',hit.get('score')):.6f}: "
                             f"{d.get('document_number') or 'Không có thông tin'} — Điều {c.get('article')}, "
                             f"Khoản {c.get('clause')}, scope {c['scope']}, attachment {c['attachment_status']}. "
                             f"Chunk `{c['chunk_id']}`; địa chỉ chưa xác minh.")
                lines.append('  Trích đoạn: '+c['text'].replace('\n',' '))
    (args.output/'report.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    (args.output/'manifest.json').write_text(json.dumps(
        {'kind':'technical_comparison_artifacts','files':{name:file_hash(args.output/name)
         for name in ('report.json','report.md')}},indent=2),encoding='utf-8')
    print('\n'.join(lines))


if __name__ == '__main__':
    main()
