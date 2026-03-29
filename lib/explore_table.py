import sys
import os
import json
import termios
import tty

sys.path.insert(0, os.path.dirname(__file__))
from st_core import read_json

# ANSI codes
RESET     = '\033[0m'
BOLD      = '\033[1m'
CYAN_BG   = '\033[46m'
CYAN_FG   = '\033[36m'
BRIGHT_BG = '\033[100m'
BRIGHT_FG = '\033[97m'
DIM       = '\033[2m'

MAX_COL_WIDTH = 30


def truncate(s, width):
    s = str(s)
    if len(s) > width:
        return s[:width - 1] + '…'
    return s


def col_width(col, data):
    w = len(col)
    for row in data:
        w = max(w, len(str(row.get(col, ''))))
    return min(w, MAX_COL_WIDTH)


def read_key(fd):
    ch = os.read(fd, 1)
    if ch == b'\x1b':
        try:
            ch2 = os.read(fd, 1)
            if ch2 == b'[':
                ch3 = os.read(fd, 1)
                if ch3 == b'A': return 'UP'
                if ch3 == b'B': return 'DOWN'
                if ch3 == b'C': return 'RIGHT'
                if ch3 == b'D': return 'LEFT'
                if ch3 == b'5':
                    os.read(fd, 1)  # consume trailing '~'
                    return 'PAGEUP'
                if ch3 == b'6':
                    os.read(fd, 1)  # consume trailing '~'
                    return 'PAGEDOWN'
                return 'ESC'
            return 'ESC'
        except Exception:
            return 'ESC'
    if ch in (b'\r', b'\n'): return 'ENTER'
    if ch == b'\x03': return 'CTRL_C'
    if ch == b' ':    return 'SPACE'
    try:
        return ch.decode('utf-8')
    except Exception:
        return ''


def render_table(tty_file, data, all_cols, visible_cols, sort_col, sort_asc,
                 row_offset, cur_row, cur_col, col_start, term_rows, term_cols):
    lines = []

    # Compute widths for visible cols
    widths = {c: col_width(c, data) for c in all_cols}

    # Determine which visible cols fit on screen starting from col_start
    display_cols = []
    used = 2  # leading '│ '
    for i in range(col_start, len(visible_cols)):
        c = visible_cols[i]
        w = widths[c] + 3  # ' │ ' between cols, or ' │' at end
        if used + w > term_cols and display_cols:
            break
        display_cols.append((i, c))
        used += w

    def cell(col, val, width):
        return truncate(str(val), width).ljust(width)

    def sep_line(left, mid, right, cols):
        parts = ['─' * (widths[c] + 2) for _, c in cols]
        return left + mid.join(parts) + right

    # Top border
    lines.append(BOLD + sep_line('┌', '┬', '┐', display_cols) + RESET)

    # Header row
    header_cells = []
    for i, c in display_cols:
        w = widths[c]
        label = c
        if c == sort_col:
            label += ' ↑' if sort_asc else ' ↓'
        txt = truncate(label, w).ljust(w)
        if i == cur_col:
            header_cells.append(BOLD + CYAN_BG + ' ' + txt + ' ' + RESET)
        else:
            header_cells.append(BOLD + ' ' + txt + ' ' + RESET)
    lines.append(BOLD + '│' + '│'.join(header_cells) + '│' + RESET)

    # Separator
    lines.append(BOLD + sep_line('├', '┼', '┤', display_cols) + RESET)

    # Data rows
    data_rows = term_rows - 5  # top border + header + sep + bottom border + status
    if data_rows < 1:
        data_rows = 1

    for rel in range(data_rows):
        abs_idx = row_offset + rel
        if abs_idx >= len(data):
            lines.append('│' + ' ' * (term_cols - 2) + '│')
            continue
        row = data[abs_idx]
        is_cursor = (abs_idx == cur_row)
        cells = []
        for i, c in display_cols:
            w = widths[c]
            txt = cell(c, row.get(c, ''), w)
            if is_cursor:
                cells.append(BOLD + BRIGHT_FG + ' ' + txt + ' ' + RESET)
            else:
                cells.append(' ' + txt + ' ')
        row_line = '│' + '│'.join(cells) + '│'
        if is_cursor:
            lines.append(BOLD + BRIGHT_BG + row_line + RESET)
        else:
            lines.append(row_line)

    # Bottom border
    lines.append(BOLD + sep_line('└', '┴', '┘', display_cols) + RESET)

    # Status bar
    sort_info = f'{sort_col} {"↑" if sort_asc else "↓"}' if sort_col else 'none'
    status = (f'{DIM}[↑↓/PgUp/PgDn] rows  [←→] cols  [Enter] detail  [s] sort  [c] cols  [q] quit{RESET}'
              f'  │  sort: {sort_info}  │  row {cur_row + 1}/{len(data)}')
    lines.append(status)

    # Write to tty
    output = '\033[H'  # move cursor to top-left
    output += '\033[?25l'  # hide cursor
    for line in lines:
        output += '\r' + line + '\033[K\n'
    tty_file.write(output.encode('utf-8'))
    tty_file.flush()


