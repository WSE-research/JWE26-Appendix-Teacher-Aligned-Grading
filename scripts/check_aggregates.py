#!/usr/bin/env python3
"""Check selected published aggregate relationships offline, without restricted data.

This checks arithmetic and cross-file consistency. It does not reconstruct
student-level estimates, bootstrap intervals, or the underlying observations.
"""
from pathlib import Path
import csv
import json
import math
import re
import sys

ROOT = Path(__file__).resolve().parents[1]


def require(condition, message):
    if not condition:
        raise ValueError(message)


def table(number):
    with (ROOT / f'tables/table-a{number}.csv').open(newline='', encoding='utf-8') as stream:
        return list(csv.reader(stream))


def close(actual, expected, tolerance, label):
    require(abs(actual - expected) <= tolerance, f'{label}: {actual} != {expected}')


def numbers(cell):
    return [float(x) for x in re.findall(r'[+-]?\d+(?:\.\d+)?', cell)]


def model_name(name):
    return name.split('^{', 1)[0].strip()


def check_feedback():
    grid = table(10)
    counts = [int(n) for n in grid[0][1:]]
    require(counts == [0, 1, 3, 5, 10, 15, 20, 25, 30, 35, 40], 'Unexpected example grid')
    curves = {row[0]: [float(v) for v in row[1:]] for row in grid[1:]}
    aliases = {'Claude Haiku 4.5': 'Haiku 4.5', 'Qwen3.5-397B-A17B': 'Qwen3.5-397B',
               'Gemini 2.5 Flash-Lite': 'Gemini 2.5 FL', 'Mistral Small 3.2 24B': 'Mistral 3.2'}
    groups = {'ICWE run': 'ICWE', 'On premises, original': 'on-prem.',
              'On premises, reproducibility': 'rerun', 'OpenRouter, first P1': 'API'}
    seen = set()
    suffix = None
    for row in table(9)[2:]:
        if all(not cell for cell in row[1:]):
            suffix = next((v for k, v in groups.items() if row[0].startswith(k)), None)
            require(suffix is not None, f'Unknown trajectory group: {row[0]}')
            continue
        key = f'{aliases.get(row[0], row[0])}, {suffix}'
        require(key in curves and key not in seen, f'Missing/duplicate curve: {key}')
        seen.add(key)
        values = curves[key]
        first = [next((str(n) for n, v in zip(counts, values) if v >= target), '–')
                 for target in (85, 88, 90)]
        sustained = [next((str(counts[i]) for i in range(len(values))
                           if all(v >= target for v in values[i:])), '–')
                     for target in (85, 90)]
        require(row[1:6] == first + sustained, f'Target attainment mismatch: {key}')
        close(float(row[6]), values[0], 0.00001, f'{key}: n=0')
        close(float(row[7]), values[-1], 0.00001, f'{key}: n=40')
    require(seen == set(curves) and len(seen) == 14, 'Incomplete curve coverage')
    return len(seen)


def check_teacher_agreement():
    gate = table(6)[1:]
    for row in gate:
        difference = float(row[2]) - float(row[1])
        close(difference, float(row[3]), 0.011, f'Gate difference: {row[0]}')
        if row[4] != '(control)':
            require(row[4] == ('yes' if abs(difference) <= 3 else 'no'), f'Gate status: {row[0]}')
    checked = 0
    for row in table(7)[2:]:
        if '/' not in row[1]:
            continue
        percent, k, n = numbers(row[1])
        close(percent, 100 * k / n, 0.0051, f'Agreement percentage: {row[0]}')
        if not row[2]:
            continue  # Descriptive reference lines have no Wilson interval.
        z = 1.959963984540054
        prop = k / n
        center = (prop + z*z/(2*n)) / (1 + z*z/n)
        radius = z * math.sqrt(prop*(1-prop)/n + z*z/(4*n*n)) / (1 + z*z/n)
        require(len(numbers(row[2])) == 2, f'Wilson interval shape: {row[0]}')
        for actual, expected in zip(numbers(row[2]), [100*(center-radius), 100*(center+radius)]):
            close(actual, expected, 0.0051, f'Wilson interval: {row[0]}')
        over_k, over_pct = numbers(row[4])
        conf_pct, conf_k, conf_n = numbers(row[5])
        require(k == over_k + conf_k and n == 43 + conf_n, f'Subset counts: {row[0]}')
        close(over_pct, 100*over_k/43, 0.0051, f'Overruled percentage: {row[0]}')
        close(conf_pct, 100*conf_k/conf_n, 0.0051, f'Confirmed percentage: {row[0]}')
        checked += 1
    require(checked == 15, 'Incomplete base-arm agreement coverage')
    return checked


