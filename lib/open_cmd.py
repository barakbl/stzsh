import sys
import os
import json
import csv
import io
import tty
import termios

sys.path.insert(0, os.path.dirname(__file__))
from st_core import write_json

try:
    import tomllib
except ImportError:
    try:
        import tomli as tomllib
    except ImportError:
        tomllib = None

try:
    import yaml
except ImportError:
    yaml = None

FORMATS = ['json', 'csv', 'yml', 'toml', 'table']

SUFFIX_MAP = {
    '.json': 'json',
    '.csv':  'csv',
    '.yml':  'yml',
    '.yaml': 'yml',
    '.toml': 'toml',
}


def parse_json(content):
    result = json.loads(content)
    return result if isinstance(result, list) else [result]


def parse_csv(content):
    reader = csv.DictReader(io.StringIO(content))
    return list(reader)


def parse_yml(content):
    if yaml is None:
        print('open: pyyaml not installed — run: pip install pyyaml', file=sys.stderr)
        sys.exit(1)
    result = yaml.safe_load(content)
    if isinstance(result, list):
        return result
    if isinstance(result, dict):
        for v in result.values():
            if isinstance(v, list):
                return v
    return [result]


def parse_toml(content):
    if tomllib is None:
        print('open: tomllib not available — requires Python 3.11+ or: pip install tomli', file=sys.stderr)
        sys.exit(1)
    result = tomllib.loads(content)
    for v in result.values():
        if isinstance(v, list):
            return v
    return [result]


def parse_table(content):
    lines = content.splitlines(keepends=True)
    headers = None
    result = []
    for line in lines:
        line = line.rstrip('\n')
        if not line.strip():
            continue
        if headers is None:
            headers = line.split()
        else:
            tokens = line.split(None, len(headers) - 1)
            row = {}
            for i, header in enumerate(headers):
                row[header] = tokens[i].strip() if i < len(tokens) else ''
            result.append(row)
    return result


PARSERS = {
    'json':  parse_json,
    'csv':   parse_csv,
    'yml':   parse_yml,
    'toml':  parse_toml,
    'table': parse_table,
}


def interactive_select(options):
    state = [0]

    def render():
        sys.stderr.write('\033[?25l')
        for i, opt in enumerate(options):
            prefix = '\033[1m\033[96m> \033[0m\033[1m' if i == state[0] else '  '
            suffix = '\033[0m' if i == state[0] else ''
            sys.stderr.write(f'\r\033[K{prefix}{opt}{suffix}\n')
        sys.stderr.write(f'\033[{len(options)}A')
        sys.stderr.flush()

    fd = sys.stdin.fileno()
    old = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        render()
        while True:
            ch = os.read(fd, 1)
            if ch in (b'\r', b'\n'):
                break
            elif ch == b'\x03':
                sys.stderr.write(f'\033[{len(options)}B\033[?25h\n')
                sys.exit(0)
            elif ch == b'\x1b':
                ch2 = os.read(fd, 1)
                if ch2 == b'[':
                    ch3 = os.read(fd, 1)
                    if ch3 == b'A':
                        state[0] = (state[0] - 1) % len(options)
                    elif ch3 == b'B':
                        state[0] = (state[0] + 1) % len(options)
            render()
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old)
        sys.stderr.write(f'\033[{len(options)}B\033[?25h\n')
        sys.stderr.flush()

    return options[state[0]]


def main():
    args = sys.argv[1:]

    if not args:
        print('usage: open <file> [--from json|csv|yml|toml|table]', file=sys.stderr)
        sys.exit(1)

    filepath = args[0]

    fmt = None
    if '--from' in args:
        idx = args.index('--from')
        if idx + 1 < len(args):
            fmt = args[idx + 1].lower()
            if fmt not in PARSERS:
                print(f'open: unknown format "{fmt}". Choose from: {", ".join(FORMATS)}', file=sys.stderr)
                sys.exit(1)

    if fmt is None:
        _, ext = os.path.splitext(filepath)
        fmt = SUFFIX_MAP.get(ext.lower())

    if fmt is None:
        sys.stderr.write(f'open: unknown file type — select format:\n')
        fmt = interactive_select(FORMATS)

    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
    except FileNotFoundError:
        print(f'open: file not found: {filepath}', file=sys.stderr)
        sys.exit(1)
    except OSError as e:
        print(f'open: {e}', file=sys.stderr)
        sys.exit(1)

    data = PARSERS[fmt](content)
    write_json(data)


if __name__ == '__main__':
    main()
