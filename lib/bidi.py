#!/usr/bin/env python3
"""
Apply the Unicode Bidirectional Algorithm (UBA) to text for terminal display.
Handles Hebrew, Arabic, and mixed RTL/LTR content.
ANSI escape sequences are treated as atomic invisible units and never split.

Usage:
    echo "שלום world" | bidi
    bidi "שלום world"
    bidi --rtl "mixed RTL paragraph"
    bidi --ltr "force LTR paragraph"
"""

import re
import sys
import unicodedata

# ── ANSI handling ─────────────────────────────────────────────────────────────

# Matches CSI sequences (\x1b[...m), OSC, and single-char escapes
_ANSI_RE = re.compile(r'\x1b(?:\[[0-9;]*[A-Za-z]|\][^\x07]*\x07|.)')

# PUA placeholder range – characters here are invisible to BiDi logic (BN class)
_PUA = 0xE000

def _encode_ansi(line):
    """Replace each ANSI sequence with a single PUA placeholder. Return (clean, seqs)."""
    seqs = []
    def _replace(m):
        ch = chr(_PUA + len(seqs))
        seqs.append(m.group())
        return ch
    return _ANSI_RE.sub(_replace, line), seqs

def _decode_ansi(chars, seqs):
    """Restore PUA placeholders back to original ANSI sequences."""
    out = []
    for ch in chars:
        code = ord(ch)
        if _PUA <= code < _PUA + len(seqs):
            out.append(seqs[code - _PUA])
        else:
            out.append(ch)
    return ''.join(out)

# ── BiDi character classes ────────────────────────────────────────────────────

_RTL_STRONG = frozenset(('R', 'AL'))
_LTR_STRONG = frozenset(('L',))
_WEAK_TYPES = frozenset(('ES', 'ET', 'CS', 'NSM', 'BN'))
_NEUTRAL    = frozenset(('WS', 'ON', 'B', 'S'))

def _bclass(ch):
    """BiDi class, treating PUA placeholders as BN (invisible)."""
    if _PUA <= ord(ch) < _PUA + 0x1000:
        return 'BN'
    return unicodedata.bidirectional(ch)

# ── Core algorithm ─────────────────────────────────────────────────────────────

def resolve_levels(chars):
    """
    Assign a BiDi embedding level (0=LTR, 1=RTL) to each character.
    Simplified single-level UBA covering Hebrew/Arabic + Latin mixed text.
    """
    n = len(chars)
    classes = [_bclass(ch) for ch in chars]

    # P2/P3: paragraph base level from first strong character
    para_level = 0
    for bc in classes:
        if bc in _RTL_STRONG:
            para_level = 1
            break
        if bc in _LTR_STRONG:
            break

    levels = [para_level] * n

    # W1: NSM inherits previous non-NSM class
    prev = 'ON'
    for i, bc in enumerate(classes):
        if bc == 'NSM':
            classes[i] = prev
        elif bc != 'BN':
            prev = bc

    # W2: EN after AL → AN
    last_strong = None
    for i, bc in enumerate(classes):
        if bc in _RTL_STRONG or bc in _LTR_STRONG:
            last_strong = bc
        if bc == 'EN' and last_strong in _RTL_STRONG:
            classes[i] = 'AN'

    # W3: AL → R
    for i, bc in enumerate(classes):
        if bc == 'AL':
            classes[i] = 'R'

    # W4: single ES/CS between two ENs → EN; single CS between two ANs → AN
    for i in range(1, n - 1):
        if classes[i] == 'ES' and classes[i-1] == 'EN' and classes[i+1] == 'EN':
            classes[i] = 'EN'
        elif classes[i] == 'CS':
            if classes[i-1] == 'EN' and classes[i+1] == 'EN':
                classes[i] = 'EN'
            elif classes[i-1] == 'AN' and classes[i+1] == 'AN':
                classes[i] = 'AN'

    # W5: ET adjacent to EN → EN
    for i in range(n):
        if classes[i] == 'ET':
            for j in range(i - 1, -1, -1):
                if classes[j] == 'EN':
                    classes[i] = 'EN'; break
                if classes[j] not in _WEAK_TYPES:
                    break
    for i in range(n - 1, -1, -1):
        if classes[i] == 'ET':
            for j in range(i + 1, n):
                if classes[j] == 'EN':
                    classes[i] = 'EN'; break
                if classes[j] not in _WEAK_TYPES:
                    break

    # W6: remaining separators/terminators → ON
    for i, bc in enumerate(classes):
        if bc in ('ET', 'ES', 'CS'):
            classes[i] = 'ON'

    # W7: EN after last LTR strong → L
    last_strong = para_level
    for i, bc in enumerate(classes):
        if bc == 'L':
            last_strong = 0
        elif bc == 'R':
            last_strong = 1
        if bc == 'EN' and last_strong == 0:
            classes[i] = 'L'

    # Assign levels from resolved classes
    for i, bc in enumerate(classes):
        if bc == 'L':
            levels[i] = 0
        elif bc in ('R', 'AN', 'EN'):
            levels[i] = 1
        # BN/neutrals keep para_level

    # N1/N2: neutrals between chars of same direction take that direction
    for i in range(n):
        if classes[i] in _NEUTRAL or classes[i] in _WEAK_TYPES:
            left = para_level
            for j in range(i - 1, -1, -1):
                if classes[j] not in _NEUTRAL and classes[j] not in _WEAK_TYPES:
                    left = levels[j]; break
            right = para_level
            for j in range(i + 1, n):
                if classes[j] not in _NEUTRAL and classes[j] not in _WEAK_TYPES:
                    right = levels[j]; break
            levels[i] = left if left == right else para_level

    return levels, para_level

