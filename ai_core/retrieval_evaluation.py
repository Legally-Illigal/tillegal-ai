"""T5 article-discovery evaluation. Human-reviewed labels gate real metrics."""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime
import hashlib
import json
from pathlib import Path
import sys
import unicodedata

from .bm25_retrieval import digest, load_index
from .data_contracts import canonical_json, ContractError, file_hash

POLICY = {
    "version": "article-discovery-strict-v1",
    "unit": "document_version_and_article_node",
    "eligible_attachment": "STRUCTURAL",
    "quoted_scope": "unresolved_block",
    "uncertain_attachment": "unresolved_block_consumes_rank",
    "dedupe": "first_occurrence_preserves_rank_order",
    "candidate_pool_k": 100,
    "ks": [5, 10],
    "heading_credit": "article_discovery_only_not_sufficient_evidence",
}


def unit_id(version, node):
    return f"article::{version}::{node}"


class EvaluationCorpus:
    """Read-only lookup for evaluation, not a citation resolver."""

    def __init__(self, index):
        self.index = index
        self.payload = index.to_dict()
        self.chunks = {c['chunk_id']: c for c in self.payload['chunks']}
        self.nodes = {n['node_id']: n for ns in self.payload['nodes'].values() for n in ns}
        self.articles = {unit_id(dv, n['node_id']): (dv, n)
                         for dv, ns in self.payload['nodes'].items() for n in ns if n['kind'] == 'article'}

    def article_for(self, chunk):
        for nid in reversed(chunk['ancestor_ids']):
            if self.nodes[nid]['kind'] == 'article':
                return unit_id(chunk['document_version_id'], nid)
        return None

    def ranked_units(self, hits):
        rows, seen = [], set()
        for expected_rank, hit in enumerate(hits, 1):
            if hit['rank'] != expected_rank:
                raise ContractError('chunk ranks must be contiguous starting at one')
            chunk = self.chunks.get(hit['chunk']['chunk_id'])
            if chunk is None or chunk != hit['chunk']:
                raise ContractError('prediction chunk differs from pinned index')
            article = self.article_for(chunk)
            eligible = (article is not None and chunk['attachment_status'] == 'STRUCTURAL'
                        and chunk['scope'] != 'quoted' and 'SOURCE_TEXT_POSSIBLY_INCOMPLETE' not in chunk['issues'])
            key = article if eligible else 'unresolved-block::' + chunk['block_id']
            if key not in seen:
                seen.add(key)
                rows.append({'unit_id': key, 'unit_rank': len(rows) + 1, 'first_chunk_rank': expected_rank,
                             'chunk_id': chunk['chunk_id'], 'eligible_article': eligible,
                             'attachment_status': chunk['attachment_status'], 'scope': chunk['scope'],
                             'issues': chunk['issues']})
        return rows


