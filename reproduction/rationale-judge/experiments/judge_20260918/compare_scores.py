"""Descriptive, post-freeze model-score/rationale comparison. No inference or human labels."""
import ast
import collections
import csv
import hashlib
import io
import itertools
import json
import subprocess
from pathlib import Path
import frozen_lexicon as lex

COLLECTION_COMMIT = '109b1527660fd023f017e7e2b985dc5958d12a7c'
METHODS = ('primary', 's2', 'gemma')
BINARY = {'acceptable': 1, 'defect': 0, 'supports_correct': 1, 'supports_incorrect': 0}
STATES = ('consistent', 'contradictory', 'abstained', 'input_missing', 'score_missing')


def require(ok, message):
    if not ok:
        raise ValueError(message)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def no_duplicates(pairs):
    out = {}
    for key, value in pairs:
        require(key not in out, 'Duplicate JSON key')
        out[key] = value
    return out


def decode(data):
    return json.loads(data, object_pairs_hook=no_duplicates)


def json_rows(path, keys):
    rows = [decode(x) for x in path.read_text(encoding='utf-8').splitlines()]
    require(all(isinstance(r, dict) and set(r) == keys for r in rows), 'Unexpected row fields')
    require(all(isinstance(r['id'], str) and r['id'] for r in rows), 'Invalid ID')
    require(len({r['id'] for r in rows}) == len(rows), 'Duplicate row ID')
    return {r['id']: r for r in rows}


def git_blob(root, ref, path):
    return subprocess.check_output(['git', '-C', str(root), 'show', ref + ':' + path])


def git_paths(root, ref, path):
    return subprocess.check_output(['git', '-C', str(root), 'ls-tree', '-r', '--name-only', ref, path], text=True).splitlines()


def score_value(value):
    if value == '':
        return None
    require(value in ('0', '0.0', '1', '1.0'), 'Nonbinary or malformed model score')
    return int(float(value))


def parsable_value(value):
    require(value in ('True', 'False', 'true', 'false', '1', '0'), 'Malformed parsability')
    return value in ('True', 'true', '1')


def usable_score(recorded, parsable):
    require(not parsable or recorded is not None, 'Parsable row lacks a model score')
    return recorded if parsable else None


def comparison_state(label, score, reason):
    if not reason.strip():
        return 'input_missing'
    if score is None:
        return 'score_missing'
    if label not in BINARY:
        return 'abstained'
    return 'consistent' if BINARY[label] == score else 'contradictory'


def ratio(n, d):
    return n / d if d else None


def summarize(rows):
    n = len(rows)
    report = dict(rows=n, missing_reason=sum(r['reason_missing'] for r in rows),
                  missing_score=sum(r['score'] is None for r in rows),
                  unparsable_score=sum(not r.get('parsable', True) for r in rows),
                  empty_score_field=sum(r.get('recorded_model_score', r['score']) is None for r in rows), methods={}, pairs={})
    for method in METHODS:
        states = collections.Counter(r[method + '_state'] for r in rows)
        require(sum(states.values()) == n and set(states) <= set(STATES), 'Invalid partition')
        decisive = sum(not r['reason_missing'] and r[method + '_label'] in BINARY for r in rows)
        comparable = states['consistent'] + states['contradictory']
        report['methods'][method] = dict(
            label_counts=dict(collections.Counter(r[method + '_label'] for r in rows)),
            states={s: states[s] for s in STATES}, decisive=decisive, comparable=comparable,
            decisive_coverage=ratio(decisive, n), comparison_coverage=ratio(comparable, n),
            consistency_among_comparable=ratio(states['consistent'], comparable),
            contradiction_among_comparable=ratio(states['contradictory'], comparable),
            observed_contradictions_per_all_rows=ratio(states['contradictory'], n))
    for first, second in itertools.combinations(METHODS, 2):
        common = [r for r in rows if r[first + '_state'] in ('consistent', 'contradictory')
                  and r[second + '_state'] in ('consistent', 'contradictory')]
        cells = collections.Counter((r[first+'_state'], r[second+'_state']) for r in common)
        report['pairs'][first + '__' + second] = dict(common_n=len(common),
            both_consistent=cells['consistent', 'consistent'],
            first_only_contradictory=cells['contradictory', 'consistent'],
            second_only_contradictory=cells['consistent', 'contradictory'],
            both_contradictory=cells['contradictory', 'contradictory'])
    return report


