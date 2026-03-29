import sys
import os
sys.path.insert(0, os.path.dirname(__file__))
from st_core import read_json, write_json

DEFAULT_N = 10

def main():
    args = sys.argv[1:]
    mode = os.path.basename(sys.argv[0]).replace('.py', '')  # 'head' or 'tail'

    n = DEFAULT_N
    if '-n' in args:
        idx = args.index('-n')
        if idx + 1 < len(args):
            try:
                n = int(args[idx + 1])
            except ValueError:
                print(f'{mode}: -n requires an integer', file=sys.stderr)
                sys.exit(1)

    data = read_json()

    if mode == 'tail':
        write_json(data[-n:])
    else:
        write_json(data[:n])

if __name__ == '__main__':
    main()
