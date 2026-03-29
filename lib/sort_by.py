import sys
import os
sys.path.insert(0, os.path.dirname(__file__))
from st_core import read_json, write_json


if __name__ == '__main__':
    args = sys.argv[1:]
    if not args:
        sys.exit('sort-by: field name required')
    field = args[0]
    desc = '--desc' in args
    data = read_json()

    def key(row):
        val = row.get(field, '')
        try:
            return (0, float(val))
        except (TypeError, ValueError):
            return (1, str(val))

    write_json(sorted(data, key=key, reverse=desc))