def validate_dataset(dataset, corpus):
    """Validate draft or reviewed labels without granting any human approval."""
    if (dataset.get('schema_version') != '1' or dataset.get('artifact_kind') != 'retrieval_annotation_dataset'
            or dataset.get('usage_policy') != 'EXPERIMENTAL_ONLY'
            or dataset.get('judgment_scope') != 'LOCAL_SNAPSHOT_RELEVANCE_ONLY'
            or dataset.get('policy') != POLICY):
        raise ContractError('unsupported annotation contract/policy')
    if dataset.get('index_id') != corpus.index.index_id or dataset.get('processed_snapshot_id') != corpus.payload['source']['processed_snapshot_id']:
        raise ContractError('annotation snapshot/index mismatch; reannotation required')
    if not isinstance(dataset.get('dataset_id'), str) or not dataset['dataset_id'].strip():
        raise ContractError('dataset_id required')
    if not isinstance(dataset.get('test_status'), str) or not dataset['test_status'].strip():
        raise ContractError('test exposure status required')
    cases = dataset['cases']
    if not isinstance(cases, list) or not cases:
        raise ContractError('nonempty cases required')
    seen_ids, seen_questions, family_splits, unit_splits = set(), set(), {}, {}
    for case in cases:
        if not isinstance(case['question_id'], str) or not case['question_id'] or case['question_id'] in seen_ids:
            raise ContractError('missing/duplicate question_id')
        seen_ids.add(case['question_id'])
        question = case['question']
        if not isinstance(question, str) or not question.strip() or len(question) > 10000:
            raise ContractError('invalid question')
        normalized = ' '.join(unicodedata.normalize('NFC', question).casefold().split())
        if normalized in seen_questions:
            raise ContractError('duplicate normalized question')
        seen_questions.add(normalized)
        split, family = case['split'], case['family_id']
        if split not in ('dev', 'test') or not isinstance(family, str) or not family:
            raise ContractError('invalid split/family')
        if family in family_splits and family_splits[family] != split:
            raise ContractError('question family crosses dev/test')
        family_splits[family] = split
        if case['answerability'] not in ('UNKNOWN', 'ANSWERABLE', 'UNANSWERABLE', 'AMBIGUOUS'):
            raise ContractError('unknown answerability')
        if case.get('as_of_date') is not None:
            raise ContractError('v1 labels judge local text, not current temporal validity; as_of_date must be null')
        for name in ('proposed_units', 'relevant_units'):
            units = case[name]
            if not isinstance(units, list) or len(set(units)) != len(units):
                raise ContractError('duplicate/invalid unit list')
            for uid in units:
                if uid not in corpus.articles:
                    raise ContractError('unknown article unit')
                if uid in unit_splits and unit_splits[uid] != split:
                    raise ContractError('source article crosses dev/test')
                unit_splits[uid] = split
        for evidence in case['evidence']:
            chunk = corpus.chunks.get(evidence['chunk_id'])
            if chunk is None or evidence['unit_id'] != corpus.article_for(chunk):
                raise ContractError('evidence article/version mismatch')
            if evidence['unit_id'] not in case['proposed_units'] + case['relevant_units']:
                raise ContractError('evidence must reference a declared candidate/relevant unit')
            start, end = evidence['start'], evidence['end']
            if type(start) is not int or type(end) is not int or not 0 <= start < end <= len(chunk['text']):
                raise ContractError('invalid evidence Unicode offsets')
            if chunk['text'][start:end] != evidence['quote'] or evidence['text_sha256'] != chunk['text_sha256']:
                raise ContractError('evidence quote/hash mismatch')
            if evidence['source_locator'] != chunk['source_locator']:
                raise ContractError('evidence source trace mismatch')
        review = case['review']
        if review['status'] not in ('PENDING_HUMAN_REVIEW', 'ACCEPTED_HUMAN', 'EXCLUDED_HUMAN'):
            raise ContractError('unknown review status')
        for flag in ('source_read', 'unit_mapping_checked', 'alternatives_checked', 'relevance_complete', 'predictions_hidden'):
            if type(review.get(flag)) is not bool:
                raise ContractError('review attestations must be explicit booleans')
        if review['status'] == 'PENDING_HUMAN_REVIEW':
            if review['reviewer_id'] is not None or review['reviewed_at'] is not None:
                raise ContractError('pending review must not impersonate a reviewer')
            continue
        if (review.get('reviewer_type') != 'human' or not isinstance(review['reviewer_id'], str)
                or not review['reviewer_id'].strip() or not isinstance(review['notes'], str) or not review['notes'].strip()):
            raise ContractError('reviewed labels require human identity and rationale')
        try:
            when = datetime.fromisoformat(review['reviewed_at'])
        except (TypeError, ValueError) as error:
            raise ContractError('reviewed_at requires ISO timestamp') from error
        if when.tzinfo is None or not review['source_read']:
            raise ContractError('source reading and timestamp timezone required')
        if review['status'] == 'ACCEPTED_HUMAN':
            if case['answerability'] != 'ANSWERABLE' or not case['relevant_units']:
                raise ContractError('accepted scored case needs answerable nonempty gold')
            if not all(review[f] for f in ('unit_mapping_checked', 'alternatives_checked', 'relevance_complete', 'predictions_hidden')):
                raise ContractError('reviewed gold requires complete, blind source/alternative checks')
            evidenced = {e['unit_id'] for e in case['evidence']}
            if not set(case['relevant_units']) <= evidenced:
                raise ContractError('each relevant unit requires source evidence')
        elif case['relevant_units']:
            raise ContractError('excluded case must not contribute positive labels')
    return dataset


