import sys
import os
sys.path.insert(0, os.path.dirname(__file__))
from st_core import read_json

BOLD = '\033[1m'
RESET = '\033[0m'


def describe(data):
    if not data:
        print('(empty)')
        return
    columns = list(data[0].keys())
    width = max(len(c) for c in columns)
    top    = BOLD + '┌' + '─' * (width + 2) + '┐' + RESET
    bottom = BOLD + '└' + '─' * (width + 2) + '┘' + RESET
    print(top)
    for col in columns:
        print(BOLD + '│ ' + RESET + col.ljust(width) + BOLD + ' │' + RESET)
    print(bottom)


if __name__ == '__main__':
    describe(read_json())
