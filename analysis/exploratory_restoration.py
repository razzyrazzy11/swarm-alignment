"""Post-release descriptive decomposition; no provider calls or causal strata claim."""
import argparse
from collections import defaultdict
import hashlib
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def diagnostic():
    report_path = ROOT / 'research/live-results.json'
    report = json.loads(report_path.read_text(encoding='utf-8'))
    data_path = ROOT / 'data/live_cases.jsonl'
    raw = data_path.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    if report['status'] != 'complete' or digest != report['artifacts']['data/live_cases.jsonl']:
        raise ValueError('Completed released evidence hash required')
    selected = [r for line in raw.decode('utf-8').splitlines()
                if (r := json.loads(line))['metadata']['exposure'] == 'actual'
                and r['metadata']['mode'] == 'delegated'
                and r['metadata']['mechanism'] in ('random', 'selective')
                and r['metadata']['restoration'] in ('metadata', 'random')]
    lookup = {(r['metadata']['source_seed'], r['metadata']['mechanism'],
               r['metadata']['restoration'], r['model']): r for r in selected}
    models = report['config']['monitors']
    seeds = sorted({key[0] for key in lookup})
    if len(lookup) != len(selected) or len(seeds) != 192 or len(selected) != 192 * 2 * 2 * len(models):
        raise ValueError('Duplicate or incomplete paired diagnostic grid')
    results = {}
    for model in models:
        strata = defaultdict(lambda: dict(pairs=0, metadata_correct=0, random_correct=0,
                                          gain=0, metadata_bytes=0, random_bytes=0))
        for seed in seeds:
            for loss in ('random', 'selective'):
                m = lookup[seed, loss, 'metadata', model]
                r = lookup[seed, loss, 'random', model]
                ms, rs = len(m['compatible_labels']) == 1, len(r['compatible_labels']) == 1
                group = ('both_singleton' if ms and rs else 'metadata_only_singleton' if ms
                         else 'random_only_singleton' if rs else 'both_ambiguous')
                t = strata[group]
                mg, rg = int(m['scored']['grounded_correct']), int(r['scored']['grounded_correct'])
                t['pairs'] += 1
                t['metadata_correct'] += mg
                t['random_correct'] += rg
                t['gain'] += mg - rg
                t['metadata_bytes'] += m['restored_bytes']
                t['random_bytes'] += r['restored_bytes']
        reproduced = sum(t['gain'] for t in strata.values()) / (2 * len(seeds))
        expected = report['analysis']['effects'][model]['delegated']['restoration_grounded_metadata_minus_random']['estimate']
        if not math.isclose(reproduced, expected, rel_tol=0, abs_tol=1e-15):
            raise ValueError('Decomposition does not recover the registered aggregate')
        results[model] = dict(strata)
    return dict(status='Exploratory post-release diagnostic; not a new confirmatory endpoint',
                source_clusters=len(seeds), dependent_pairs_per_reader=2 * len(seeds),
                data_sha256=digest, report_sha256=hashlib.sha256(report_path.read_bytes().replace(b'\r\n', b'\n')).hexdigest(),
                caveat='Strata depend on realized evidence support under both policies. Conditional counts are descriptive, not isolated causal effects. Information selection is the intended acquisition mechanism; different semantic information does not invalidate the original estimand. Bytes are not tokens or full acquisition cost. No new provider calls.',
                analysis=results)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    destination = parser.add_mutually_exclusive_group()
    destination.add_argument('--out', type=Path)
    destination.add_argument('--check', type=Path)
    args = parser.parse_args()
    result = diagnostic()
    text = json.dumps(result, indent=2) + '\n'
    if args.check:
        if json.loads(args.check.read_text(encoding='utf-8')) != result:
            raise SystemExit('Exploratory diagnostic mismatch')
        print('PASS: post-release diagnostic reproduces all registered aggregate gains')
        raise SystemExit(0)
    if args.out:
        args.out.write_text(text, encoding='utf-8', newline='\n')
    else:
        print(text, end='')
