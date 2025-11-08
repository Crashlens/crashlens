#!/usr/bin/env python3
import re, pathlib, sys

root = pathlib.Path('.').resolve()
pattern_decorator = re.compile(r'@click\.command\((?:["\'])guard(?:["\'])\)', re.I)
pattern_def = re.compile(r'def\s+guard\(')

def remove_block(text, start_idx):
    # remove from start_idx until next top-level def/class or EOF
    i = start_idx
    lines = text.splitlines(True)
    # find line index
    line_no = text.count('\n', 0, start_idx)
    # scan forward until we meet a line starting at column 0 with "def " or "class " or another decorator at 0
    for j in range(line_no, len(lines)):
        if re.match(r'^(def |class |@)', lines[j]):
            if j == line_no:
                continue
            return ''.join(lines[:line_no]) + ''.join(lines[j:])
    return ''.join(lines[:line_no])

for p in root.rglob('*.py'):
    txt = p.read_text(encoding='utf8')
    orig = txt
    changed = False
    # remove decorator-based guard command
    for m in pattern_decorator.finditer(txt):
        start = m.start()
        txt = remove_block(txt, start)
        changed = True