def check_crosstab():
    with (ROOT/'figures/data/teacher_label_crosstab.csv').open(newline='') as stream:
        rows = list(csv.DictReader(stream))
    cells = {(r['rater'], int(r['teacher_label']), int(r['level'])): int(r['count']) for r in rows}
    require(len(rows) == len(cells) == 20, 'Duplicate/missing crosstab cells')
    require(all(v >= 0 for v in cells.values()), 'Negative crosstab count')
    result = {}
    for coder, expected_kappa in [('jonas', 0.749), ('andreas', 0.508)]:
        for teacher, expected in [(0, 198), (1, 252)]:
            require(sum(cells[coder, teacher, level] for level in range(5)) == expected,
                    f'Crosstab denominator: {coder}/{teacher}')
        kappas = []
        for threshold in range(1, 5):
            matches = sum(cells[coder, teacher, level] for teacher in (0, 1) for level in range(5)
                          if int(level >= threshold) == teacher)
            positives = sum(cells[coder, teacher, level] for teacher in (0, 1) for level in range(threshold, 5))
            observed = matches / 450
            chance = (positives*252 + (450-positives)*198) / 450**2
            kappas.append((observed-chance)/(1-chance))
        require(kappas.index(max(kappas)) + 1 == 3, f'Primary-threshold relation: {coder}')
        close(kappas[2], expected_kappa, 0.00051, f'Coder/teacher kappa: {coder}')
        result[coder] = round(kappas[2], 6)
    return result


def check_binary():
    doc = json.loads((ROOT/'figures/data/binary_runs_vs_reference.json').read_text())
    require(doc['primary_threshold'] == 3 and len(doc['runs']) == 15, 'Unexpected binary aggregate scope')
    rows = {model_name(row[0]): row for row in table(11)[1:] if row[1]}
    paired = {model_name(row[0]): row for row in table(12)[2:] if row[1]}
    names = {
        'microsoft/phi-4:16k': 'Phi-4',
        'mistralai/Mistral-Small-3.2-24B-Instruct-2506': 'Mistral Small 3.2',
        'Qwen/Qwen3.6-27B': 'Qwen3.6-27B', 'Qwen/Qwen3.8-27B': 'Qwen3.8-27B',
        'Qwen/Qwen3-32B': 'Qwen3-32B', 'Qwen/Qwen3.5-27B': 'Qwen3.5-27B',
        'deepseek/deepseek-v4-flash': 'DeepSeek V4 Flash', 'openai/gpt-5.6-luna': 'GPT-5.6 Luna',
        'qwen/qwen3.8-flash': 'Qwen3.8 Flash', 'google/gemini-3.5-flash-lite': 'Gemini 3.5 Flash-Lite',
        'anthropic/claude-haiku-4.5': 'Claude Haiku 4.5', 'deepseek/deepseek-v3.2': 'DeepSeek V3.2',
        'google/gemini-2.5-flash-lite': 'Gemini 2.5 Flash-Lite',
        'qwen/qwen3.5-397b-a17b': 'Qwen3.5-397B-A17B', 'z-ai/glm-4.7-flash': 'GLM-4.7 Flash'}
    reference = doc['humans']['t3']['teacher_vs_reference']
    require(set(names) == {r['model'] for r in doc['runs']}, 'Unexpected model set')
    require(set(paired) == set(names.values()), 'Unexpected paired table model set')
    require(set(rows) == set(names.values()) | {'Historical teacher label'}, 'Unexpected binary table model set')
    for run in doc['runs']:
        name = names[run['model']]
        require(run['headline'] is True, f'Non-base arm in aggregate: {name}')
        require(len(numbers(rows[name][1])) == 3 and len(run['reference_t3']['kappa_ci']) == 2,
                f'Binary interval shape: {name}')
        require(len(numbers(paired[name][1])) == 3, f'Paired interval shape: {name}')
        for actual, expected in zip(numbers(rows[name][1]),
                                    [run['reference_t3']['kappa'], *run['reference_t3']['kappa_ci']]):
            close(actual, expected, 0.00051, f'Binary estimate/interval: {name}')
        close(float(rows[name][2]), run['teacher']['kappa'], 0.00051, f'Teacher kappa: {name}')
        close(numbers(paired[name][1])[0], run['reference_t3']['kappa']-reference['kappa'],
              0.00051, f'Paired point difference: {name}')
    require(len(numbers(rows['Historical teacher label'][1])) == 3 and len(reference['kappa_ci']) == 2,
            'Teacher/reference interval shape')
    for actual, expected in zip(numbers(rows['Historical teacher label'][1]),
                                [reference['kappa'], *reference['kappa_ci']]):
        close(actual, expected, 0.00051, 'Teacher/reference estimate/interval')
    return len(doc['runs'])


def check_rationale():
    rows = table(14)
    totals = {}
    for column, name in enumerate(rows[0][1:], 1):
        contradictions = comparable = 0
        for row in rows[1:]:
            numerator, denominator = map(int, row[column].split('/'))
            require(0 <= numerator <= denominator <= 450, f'Rationale counts: {row[0]}/{name}')
            contradictions += numerator
            comparable += denominator
        totals[name] = {'contradictions': contradictions, 'comparable': comparable}
    require(len(rows) == 5, 'Unexpected rationale grader count')
    return totals


def check():
    return {'status': 'PASS', 'full_grid_trajectories_checked': check_feedback(),
            'base_arm_percentages_and_wilson_intervals_checked': check_teacher_agreement(),
            'coder_teacher_kappa_at_threshold_3': check_crosstab(),
            'binary_base_arms_cross_checked': check_binary(),
            'rationale_totals': check_rationale(),
            'scope': 'Published aggregate arithmetic and cross-file consistency only; no raw-data or bootstrap reconstruction.'}


if __name__ == '__main__':
    try:
        print(json.dumps(check(), indent=2))
    except (ValueError, KeyError, IndexError, OSError) as error:
        print(f'FAIL: {error}', file=sys.stderr)
        sys.exit(1)
