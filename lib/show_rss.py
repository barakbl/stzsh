#!/usr/bin/env python3
"""
Parse and display RSS/Atom feed items from stdin.

Accepts either:
  - Raw XML (piped directly from curl/wget)
  - JSON (piped from `http get`, which converts XML → JSON)

Usage:
  http get https://example.com/feed.xml | show_rss
  http get https://example.com/feed.xml | show_rss --limit 5
  http get https://example.com/feed.xml | show_rss --no-desc
"""

import sys
import json
import textwrap
import xml.etree.ElementTree as ET
from datetime import datetime

import os as _os
import importlib.util as _ilu
_bidi_path = _os.path.join(_os.path.dirname(__file__), 'bidi.py')
_spec = _ilu.spec_from_file_location('bidi', _bidi_path)
_bidi_mod = _ilu.module_from_spec(_spec)
_spec.loader.exec_module(_bidi_mod)
_apply_bidi = _bidi_mod.apply_bidi
_has_rtl    = _bidi_mod.has_rtl

BOLD    = '\033[1m'
CYAN    = '\033[96m'
YELLOW  = '\033[93m'
GREEN   = '\033[92m'
DIM     = '\033[2m'
BLUE    = '\033[94m'
RESET   = '\033[0m'

# ── Helpers ───────────────────────────────────────────────────────────────────

def strip_tags(text):
    """Remove HTML tags from description text."""
    import re
    text = re.sub(r'<[^>]+>', '', text or '')
    text = re.sub(r'&amp;', '&', text)
    text = re.sub(r'&lt;', '<', text)
    text = re.sub(r'&gt;', '>', text)
    text = re.sub(r'&quot;', '"', text)
    text = re.sub(r'&#?\w+;', '', text)
    return text.strip()

def fmt_date(raw):
    """Parse and reformat common RSS/Atom date strings."""
    if not raw:
        return ''
    for fmt in (
        '%a, %d %b %Y %H:%M:%S %z',
        '%a, %d %b %Y %H:%M:%S %Z',
        '%Y-%m-%dT%H:%M:%S%z',
        '%Y-%m-%dT%H:%M:%SZ',
        '%Y-%m-%d',
    ):
        try:
            dt = datetime.strptime(raw.strip(), fmt)
            return dt.strftime('%Y-%m-%d %H:%M')
        except ValueError:
            continue
    return raw.strip()

def text_val(val):
    """Extract string from a value that may be str, dict, or list."""
    if isinstance(val, str):
        return val
    if isinstance(val, dict):
        return val.get('#text') or val.get('text') or ''
    if isinstance(val, list) and val:
        return text_val(val[0])
    return ''

def link_val(val):
    """Extract URL from <link> which may be a string or dict with @href."""
    if isinstance(val, str):
        return val
    if isinstance(val, dict):
        attrs = val.get('@attributes', {})
        return attrs.get('href') or val.get('href') or val.get('#text') or ''
    if isinstance(val, list):
        for v in val:
            result = link_val(v)
            if result:
                return result
    return ''

# ── RSS 2.0 parser (from JSON) ────────────────────────────────────────────────

def parse_rss_json(data):
    """Extract channel meta and items from http-converted RSS JSON."""
    # Unwrap top-level key (rss, feed, or namespaced variants)
    if isinstance(data, dict) and len(data) == 1:
        data = next(iter(data.values()))

    channel = data.get('channel') or data
    if isinstance(channel, list):
        channel = channel[0]

    meta = {
        'title': text_val(channel.get('title', '')),
        'link':  link_val(channel.get('link', '')),
        'desc':  text_val(channel.get('description', '') or channel.get('subtitle', '')),
    }

    raw_items = channel.get('item') or channel.get('entry') or []
    if isinstance(raw_items, dict):
        raw_items = [raw_items]

    items = []
    for it in raw_items:
        if not isinstance(it, dict):
            continue
        items.append({
            'title':   text_val(it.get('title', '')),
            'link':    link_val(it.get('link', '') or it.get('url', '')),
            'date':    fmt_date(text_val(it.get('pubDate') or it.get('published') or it.get('updated') or '')),
            'author':  text_val(
                it.get('author') or
                (it.get('author', {}) or {}).get('name', '') or ''
            ),
            'desc':    strip_tags(text_val(
                it.get('description') or it.get('summary') or it.get('content') or ''
            )),
        })
    return meta, items

# ── RSS/Atom XML parser (raw XML fallback) ────────────────────────────────────

_ATOM_NS = 'http://www.w3.org/2005/Atom'

def _find(elem, *tags):
    for tag in tags:
        found = elem.find(tag)
        if found is not None:
            return found
        found = elem.find(f'{{{_ATOM_NS}}}{tag}')
        if found is not None:
            return found
    return None

def _text(elem, *tags):
    el = _find(elem, *tags)
    return (el.text or '').strip() if el is not None else ''

