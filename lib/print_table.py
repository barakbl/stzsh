import sys
import os
import subprocess
import io
sys.path.insert(0, os.path.dirname(__file__))
from st_core import read_json

BOLD   = '\033[1m'
BRIGHT = '\033[97m'
RESET  = '\033[0m'

BAR_CHAR = '█'
BAR_MAX  = 38


def is_histogram(data):
    if not data:
        return False
    cols = list(data[0].keys())
    return (
        'count'     in cols and
        'percent'   in cols and
        'frequency' in cols and
        isinstance(data[0].get('frequency'), float)
    )


def print_table(data):
    if not data:
        return
    columns = list(data[0].keys())
    hist = is_histogram(data)

    widths = {col: len(col) for col in columns}
    for row in data:
        for col in columns:
            if hist and col == 'frequency':
                widths[col] = BAR_MAX
            else:
                widths[col] = max(widths[col], len(str(row.get(col, ''))))

    def format_cell(col, val, is_header=False):
        if hist and col == 'frequency' and not is_header:
            bar_len = round(float(val) * BAR_MAX)
            return (BAR_CHAR * bar_len).ljust(BAR_MAX)
        return str(val).ljust(widths[col])

    def row_line(row, bold=False, is_header=False):
        cells = ' │ '.join(format_cell(col, row.get(col, ''), is_header) for col in columns)
        line = '│ ' + cells + ' │'
        return (BOLD + line + RESET) if bold else (BRIGHT + line + RESET)

    def sep_line(left, mid, right, bold=False):
        parts = ('─' * (widths[col] + 2) for col in columns)
        line = left + mid.join(parts) + right
        return (BOLD + line + RESET) if bold else line

    print(sep_line('┌', '┬', '┐', bold=True))
    print(row_line({col: col for col in columns}, bold=True, is_header=True))
    print(sep_line('├', '┼', '┤', bold=True))
    for row in data:
        print(row_line(row))
    print(sep_line('├', '┼', '┤', bold=True))
    print(row_line({col: col for col in columns}, bold=True, is_header=True))
    print(sep_line('└', '┴', '┘', bold=True))


if __name__ == '__main__':
    use_less = '--less' in sys.argv[1:]
    if use_less:
        buf = io.StringIO()
        _real_stdout = sys.stdout
        sys.stdout = buf
        print_table(read_json())
        sys.stdout = _real_stdout
        pager = subprocess.Popen(['less', '-R'], stdin=subprocess.PIPE)
        pager.communicate(buf.getvalue().encode())
    else:
        print_table(read_json())