def build_rows(root, package):
    prefix = str(package.relative_to(root)).replace('\\', '/')
    pinned = ['manifest.json', 'prompt.txt', 'collect.py', 'all_blind.jsonl', 'source_mapping.jsonl']
    actual_full = {str(p.relative_to(root)).replace('\\', '/') for p in (package/'results/full').rglob('*') if p.is_file()}
    expected_full = set(git_paths(root, COLLECTION_COMMIT, prefix+'/results/full'))
    require(actual_full == expected_full and bool(expected_full), 'Incomplete or extra frozen collection inventory')
    pinned += [name[len(prefix)+1:] for name in sorted(expected_full)]
    frozen_hashes = {}
    for name in pinned:
        raw = (package/name).read_bytes()
        require(raw == git_blob(root, COLLECTION_COMMIT, prefix+'/'+name), 'Frozen collection drift: '+name)
        frozen_hashes[name] = sha(raw)
    manifest = decode((package/'manifest.json').read_bytes())
    for name in ('all_blind.jsonl', 'source_mapping.jsonl'):
        require(frozen_hashes[name] == manifest['input_sha256'][name], 'Input manifest drift')
    lp = decode((package/'lexicon_provenance.json').read_bytes())
    old = git_blob(root, manifest['source_ref'], lp['source_path'])
    require(lp['source_ref'] == manifest['source_ref'] and sha(old) == lp['source_sha256'], 'Lexicon source drift')
    require(sha((package/'frozen_lexicon.py').read_bytes()) == lp['extracted_sha256'], 'Extracted lexicon drift')
    # Reconstruct the exact allowlisted AST extraction, without importing the old script.
    src = old.decode(); parts = ['"""Verbatim frozen lexical classifiers; no old analysis entrypoint imported."""', 'import re']
    names = {'LEXICON_VERSION','DEFECT_PATTERN','ACCEPTABLE_PATTERN','CONTRASTIVE_PATTERN','DEFECT_RE','ACCEPTABLE_RE','CONTRASTIVE_RE'}
    for node in ast.parse(src).body:
        if isinstance(node, ast.Assign) and isinstance(node.targets[0], ast.Name):
            if node.targets[0].id in names: parts.append(ast.get_source_segment(src, node))
            if node.targets[0].id == 'MODELS': require([list(pair) for pair in ast.literal_eval(node.value)] == lp['models'], 'Model map drift')
        if isinstance(node, ast.FunctionDef) and node.name in ('classify', 'classify_s2'):
            parts.append(ast.get_source_segment(src, node))
    require(('\n\n'.join(parts)+'\n').encode() == (package/'frozen_lexicon.py').read_bytes(), 'Classifier extraction mismatch')
    inputs = json_rows(package/'all_blind.jsonl', {'id', 'reason'})
    mapping = json_rows(package/'source_mapping.jsonl', {'id','source_path','csv_data_row_index'})
    verdicts = json_rows(package/'results/full/results/verdicts.jsonl', {'kind','id','status','label','evidence'})
    require(len(inputs) == 1800 and set(inputs) == set(mapping) == set(verdicts), 'Incomplete ID join')
    source_rows = {}; source_models = {}; selected_keys = set()
    for source in manifest['sources']:
        path = source['path']; raw = git_blob(root, manifest['source_ref'], path)
        require(sha(raw) == source['sha256'], 'Source CSV drift')
        models = [model for model, folder in lp['models'] if '/'+folder+'/' in path]
        require(len(models) == 1, 'Ambiguous source model'); source_models[path] = models[0]
        reader = csv.reader(io.StringIO(raw.decode('utf-8'))); header = next(reader)
        require(len(header) == len(set(header)), 'Duplicate CSV column')
        indexes = {k: header.index(k) for k in ('n_examples','reason','re_eval_score','parsable')}
        selected = {}
        for index, row in enumerate(reader):
            require(len(row) == len(header), 'Malformed CSV row')
            # No excluded column values are inspected, logged, or exported.
            if row[indexes['n_examples']] != '40': continue
            selected[index] = {k: row[j] for k,j in indexes.items()}
            selected_keys.add((path, index))
        require(len(selected) == source['n40_count'] == 450, 'Wrong n40 inclusion')
        source_rows[path] = selected
    require(len(source_rows) == len(set(source_models.values())) == 4, 'Expected four source models')
    output = []; seen = set()
    for ident in sorted(inputs):
        inp, key, verdict = inputs[ident], mapping[ident], verdicts[ident]
        path, index = key['source_path'], key['csv_data_row_index']
        require(type(index) is int and (path,index) in selected_keys and (path,index) not in seen, 'Invalid/duplicate source join')
        seen.add((path,index))
        require(ident == sha((manifest['source_ref']+'\n'+path+'\n'+str(index)).encode()), 'Opaque ID binding mismatch')
        original = source_rows[path][index]
        reason = inp['reason']
        require(isinstance(reason,str) and original['reason'] == reason, 'Rationale mismatch (no normalization permitted)')
        recorded_score = score_value(original['re_eval_score']); parsable = parsable_value(original['parsable'])
        score = usable_score(recorded_score, parsable)
        require(verdict['kind'] == 'result', 'Unexpected event kind')
        if not reason.strip():
            require(verdict['status'] == 'input_missing' and verdict['label'] is None and verdict['evidence'] is None, 'Missing input mismatch')
            judge_label = 'input_missing'
        else:
            require(verdict['status'] == 'ok' and verdict['label'] in ('supports_correct','supports_incorrect','undetermined'), 'Invalid judge result')
            quote = verdict['evidence']
            require(isinstance(quote,str) and quote.strip() and quote in reason, 'Invalid judge quote')
            judge_label = verdict['label']
        row = dict(id=ident, model=source_models[path], recorded_model_score=recorded_score, score=score, parsable=parsable, reason_missing=not reason.strip(),
                   primary_label=lex.classify(reason), s2_label=lex.classify_s2(reason), gemma_label=judge_label)
        for method in METHODS: row[method+'_state'] = comparison_state(row[method+'_label'],score,reason)
        output.append(row)
    require(seen == selected_keys, 'Omitted source row')
    require(sum(r['reason_missing'] for r in output) == 1, 'Unexpected missingness')
    return output, dict(collection_commit=COLLECTION_COMMIT, source_ref=manifest['source_ref'],
        sources=manifest['sources'], frozen_sha256=frozen_hashes, lexicon=lp,
        analysis_sha256=sha(Path(__file__).read_bytes()), protocol_sha256=sha((package/'COMPARISON_PROTOCOL.md').read_bytes()))