def _link(elem):
    el = _find(elem, 'link')
    if el is None:
        return ''
    if el.text and el.text.strip():
        return el.text.strip()
    return el.get('href', '')

def parse_rss_xml(raw):
    root = ET.fromstring(raw)
    tag = root.tag.split('}')[-1]

    if tag == 'feed':  # Atom
        channel = root
        meta = {
            'title': _text(channel, 'title'),
            'link':  _link(channel),
            'desc':  _text(channel, 'subtitle'),
        }
        entries = (channel.findall('entry') or
                   channel.findall(f'{{{_ATOM_NS}}}entry'))
        items = []
        for e in entries:
            author_el = _find(e, 'author')
            author = _text(author_el, 'name') if author_el is not None else ''
            items.append({
                'title':  _text(e, 'title'),
                'link':   _link(e),
                'date':   fmt_date(_text(e, 'published') or _text(e, 'updated')),
                'author': author,
                'desc':   strip_tags(_text(e, 'summary') or _text(e, 'content')),
            })
        return meta, items

    # RSS 2.0
    channel = root.find('channel') or root
    meta = {
        'title': _text(channel, 'title'),
        'link':  _text(channel, 'link'),
        'desc':  _text(channel, 'description'),
    }
    items = []
    for it in channel.findall('item'):
        items.append({
            'title':  _text(it, 'title'),
            'link':   _text(it, 'link'),
            'date':   fmt_date(_text(it, 'pubDate')),
            'author': _text(it, 'author') or _text(it, '{http://purl.org/dc/elements/1.1/}creator'),
            'desc':   strip_tags(_text(it, 'description')),
        })
    return meta, items

# ── Display ───────────────────────────────────────────────────────────────────

def display(meta, items, limit=None, show_desc=True, width=80):
    feed_title = meta.get('title', '')
    feed_desc  = meta.get('desc', '')
    if _has_rtl(feed_title):
        feed_title = _apply_bidi(feed_title)
    if _has_rtl(feed_desc):
        feed_desc = _apply_bidi(feed_desc)

    if feed_title:
        print(f'\n{BOLD}{CYAN}{feed_title}{RESET}')
    if meta.get('link'):
        print(f'{DIM}{meta["link"]}{RESET}')
    if feed_desc:
        print(f'{DIM}{feed_desc}{RESET}')
    print()

    shown = items[:limit] if limit else items
    if not shown:
        print(f'{DIM}(no items found){RESET}')
        return

    for i, item in enumerate(shown, 1):
        title  = item.get('title') or '(no title)'
        link   = item.get('link', '')
        date   = item.get('date', '')
        author = item.get('author', '')
        desc   = item.get('desc', '')

        # Apply BiDi to text fields before adding ANSI codes
        if _has_rtl(title):
            title = _apply_bidi(title)
        if _has_rtl(desc):
            desc = _apply_bidi(desc)

        meta_parts = [p for p in (date, author) if p]
        meta_str   = f'  {DIM}{" · ".join(meta_parts)}{RESET}' if meta_parts else ''

        print(f'{BOLD}{YELLOW}{i:>3}.{RESET} {BOLD}{title}{RESET}')
        if meta_str:
            print(meta_str)
        if link:
            print(f'       {BLUE}{link}{RESET}')
        if show_desc and desc:
            wrapped = textwrap.fill(desc, width=width - 7,
                                    initial_indent='       ',
                                    subsequent_indent='       ')
            print(f'{DIM}{wrapped}{RESET}')
        print()

# ── CLI ───────────────────────────────────────────────────────────────────────

def main():
    import argparse
    parser = argparse.ArgumentParser(
        description='Display RSS/Atom feed items from stdin.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='Example:\n  http get https://feeds.bbci.co.uk/news/rss.xml | show_rss')
    parser.add_argument('-n', '--limit', type=int, default=None,
                        help='Max number of items to show')
    parser.add_argument('--no-desc', action='store_true',
                        help='Hide item descriptions')
    parser.add_argument('-w', '--width', type=int, default=100,
                        help='Wrap width for descriptions (default: 100)')
    args = parser.parse_args()

    raw = sys.stdin.read().strip()
    if not raw:
        print('show_rss: no input', file=sys.stderr)
        sys.exit(1)

    meta, items = None, None

    # Try JSON first (output of `http get`)
    try:
        data = json.loads(raw)
        meta, items = parse_rss_json(data)
    except (json.JSONDecodeError, Exception):
        pass

    # Fall back to raw XML
    if meta is None:
        try:
            meta, items = parse_rss_xml(raw)
        except ET.ParseError as e:
            print(f'show_rss: could not parse input as RSS/Atom XML or JSON: {e}',
                  file=sys.stderr)
            sys.exit(1)

    display(meta, items, limit=args.limit, show_desc=not args.no_desc, width=args.width)

if __name__ == '__main__':
    main()