def readiness(dataset, corpus, split):
    validate_dataset(dataset, corpus)
    if split not in ('dev', 'test'):
        raise ContractError('split must be dev or test')
    selected = [c for c in dataset['cases'] if c['split'] == split]
    if not selected:
        raise ContractError('no cases for selected split')
    counts = dict(Counter(c['review']['status'] for c in selected))
    pending = [c['question_id'] for c in selected if c['review']['status'] == 'PENDING_HUMAN_REVIEW']
    return {'status': 'NEEDS_HUMAN_REVIEW' if pending else 'READY' if counts.get('ACCEPTED_HUMAN', 0) else 'NO_SCORABLE_CASES',
            'split': split, 'counts': counts, 'pending_question_ids': pending,
            'metrics': None, 'predictions_generated': False}


def score_units(ranked, relevant, k):
    """Pure metric primitive; unit tests are synthetic, never corpus quality."""
    if type(k) is not int or k < 1 or not relevant or len(set(relevant)) != len(relevant):
        raise ContractError('positive K and nonempty unique relevant units required')
    if len(ranked) != len(set(ranked)):
        raise ContractError('ranked units must be deduplicated before scoring')
    top = ranked[:k]
    gold = set(relevant)
    hits = len(set(top) & gold)
    first = next((rank for rank, uid in enumerate(top, 1) if uid in gold), None)
    return {'recall': hits / len(gold), 'reciprocal_rank': 0.0 if first is None else 1 / first,
            'hit_count': hits, 'relevant_count': len(gold), 'first_relevant_rank': first}


def check_output(output_dir, input_paths=()):
    output = Path(output_dir).resolve()
    if output.exists() or any(output.is_relative_to(Path(p).resolve().parent) for p in input_paths):
        raise ContractError('output must be new and outside input directories')
    return output


def write_new(output_dir, files, input_paths=()):
    output = check_output(output_dir, input_paths)
    output.mkdir(parents=True, exist_ok=False)
    for name, data in files.items():
        with (output / name).open('xb') as stream:
            stream.write(data)


def freeze_dataset(dataset_path, index_manifest, split, output_dir):
    dataset_path, index_manifest = Path(dataset_path), Path(index_manifest)
    original = dataset_path.read_bytes()
    dataset = json.loads(original)
    corpus = EvaluationCorpus(load_index(index_manifest))
    state = readiness(dataset, corpus, split)
    if state['status'] != 'READY':
        raise ContractError('cannot freeze: ' + state['status'])
    payload = canonical_json(dataset) + b'\n'
    manifest = {'schema_version': '1', 'artifact_kind': 'frozen_retrieval_labels', 'split': split,
                'dataset_sha256': hashlib.sha256(payload).hexdigest(),
                'index_id': corpus.index.index_id, 'index_manifest_sha256': file_hash(index_manifest),
                'policy': POLICY, 'usage_policy': 'EXPERIMENTAL_ONLY',
                'review_authority': 'USER_SUPPLIED_HUMAN_ATTESTATIONS_NOT_AUTHENTICATED',
                'evaluation_code_sha256': file_hash(Path(__file__))}
    if dataset_path.read_bytes() != original:
        raise ContractError('labels changed during freeze')
    write_new(output_dir, {'dataset.json': payload, 'manifest.json': canonical_json(manifest) + b'\n'},
              [dataset_path, index_manifest])
    return manifest


