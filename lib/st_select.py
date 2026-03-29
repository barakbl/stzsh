import sys
import os
sys.path.insert(0, os.path.dirname(__file__))
from st_core import read_json, write_json


if __name__ == '__main__':
    fields = sys.argv[1:]
    if not fields:
        sys.exit('st-select: at least one field name required')
    data = read_json()
    write_json([{f: row[f] for f in fields if f in row} for row in data])
