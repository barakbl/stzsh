import sys
import os
sys.path.insert(0, os.path.dirname(__file__))
from st_core import read_json, write_json


def main():
    args = sys.argv[1:]
    if not args:
        print('usage: histogram <column>', file=sys.stderr)
        sys.exit(1)
    col  = args[0]
    data = read_json()
    if not data:
        write_json([])
        return
    if col not in data[0]:
        print(f'histogram: column "{col}" not found', file=sys.stderr)
        sys.exit(1)

    counts = {}
    for row in data:
        val = str(row.get(col, ''))
        counts[val] = counts.get(val, 0) + 1

    total     = sum(counts.values())
    max_count = max(counts.values())

    result = []
    for val, count in sorted(counts.items(), key=lambda x: -x[1]):
        result.append({
            col:         val,
            'count':     count,
            'percent':   f'{count / total * 100:.2f}%',
            'frequency': round(count / max_count, 6),
        })

    write_json(result)


if __name__ == '__main__':
    main()