def evaluate(frozen_manifest, index_manifest, output_dir):
    frozen_manifest, index_manifest = Path(frozen_manifest).resolve(), Path(index_manifest).resolve()
    check_output(output_dir, [frozen_manifest, index_manifest])
    manifest = json.loads(frozen_manifest.read_text(encoding='utf-8'))
    dataset_path = frozen_manifest.parent / 'dataset.json'
    if (manifest.get('artifact_kind') != 'frozen_retrieval_labels' or manifest.get('schema_version') != '1'
            or manifest.get('policy') != POLICY or manifest.get('usage_policy') != 'EXPERIMENTAL_ONLY'
            or file_hash(dataset_path) != manifest['dataset_sha256']
            or file_hash(index_manifest) != manifest['index_manifest_sha256']
            or file_hash(Path(__file__)) != manifest['evaluation_code_sha256']):
        raise ContractError('frozen labels/index/code mismatch')
    index = load_index(index_manifest)
    if index.index_id != manifest['index_id']:
        raise ContractError('frozen index identity mismatch')
    corpus = EvaluationCorpus(index)
    dataset = json.loads(dataset_path.read_text(encoding='utf-8'))
    state = readiness(dataset, corpus, manifest['split'])
    if state['status'] != 'READY':
        raise ContractError('evaluation blocked: ' + state['status'])
    predictions, excluded = [], []
    for case in dataset['cases']:
        if case['split'] != manifest['split']:
            continue
        if case['review']['status'] == 'EXCLUDED_HUMAN':
            excluded.append({'question_id': case['question_id'], 'answerability': case['answerability'],
                             'reason': case['review']['notes']})
            continue
        response = index.search(case['question'], POLICY['candidate_pool_k'])
        units = corpus.ranked_units(response['results'])
        ids = [r['unit_id'] for r in units]
        predictions.append({'question_id': case['question_id'], 'query': case['question'], 'retrieval': response,
                            'ranked_units': units, 'scores': {str(k): score_units(ids, case['relevant_units'], k) for k in POLICY['ks']},
                            'short_unit_list_at_max_k': len(ids) < max(POLICY['ks'])})
    metrics = {str(k): {'recall_at_k': sum(p['scores'][str(k)]['recall'] for p in predictions) / len(predictions),
                       'mrr_at_k': sum(p['scores'][str(k)]['reciprocal_rank'] for p in predictions) / len(predictions)}
               for k in POLICY['ks']}
    report = {'status': 'EVALUATED_REVIEWED_LABELS', 'dataset_id': dataset['dataset_id'], 'dataset_sha256': manifest['dataset_sha256'],
              'index_id': index.index_id, 'source': corpus.payload['source'], 'policy': POLICY, 'split': manifest['split'],
              'usage_policy': 'EXPERIMENTAL_ONLY', 'measurement_scope': 'ARTICLE_DISCOVERY_NOT_LEGAL_SUPPORT',
              'scored_cases': len(predictions), 'excluded_cases': excluded, 'metrics': metrics,
              'test_status': dataset['test_status'], 'review_authority': manifest['review_authority'],
              'evaluation_code_sha256': file_hash(Path(__file__))}
    if file_hash(dataset_path) != manifest['dataset_sha256']:
        raise ContractError('labels changed during evaluation')
    prediction_bytes = b''.join(canonical_json(p) + b'\n' for p in predictions)
    report['predictions_sha256'] = hashlib.sha256(prediction_bytes).hexdigest()
    write_new(output_dir, {'predictions.jsonl': prediction_bytes, 'report.json': canonical_json(report) + b'\n'},
              [frozen_manifest, index_manifest])
    return report


def main(argv=None):
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, 'reconfigure'):
            stream.reconfigure(encoding='utf-8')
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    for name in ('inspect', 'freeze', 'evaluate'):
        sub = commands.add_parser(name)
        sub.add_argument('--index-manifest', required=True, type=Path)
        sub.add_argument('--output-dir', required=True, type=Path)
        if name == 'evaluate':
            sub.add_argument('--frozen-manifest', required=True, type=Path)
        else:
            sub.add_argument('--dataset', required=True, type=Path)
            sub.add_argument('--split', choices=['dev', 'test'], required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == 'freeze':
            result = freeze_dataset(args.dataset, args.index_manifest, args.split, args.output_dir)
        elif args.command == 'evaluate':
            result = evaluate(args.frozen_manifest, args.index_manifest, args.output_dir)
        else:
            dataset = json.loads(args.dataset.read_text(encoding='utf-8'))
            corpus = EvaluationCorpus(load_index(args.index_manifest))
            result = {**readiness(dataset, corpus, args.split), 'dataset_sha256': file_hash(args.dataset),
                      'index_id': corpus.index.index_id, 'processed_snapshot_id': dataset['processed_snapshot_id']}
            write_new(args.output_dir, {'readiness.json': canonical_json(result) + b'\n'}, [args.dataset, args.index_manifest])
        print(json.dumps(result, ensure_ascii=False))
        return 0
    except (OSError, ValueError, TypeError, KeyError) as error:
        print(json.dumps({'status': 'ERROR', 'error': str(error)}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