def row_detail(tty_fd, tty_file, row, cols, row_num, total):
    """Centered popup showing one row in article style (bold label + value)."""
    scroll = 0

    def build_content(inner_w):
        """Return list of (kind, text) for all fields."""
        lines = []
        for c in cols:
            val = str(row.get(c, ''))
            lines.append(('label', c))
            if val:
                # Wrap value at inner_w
                for i in range(0, len(val), inner_w):
                    lines.append(('value', val[i:i + inner_w]))
            else:
                lines.append(('value', ''))
            lines.append(('spacer', ''))
        return lines

    def draw(term_cols, term_rows):
        nonlocal scroll

        # Popup size: 72% wide, 80% tall, minimum sensible size
        pop_w = max(40, min(term_cols - 4, int(term_cols * 0.72)))
        pop_h = max(10, min(term_rows - 2, int(term_rows * 0.80)))
        # Make pop_w even so centering is clean
        inner_w = pop_w - 4  # 2-char padding each side

        content = build_content(inner_w)

        # chrome: title bar + separator + footer separator + footer = 4 rows
        view_h = pop_h - 4
        if view_h < 1:
            view_h = 1

        max_scroll = max(0, len(content) - view_h)
        scroll_val = max(0, min(scroll, max_scroll))

        # Top-left corner of popup (1-based for ANSI)
        top  = max(1, (term_rows - pop_h) // 2)
        left = max(1, (term_cols - pop_w) // 2)
        inner_pad = pop_w - 2  # space between the two '│' chars

        def pos(r, c=left):
            return f'\033[{top + r};{c}H'

        out = '\033[?25l'  # hide cursor

        # ── Title bar ──────────────────────────────────────────────
        title = f' Row {row_num} / {total} '
        out += pos(0) + BOLD + '┌' + title.center(inner_pad, '─') + '┐' + RESET

        # ── Separator ──────────────────────────────────────────────
        out += pos(1) + BOLD + '├' + '─' * inner_pad + '┤' + RESET

        # ── Content ────────────────────────────────────────────────
        visible = content[scroll_val:scroll_val + view_h]
        for rel, (kind, text) in enumerate(visible):
            row_out = pos(2 + rel)
            if kind == 'label':
                label = truncate(text, inner_w)
                padded = ('  ' + BOLD + CYAN_FG + label + RESET).ljust(inner_w + len(BOLD + CYAN_FG + RESET) + 2)
                # right pad to fill the box
                plain_len = 2 + len(label)
                right_pad = ' ' * max(0, inner_pad - plain_len)
                out += row_out + BOLD + '│' + RESET + '  ' + BOLD + CYAN_FG + label + RESET + right_pad + BOLD + '│' + RESET
            elif kind == 'value':
                plain = text.ljust(inner_w)
                out += row_out + '│  ' + plain + '  │'
            else:  # spacer
                out += row_out + '│' + ' ' * inner_pad + '│'

        # Pad empty rows if content shorter than view_h
        for rel in range(len(visible), view_h):
            out += pos(2 + rel) + '│' + ' ' * inner_pad + '│'

        # ── Footer separator ───────────────────────────────────────
        scroll_pct = f'{scroll_val + 1}–{min(scroll_val + view_h, len(content))}/{len(content)}'
        out += pos(2 + view_h) + BOLD + '├' + '─' * inner_pad + '┤' + RESET

        # ── Footer hint ────────────────────────────────────────────
        hint_text = f'  ↑↓ / PgUp PgDn  scroll    Esc · q  close    {scroll_pct}'
        hint_plain = truncate(hint_text, inner_pad)
        out += pos(3 + view_h) + BOLD + '│' + RESET + DIM + hint_plain.ljust(inner_pad) + RESET + BOLD + '│' + RESET

        # ── Bottom border ──────────────────────────────────────────
        out += pos(4 + view_h) + BOLD + '└' + '─' * inner_pad + '┘' + RESET

        tty_file.write(out.encode('utf-8'))
        tty_file.flush()
        return max_scroll, view_h

    while True:
        term_cols, term_rows = os.get_terminal_size(tty_fd)
        max_scroll, view_h = draw(term_cols, term_rows)

        key = read_key(tty_fd)
        if key in ('ESC', 'q', 'CTRL_C', 'ENTER'):
            break
        elif key == 'UP':
            scroll = max(0, scroll - 1)
        elif key == 'DOWN':
            scroll = min(max_scroll, scroll + 1)
        elif key == 'PAGEUP':
            scroll = max(0, scroll - view_h)
        elif key == 'PAGEDOWN':
            scroll = min(max_scroll, scroll + view_h)


def column_selector(tty_fd, tty_file, all_cols, visible_cols, term_rows, term_cols):
    """Show column selector overlay. Returns new visible_cols or None (cancel)."""
    checked = [c in visible_cols for c in all_cols]
    sel = 0       # absolute cursor index in all_cols
    col_offset = 0  # first visible item index (scroll)

    modal_w = min(40, term_cols - 4)
    inner_w = modal_w - 2
    # fixed chrome: title + blank + hint1 + hint2 + bottom = 5 lines
    chrome = 5
    max_visible = max(1, term_rows - chrome - 2)  # rows available for col items

    while True:
        # Clamp scroll so sel is always visible
        if sel < col_offset:
            col_offset = sel
        elif sel >= col_offset + max_visible:
            col_offset = sel - max_visible + 1

        visible_slice = all_cols[col_offset:col_offset + max_visible]
        show_up   = col_offset > 0
        show_down = col_offset + max_visible < len(all_cols)

        # Build overlay lines
        items = []
        items.append('┌─ Columns ' + '─' * (inner_w - 10) + '┐')
        if show_up:
            items.append('│' + '  ▲ more above'.center(inner_w) + '│')
        for idx, c in enumerate(visible_slice):
            abs_i = col_offset + idx
            mark = 'x' if checked[abs_i] else ' '
            cursor = '>' if abs_i == sel else ' '
            label = truncate(c, inner_w - 5)
            items.append(f'│ {cursor}[{mark}] {label.ljust(inner_w - 5)} │')
        if show_down:
            items.append('│' + '  ▼ more below'.center(inner_w) + '│')
        items.append('│' + ' ' * inner_w + '│')
        items.append('│  Space: toggle   Enter: apply'.ljust(inner_w + 1) + '│')
        items.append('│  Esc: cancel'.ljust(inner_w + 1) + '│')
        items.append('└' + '─' * inner_w + '┘')

        # Center the modal
        start_row = max(0, (term_rows - len(items)) // 2)
        start_col = max(0, (term_cols - modal_w) // 2)

        out = ''
        for i, line in enumerate(items):
            out += f'\033[{start_row + i + 1};{start_col + 1}H'
            out += BOLD + line + RESET
        tty_file.write(out.encode('utf-8'))
        tty_file.flush()

        key = read_key(tty_fd)
        if key == 'UP':
            sel = (sel - 1) % len(all_cols)
        elif key == 'DOWN':
            sel = (sel + 1) % len(all_cols)
        elif key == 'SPACE':
            # Must keep at least 1
            if checked[sel] and sum(checked) <= 1:
                pass  # ignore
            else:
                checked[sel] = not checked[sel]
        elif key == 'ENTER':
            new_visible = [c for i, c in enumerate(all_cols) if checked[i]]
            if not new_visible:
                new_visible = [all_cols[0]]
            return new_visible
        elif key in ('ESC', 'q', 'CTRL_C'):
            return None


def main():
    try:
        data = read_json()
    except Exception as e:
        print(f'explore_table: failed to read JSON: {e}', file=sys.stderr)
        sys.exit(1)

    if not data:
        print('explore_table: no data', file=sys.stderr)
        sys.exit(1)

    if not isinstance(data, list):
        print('explore_table: expected a list of objects', file=sys.stderr)
        sys.exit(1)

    all_cols = list(data[0].keys())
    visible_cols = list(all_cols)
    sort_col = None
    sort_asc = True
    row_offset = 0
    cur_row = 0
    cur_col = 0
    col_start = 0

    tty_file = open('/dev/tty', 'r+b', buffering=0)
    tty_fd = tty_file.fileno()
    old_settings = termios.tcgetattr(tty_fd)

    def sorted_data():
        if sort_col:
            return sorted(data, key=lambda r: (r.get(sort_col) is None, r.get(sort_col, '')),
                          reverse=not sort_asc)
        return data

    def clamp_scroll(sdata, term_rows, term_cols):
        nonlocal row_offset, cur_row, cur_col, col_start
        n = len(sdata)
        if cur_row >= n:
            cur_row = max(0, n - 1)
        data_rows = term_rows - 5
        if data_rows < 1:
            data_rows = 1
        # Vertical
        if cur_row < row_offset:
            row_offset = cur_row
        elif cur_row >= row_offset + data_rows:
            row_offset = cur_row - data_rows + 1
        # Horizontal: ensure cur_col >= col_start
        if cur_col < col_start:
            col_start = cur_col
        # Ensure cur_col is visible (col_start might need advancing)
        widths = {c: col_width(c, data) for c in all_cols}
        while True:
            used = 2
            last_visible_i = col_start - 1
            for i in range(col_start, len(visible_cols)):
                c = visible_cols[i]
                w = widths[c] + 3
                if used + w > term_cols and last_visible_i >= col_start:
                    break
                last_visible_i = i
                used += w
            if cur_col <= last_visible_i:
                break
            col_start += 1

    try:
        tty.setraw(tty_fd)
        # Enter alternate screen
        tty_file.write(b'\033[?1049h\033[H\033[2J')
        tty_file.flush()

        while True:
            term_cols, term_rows = os.get_terminal_size(tty_fd)
            sdata = sorted_data()
            clamp_scroll(sdata, term_rows, term_cols)
            render_table(tty_file, sdata, all_cols, visible_cols, sort_col, sort_asc,
                         row_offset, cur_row, cur_col, col_start, term_rows, term_cols)

            key = read_key(tty_fd)

            if key in ('q', 'CTRL_C'):
                break
            elif key == 'ENTER':
                term_cols, term_rows = os.get_terminal_size(tty_fd)
                row_detail(tty_fd, tty_file, sdata[cur_row], visible_cols,
                           cur_row + 1, len(sdata))
                # Redraw the table fully after returning
                tty_file.write(b'\033[2J')
                tty_file.flush()
            elif key == 'UP':
                if cur_row > 0:
                    cur_row -= 1
            elif key == 'DOWN':
                if cur_row < len(sdata) - 1:
                    cur_row += 1
            elif key == 'PAGEUP':
                term_cols2, term_rows2 = os.get_terminal_size(tty_fd)
                page = max(1, term_rows2 - 5)
                cur_row = max(0, cur_row - page)
            elif key == 'PAGEDOWN':
                term_cols2, term_rows2 = os.get_terminal_size(tty_fd)
                page = max(1, term_rows2 - 5)
                cur_row = min(len(sdata) - 1, cur_row + page)
            elif key == 'LEFT':
                if cur_col > 0:
                    cur_col -= 1
                    if cur_col < col_start:
                        col_start = cur_col
            elif key == 'RIGHT':
                if cur_col < len(visible_cols) - 1:
                    cur_col += 1
            elif key == 's':
                focused = visible_cols[cur_col]
                if sort_col == focused:
                    sort_asc = not sort_asc
                else:
                    sort_col = focused
                    sort_asc = True
            elif key == 'c':
                term_cols, term_rows = os.get_terminal_size(tty_fd)
                result = column_selector(tty_fd, tty_file, all_cols, visible_cols,
                                         term_rows, term_cols)
                if result is not None:
                    visible_cols = result
                    if cur_col >= len(visible_cols):
                        cur_col = len(visible_cols) - 1
                    if col_start > cur_col:
                        col_start = cur_col

    finally:
        # Restore terminal
        termios.tcsetattr(tty_fd, termios.TCSADRAIN, old_settings)
        tty_file.write(b'\033[?1049l\033[?25h')  # exit alternate screen, show cursor
        tty_file.flush()
        tty_file.close()

    # Output current view as JSON to stdout
    sdata = sorted_data()
    output = [{c: row.get(c) for c in visible_cols} for row in sdata]
    json.dump(output, sys.stdout, separators=(',', ':'))
    sys.stdout.write('\n')
    sys.stdout.flush()


if __name__ == '__main__':
    main()