def render(report):
    lines = ['# Exploratory score-rationale consistency, n=40', '',
        'Four August rationale runs at temperature 0.2. These are distinct from the incomplete September OpenRouter campaign.',
        'Gemma outputs were frozen before joining original model scores. No human labels, factual correctness, significance tests, or accuracy claims.', '',
        '| Model | Method | All rows | Comparable | Consistent | Contradictory | Abstained | Missing rationale | Missing score state |',
        '|---|---|---:|---:|---:|---:|---:|---:|---:|']
    for model, stats in report['models'].items():
        for method, values in stats['methods'].items():
            s=values['states']
            lines.append(f"| {model} | {method} | {stats['rows']} | {values['comparable']} | {s['consistent']} | {s['contradictory']} | {s['abstained']} | {s['input_missing']} | {s['score_missing']} |")
    lines += ['', 'Comparable = decisive rationale with a valid binary original model score. Missing rationale takes priority in the mutually exclusive state partition. score is usable only when parsable=true; recorded_model_score preserves the raw CSV value. summary.json separately reports missing usable scores, unparsable rows and empty score fields. The historical pipeline may store a fallback zero for an unparsable row.',
        'Compare coverage alongside contradictions. Undetermined/mixed/nocue are abstentions, never agreement. Missing inputs are separate from abstentions.', '',
        '| Model | Pair (first / second) | Common comparable | Both consistent | Only first contradictory | Only second contradictory | Both contradictory |',
        '|---|---|---:|---:|---:|---:|---:|']
    for model, stats in report['models'].items():
        for pair, p in stats['pairs'].items():
            lines.append(f"| {model} | {pair} | {p['common_n']} | {p['both_consistent']} | {p['first_only_contradictory']} | {p['second_only_contradictory']} | {p['both_contradictory']} |")
    lines += ['', 'Rates with explicit denominators, label counts and provenance are in summary.json. The models share items; no independence or superiority is inferred. The 160-row agent diagnostic is not human gold. No outcomes are used to retune any instrument. Agreement/adjudication and A4/A5 remain gated.']
    return '\n'.join(lines)+'\n'


def main():
    package=Path(__file__).parent; root=package.parents[1]
    rows, provenance=build_rows(root,package)
    models={m:summarize([r for r in rows if r['model']==m]) for m in sorted({r['model'] for r in rows})}
    require(all(s['rows']==450 for s in models.values()), 'Model row count mismatch')
    report=dict(scope='Exploratory internal model-score/rationale consistency; not human agreement or factual accuracy.',
                human_label_analysis=False, statistical_tests=False, models=models, provenance=provenance)
    out=package/'results/score-comparison';out.mkdir(exist_ok=True)
    with (out/'per_item.csv').open('w',encoding='utf-8',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    (out/'summary.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    (out/'REPORT.md').write_text(render(report),encoding='utf-8')
    print(json.dumps(models,ensure_ascii=False))


if __name__ == '__main__':
    main()