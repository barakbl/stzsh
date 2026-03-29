import json
import sys
import signal

signal.signal(signal.SIGPIPE, signal.SIG_DFL)


def read_json():
    return json.load(sys.stdin)


def write_json(data):
    json.dump(data, sys.stdout, separators=(',', ':'))
    sys.stdout.write('\n')
