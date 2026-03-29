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


class TreeNode:
    def __init__(self, label, children, depth, expanded=False):
        self.label    = label
        self.children = children
        self.depth    = depth
        self.expanded = expanded


def truncate(s, width):
    s = str(s)
    if len(s) > width:
        return s[:width - 1] + '…'
    return s


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


def _dict_to_raw_node(d):
    """Convert a dict to a single {name, children?} node using first non-children key as label."""
    if not d:
        return {'name': '(empty)'}
    keys = list(d.keys())
    label_key = next((k for k in keys if k != 'children'), keys[0])
    label = str(d[label_key])
    children = []
    for k, v in d.items():
        if k == label_key:
            continue
        if k == 'children' and isinstance(v, list):
            children.extend(_to_raw_nodes(v))
        elif isinstance(v, (dict, list)):
            sub = _to_raw_nodes(v)
            children.append({'name': k, 'children': sub} if sub else {'name': k})
        else:
            children.append({'name': f'{k}: {v}'})
    node = {'name': label}
    if children:
        node['children'] = children
    return node


def _to_raw_nodes(value):
    """Convert any JSON value to a list of {name, children?} node dicts."""
    if isinstance(value, list):
        nodes = []
        for item in value:
            if isinstance(item, dict):
                nodes.append(_dict_to_raw_node(item))
            elif isinstance(item, list):
                sub = _to_raw_nodes(item)
                nodes.append({'name': '[]', 'children': sub} if sub else {'name': '[]'})
            else:
                nodes.append({'name': str(item)})
        return nodes
    elif isinstance(value, dict):
        return [_dict_to_raw_node(value)]
    else:
        return [{'name': str(value)}]


def normalize_input(data):
    """Accept list-of-dicts or a top-level dict and return list of raw node dicts."""
    if isinstance(data, list):
        return data  # existing format, pass through
    if isinstance(data, dict):
        result = []
        for k, v in data.items():
            sub = _to_raw_nodes(v)
            result.append({'name': k, 'children': sub} if sub else {'name': k})
        return result
    raise ValueError('expected a JSON object or array')


def detect_label_field(raw_nodes):
    if not raw_nodes:
        return '(node)'
    for key in raw_nodes[0].keys():
        if key != 'children':
            return key
    return '(node)'


def build_tree(raw_nodes, label_field, depth=0):
    nodes = []
    for raw in raw_nodes:
        label = str(raw.get(label_field, '(node)'))
        raw_children = raw.get('children', [])
        children = build_tree(raw_children, label_field, depth + 1) if raw_children else []
        node = TreeNode(label=label, children=children, depth=depth)
        nodes.append(node)
    return nodes


def initial_visible(roots):
    """
    Root nodes: expanded=True, their direct children in visible but collapsed.
    Grandchildren and deeper: not in visible yet.
    """
    visible = []
    for root in roots:
        root.expanded = True
        visible.append(root)
        for child in root.children:
            child.expanded = False
            visible.append(child)
    return visible


def toggle_node(visible, cursor):
    node = visible[cursor]
    if not node.children:
        return  # leaf, no-op

    if node.expanded:
        # Collapse: remove all descendants
        node.expanded = False
        i = cursor + 1
        while i < len(visible) and visible[i].depth > node.depth:
            i += 1
        del visible[cursor + 1:i]
    else:
        # Expand: insert direct children (collapsed)
        node.expanded = True
        for i, child in enumerate(node.children):
            child.expanded = False
            visible.insert(cursor + 1 + i, child)


def clamp_scroll(visible, cursor, row_offset, data_rows):
    n = len(visible)
    cursor = max(0, min(cursor, n - 1)) if n > 0 else 0
    if cursor < row_offset:
        row_offset = cursor
    elif cursor >= row_offset + data_rows:
        row_offset = cursor - data_rows + 1
    row_offset = max(0, row_offset)
    return cursor, row_offset