def reorder(chars, levels, para_level):
    """L2: reverse contiguous runs of characters at each level, highest first."""
    if not chars:
        return chars
    max_level = max(levels) if levels else para_level
    result = list(chars)
    for level in range(max_level, 0, -1):
        i = 0
        while i < len(result):
            if levels[i] >= level:
                j = i
                while j < len(result) and levels[j] >= level:
                    j += 1
                result[i:j] = result[i:j][::-1]
                i = j
            else:
                i += 1
    return result

# ── Public API ────────────────────────────────────────────────────────────────

def process_line(line, force_dir=None):
    """Apply BiDi to a single line, preserving ANSI escape sequences intact."""
    if not line:
        return line

    clean, seqs = _encode_ansi(line)
    chars = list(clean)

    levels, para_level = resolve_levels(chars)

    if force_dir == 'rtl':
        para_level = 1
        levels = [
            max(1, lv) if _bclass(ch) not in _NEUTRAL else lv
            for ch, lv in zip(chars, levels)
        ]
    elif force_dir == 'ltr':
        para_level = 0

    reordered = reorder(chars, levels, para_level)
    return _decode_ansi(reordered, seqs)

def apply_bidi(text, force_dir=None):
    """Apply BiDi to every line in text."""
    return '\n'.join(process_line(line, force_dir) for line in text.split('\n'))

def has_rtl(text):
    """Return True if text contains any RTL (Hebrew/Arabic) characters."""
    return any(unicodedata.bidirectional(ch) in _RTL_STRONG for ch in text)

# ── CLI ────────────────────────────────────────────────────────────────────────

def main():
    import argparse
    parser = argparse.ArgumentParser(
        description='Apply Unicode BiDi algorithm to Hebrew/Arabic text for terminal display.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  echo "שלום world"   | bidi
  bidi "مرحبا world"
  bidi --rtl "mixed RTL paragraph"
  bidi --ltr "שלום"
        """)
    parser.add_argument('-r', '--rtl', action='store_true',
                        help='Force RTL paragraph direction')
    parser.add_argument('-l', '--ltr', action='store_true',
                        help='Force LTR paragraph direction')
    parser.add_argument('text', nargs='*',
                        help='Text to process (reads from stdin if omitted)')
    args = parser.parse_args()

    force_dir = 'rtl' if args.rtl else ('ltr' if args.ltr else None)

    text = ' '.join(args.text) if args.text else sys.stdin.read().rstrip('\n')
    print(apply_bidi(text, force_dir))

if __name__ == '__main__':
    main()
