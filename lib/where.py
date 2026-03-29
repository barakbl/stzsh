import sys
import re
import os
sys.path.insert(0, os.path.dirname(__file__))
from st_core import read_json, write_json

OPERATORS = ['==', '!=', '>=', '<=', '>', '<', 'like']


def parse_condition(cond):
    for op in OPERATORS:
        idx = cond.find(op)
        if idx != -1:
            field = cond[:idx].strip()
            value = cond[idx + len(op):].strip()
            return field, op, value
    sys.exit(f'where: unrecognised operator in: {cond!r}')


def coerce(a, b):
    try:
        return float(a), float(b)
    except (TypeError, ValueError):
        return str(a), str(b)


def matches(row, field, op, value):
    cell = row.get(field, '')
    if op == 'like':
        pattern = re.escape(value).replace(r'\%', '.*').replace(r'\_', '.')
        return bool(re.search(pattern, str(cell), re.IGNORECASE))
    a, b = coerce(cell, value)
    return {
        '==': a == b,
        '!=': a != b,
        '>':  a > b,
        '<':  a < b,
        '>=': a >= b,
        '<=': a <= b,
    }[op]


if __name__ == '__main__':
    if len(sys.argv) < 2:
        sys.exit('where: condition required')
    field, op, value = parse_condition(' '.join(sys.argv[1:]))
    data = read_json()
    write_json([row for row in data if matches(row, field, op, value)])
