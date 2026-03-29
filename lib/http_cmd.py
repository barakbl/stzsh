import sys
import os
import json
import urllib.request
import urllib.error
import xml.etree.ElementTree as ET

BOLD  = '\033[1m'
CYAN  = '\033[96m'
GREEN = '\033[92m'
RED   = '\033[91m'
DIM   = '\033[2m'
RESET = '\033[0m'


def eprint(*args, **kwargs):
    print(*args, **kwargs, file=sys.stderr)


def prompt(label, default=None):
    suffix = f' [{default}]' if default else ''
    try:
        sys.stderr.write(f'{BOLD}{CYAN}{label}{suffix}: {RESET}')
        sys.stderr.flush()
        val = sys.stdin.readline().strip()
    except (EOFError, KeyboardInterrupt):
        eprint()
        sys.exit(0)
    return val or default or ''


def parse_headers(args, start):
    headers = {}
    i = start
    while i < len(args):
        if args[i] == '--header' and i + 1 < len(args):
            key, _, val = args[i + 1].partition(':')
            headers[key.strip()] = val.strip()
            i += 2
        else:
            i += 1
    return headers


def xml_to_dict(elem):
    result = {}
    if elem.attrib:
        result['@attributes'] = dict(elem.attrib)
    children = list(elem)
    if children:
        child_dict = {}
        for child in children:
            val = xml_to_dict(child)
            if child.tag in child_dict:
                existing = child_dict[child.tag]
                if not isinstance(existing, list):
                    child_dict[child.tag] = [existing]
                child_dict[child.tag].append(val)
            else:
                child_dict[child.tag] = val
        result.update(child_dict)
    if elem.text and elem.text.strip():
        text = elem.text.strip()
        result['#text'] = text if result else text
        if not result or list(result.keys()) == ['#text']:
            return text
    return result or ''


def try_parse_xml(raw):
    try:
        root = ET.fromstring(raw)
        return {root.tag: xml_to_dict(root)}
    except ET.ParseError:
        return None


def do_request(method, url, headers=None, body=None):
    data = None
    if body:
        data = body.encode()
        if headers is None:
            headers = {}
        headers.setdefault('Content-Type', 'application/json')

    req = urllib.request.Request(url, data=data, headers=headers or {}, method=method)
    try:
        with urllib.request.urlopen(req) as resp:
            raw = resp.read().decode(errors='replace')
            eprint(f'{BOLD}{GREEN}{resp.status} {resp.reason}{RESET}')
            try:
                parsed = json.loads(raw)
                print(json.dumps(parsed, indent=2))
            except json.JSONDecodeError:
                xml_parsed = try_parse_xml(raw)
                if xml_parsed is not None:
                    eprint(f'{DIM}(xml → json){RESET}')
                    print(json.dumps(xml_parsed, indent=2))
                else:
                    print(raw)
    except urllib.error.HTTPError as e:
        raw = e.read().decode(errors='replace')
        eprint(f'{BOLD}{RED}{e.code} {e.reason}{RESET}')
        try:
            parsed = json.loads(raw)
            print(json.dumps(parsed, indent=2))
        except json.JSONDecodeError:
            xml_parsed = try_parse_xml(raw)
            if xml_parsed is not None:
                eprint(f'{DIM}(xml → json){RESET}')
                print(json.dumps(xml_parsed, indent=2))
            else:
                print(raw)
        sys.exit(1)
    except urllib.error.URLError as e:
        eprint(f'{RED}Error: {e.reason}{RESET}')
        sys.exit(1)


def interactive_mode():
    eprint(f'{BOLD}{CYAN}http interactive shell{RESET} {DIM}(Ctrl-C to exit){RESET}\n')
    method = prompt('method', 'GET').upper()
    url    = prompt('url')
    if not url:
        eprint(f'{RED}url is required{RESET}')
        sys.exit(1)

    headers = {}
    eprint(f'{DIM}add headers as Key: Value (empty line to skip){RESET}')
    while True:
        h = prompt('header')
        if not h:
            break
        key, _, val = h.partition(':')
        if key and val:
            headers[key.strip()] = val.strip()

    body = None
    if method in ('POST', 'PUT', 'PATCH'):
        body = prompt('body (JSON)')

    eprint()
    do_request(method, url, headers or None, body or None)


def main():
    args = sys.argv[1:]

    if not args or args[0] in ('-h', '--help'):
        eprint(f'usage: http <get|post> <url> [--header Key:Value] [--body <json>]')
        eprint(f'       http --interactive')
        sys.exit(0)

    if args[0] == '--interactive':
        interactive_mode()
        return

    subcmd = args[0].upper()
    if subcmd not in ('GET', 'POST', 'PUT', 'PATCH', 'DELETE'):
        eprint(f'{RED}unknown subcommand: {args[0]}{RESET}')
        sys.exit(1)

    if len(args) < 2:
        eprint(f'{RED}url required{RESET}')
        sys.exit(1)

    url     = args[1]
    headers = parse_headers(args[2:], 0)

    body = None
    if '--body' in args:
        idx = args.index('--body')
        if idx + 1 < len(args):
            body = args[idx + 1]

    do_request(subcmd, url, headers or None, body)


if __name__ == '__main__':
    main()
