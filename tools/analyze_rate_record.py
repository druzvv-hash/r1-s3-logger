"""Validate a native recording and report cadence/dispersion, without editing it.

--experimental-rate enables only diagnostic 10..1000 Hz config decoding. It does
not relax CRC, SHA, raw/calibrated, time, quality or integration checks.
"""
import argparse
import hashlib
import json
from pathlib import Path
import statistics
import sys
import tempfile

import contracts


def analyze(path, experimental=False):
    original = contracts.REGISTRY
    try:
        if experimental:
            contracts.REGISTRY = [dict(f) for f in original]
            field = next(f for f in contracts.REGISTRY if f['name'] == 'requested_rate_hz')
            field.pop('enum', None)
            field.update(min=10, max=1000)
        data = path.read_bytes()
        record = contracts.read_native(data)
        rows = record['rows']
        config = record['metadata']['config']
        intervals = [b['t_us'] - a['t_us'] for a, b in zip(rows, rows[1:])]
        gaps = sum(b['seq'] - a['seq'] - 1 for a, b in zip(rows, rows[1:]))
        result = dict(file=path.name, bytes=len(data), sha256=hashlib.sha256(data).hexdigest(),
                      clean=record['clean'], verified_rows=len(rows),
                      unverified_rows=len(record['unverified_rows']), partial_line=record['partial_line'],
                      requested_hz=config['requested_rate_hz'], missing_sequences=gaps,
                      invalid_rows=sum(bool(r['quality'] & contracts.INVALID) for r in rows),
                      gap_rows=sum(bool(r['quality'] & contracts.GAP) for r in rows),
                      experimental_rate_decoder=experimental)
        if intervals:
            ordered = sorted(intervals)
            result.update(actual_hz=1e6 / statistics.mean(intervals),
                          interval_us=dict(min=min(intervals), median=statistics.median(intervals),
                                           p99=ordered[int((len(ordered)-1)*.99)], max=max(intervals)))
        for channel in ('I_A', 'U_V'):
            values = [r[channel] for r in rows if r[channel] is not None]
            diffs = [b[channel]-a[channel] for a,b in zip(rows, rows[1:])
                     if a[channel] is not None and b[channel] is not None and b['seq']==a['seq']+1]
            if values:
                result[channel] = dict(mean=statistics.mean(values), std=statistics.pstdev(values),
                                       min=min(values), max=max(values),
                                       adjacent_difference_std=statistics.pstdev(diffs) if diffs else None)
        # Exercise the production streaming adapter too, with the same explicit
        # diagnostic registry override only when requested.
        sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'viewer'))
        import core
        with tempfile.TemporaryDirectory(prefix='r1-rate-') as folder:
            with path.open('rb') as source:
                session = core.load(source, Path(folder)/'record.sqlite')
            try:
                result['viewer_rows'] = session.summary['rows']
                result['viewer_integrity'] = session.summary['integrity']
            finally:
                session.close()
        return result
    finally:
        contracts.REGISTRY = original


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('file', type=Path)
    parser.add_argument('--experimental-rate', action='store_true')
    args = parser.parse_args()
    print(json.dumps(analyze(args.file, args.experimental_rate), indent=2))
