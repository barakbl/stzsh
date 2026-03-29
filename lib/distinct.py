import sys
import os
sys.path.insert(0, os.path.dirname(__file__))
from st_core import read_json, write_json

def main():
    cols = sys.argv[1:]
    if not cols:
        print('distinct: at least one column required', file=sys.stderr)
        sys.exit(1)

    data = read_json()
    seen = set()
    result = []
    for row in data:
        key = tuple(str(row.get(c, '')) for c in cols)
        if key not in seen:
            seen.add(key)
            result.append(row)

    write_json(result)

if __name__ == '__main__':
    main()
