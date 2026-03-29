import sys
import os
import re
sys.path.insert(0, os.path.dirname(__file__))
from st_core import write_json


def parse_table(lines):
    headers = None
    result = []
    for line in lines:
        line = line.rstrip('\n')
        if not line.strip():
            continue
        if headers is None:
            headers = line.split()
        else:
            # maxsplit ensures last header absorbs remaining tokens (e.g. filenames with spaces)
            tokens = line.split(None, len(headers) - 1)
            row = {}
            for i, header in enumerate(headers):
                row[header] = tokens[i].strip() if i < len(tokens) else ''
            result.append(row)
    return result


def parse_cmdlist(lines):
    return [{'name': line.strip()} for line in lines if line.strip()]


def parse_regex(pattern, lines):
    try:
        compiled = re.compile(pattern)
    except re.error as e:
        sys.exit(f'parse_stzsh: invalid regex: {e}')
    result = []
    for line in lines:
        m = compiled.search(line.rstrip('\n'))
        if m:
            result.append(m.groupdict())
    return result


if __name__ == '__main__':
    args = sys.argv[1:]
    if '--input' not in args:
        sys.exit('parse_stzsh: --input <mode> required')
    idx = args.index('--input')
    if idx + 1 >= len(args):
        sys.exit('parse_stzsh: --input requires a value')
    mode = args[idx + 1]

    lines = sys.stdin.readlines()

    if mode == 'table':
        data = parse_table(lines)
    elif mode == 'cmdlist':
        data = parse_cmdlist(lines)
    else:
        data = parse_regex(mode, lines)

    write_json(data)