def render_tree(tty_file, visible, cursor, row_offset, term_rows, term_cols):
    data_rows = term_rows - 3  # top border + bottom border + status bar
    if data_rows < 1:
        data_rows = 1

    lines = []

    # Top border
    title = '─ Tree '
    border_fill = '─' * max(0, term_cols - 2 - len(title))
    lines.append(BOLD + '┌' + title + border_fill + '┐' + RESET)

    for rel in range(data_rows):
        abs_idx = row_offset + rel
        if abs_idx >= len(visible):
            lines.append('│' + ' ' * (term_cols - 2) + '│')
            continue

        node = visible[abs_idx]
        is_cursor = (abs_idx == cursor)

        indent = '  ' * node.depth
        if node.children:
            prefix = '▼ ' if node.expanded else '▶ '
        else:
            prefix = '· '

        max_label = term_cols - 4 - len(indent) - len(prefix)
        label_text = truncate(node.label, max(1, max_label))
        content = indent + prefix + label_text
        # Pad to fill inner width
        inner_width = term_cols - 2
        padded = content.ljust(inner_width)[:inner_width]

        if is_cursor:
            lines.append(BOLD + BRIGHT_BG + '│' + BRIGHT_FG + padded + RESET + BOLD + '│' + RESET)
        else:
            lines.append('│' + BRIGHT_FG + padded + RESET + '│')

    # Bottom border
    lines.append(BOLD + '└' + '─' * (term_cols - 2) + '┘' + RESET)

    # Status bar
    pos = f'{cursor + 1}/{len(visible)}' if visible else '0/0'
    status = (f'{DIM}[↑↓] navigate  [Enter/→] expand  [←] collapse  [q] quit{RESET}'
              f'   {pos}')
    lines.append(status)

    output = '\033[H'
    for line in lines:
        output += '\r' + line + '\033[K\n'
    tty_file.write(output.encode('utf-8'))
    tty_file.flush()


def main():
    try:
        data = read_json()
    except Exception as e:
        print(f'explore_tree: failed to read JSON: {e}', file=sys.stderr)
        sys.exit(1)

    if not data:
        print('explore_tree: no data', file=sys.stderr)
        sys.exit(1)

    try:
        data = normalize_input(data)
    except ValueError as e:
        print(f'explore_tree: {e}', file=sys.stderr)
        sys.exit(1)

    label_field = detect_label_field(data)
    roots = build_tree(data, label_field)
    visible = initial_visible(roots)

    cursor = 0
    row_offset = 0

    tty_file = open('/dev/tty', 'r+b', buffering=0)
    tty_fd = tty_file.fileno()
    old_settings = termios.tcgetattr(tty_fd)

    try:
        tty.setraw(tty_fd)
        tty_file.write(b'\033[?1049h\033[H\033[2J\033[?25l')
        tty_file.flush()

        while True:
            term_cols, term_rows = os.get_terminal_size(tty_fd)
            data_rows = max(1, term_rows - 3)
            cursor, row_offset = clamp_scroll(visible, cursor, row_offset, data_rows)
            render_tree(tty_file, visible, cursor, row_offset, term_rows, term_cols)

            key = read_key(tty_fd)

            if key in ('q', 'CTRL_C'):
                break
            elif key == 'UP':
                if cursor > 0:
                    cursor -= 1
            elif key == 'DOWN':
                if cursor < len(visible) - 1:
                    cursor += 1
            elif key == 'PAGEUP':
                term_cols2, term_rows2 = os.get_terminal_size(tty_fd)
                page = max(1, term_rows2 - 3)
                cursor = max(0, cursor - page)
            elif key == 'PAGEDOWN':
                term_cols2, term_rows2 = os.get_terminal_size(tty_fd)
                page = max(1, term_rows2 - 3)
                cursor = min(len(visible) - 1, cursor + page)
            elif key in ('ENTER', 'RIGHT'):
                node = visible[cursor]
                if node.children:
                    toggle_node(visible, cursor)
            elif key == 'LEFT':
                node = visible[cursor]
                if node.expanded:
                    toggle_node(visible, cursor)
                elif node.depth > 0:
                    # Jump to parent
                    target_depth = node.depth - 1
                    for i in range(cursor - 1, -1, -1):
                        if visible[i].depth == target_depth:
                            cursor = i
                            break

    finally:
        termios.tcsetattr(tty_fd, termios.TCSADRAIN, old_settings)
        tty_file.write(b'\033[?1049l\033[?25h')
        tty_file.flush()
        tty_file.close()


if __name__ == '__main__':
    main()
