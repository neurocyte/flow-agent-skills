#!/usr/bin/env python3
"""Show an info box when the user's cursor reaches a given line in flow.

Usage: follow-info-boxes.py [--connect SERVER] [--timeout SECONDS] ENTRIES.json

ENTRIES.json is a list of {"path": PATH, "line": LINE, "markdown": TEXT}.
PATH is absolute or relative to the project directory, LINE is 1-based.
When the primary cursor or a selection of an editor moves onto LINE of PATH,
the script shows TEXT as markdown in an info box at that cursor. It shows
the box again only after the cursor leaves the entry. The script stops when
flow quits, when the timeout ends, or when it gets SIGTERM.

Needs flow v0.7.2-2165 or later (follow_editors, info boxes that stay open
while the view scrolls).
"""

import argparse
import json
import os
import signal
import subprocess
import sys
import tempfile
import time


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--connect")
    parser.add_argument("--timeout", type=float, default=1800)
    parser.add_argument("entries")
    args = parser.parse_args()
    connect = ["--connect", args.connect] if args.connect else []

    def flow(*cmd, stdin=subprocess.DEVNULL):
        result = subprocess.run(["flow", *connect, "--json", *cmd], stdin=stdin, capture_output=True, text=True)
        replies = [json.loads(line)["reply"] for line in result.stdout.splitlines() if line.startswith("{")]
        return [r for r in replies if r != "ok"], result.returncode

    info, rc = flow("--exec", "get_instance_info")
    if rc != 0 or not info:
        sys.exit("follow-info-boxes: cannot connect to flow")
    project = info[0][2]

    def absolute(path):
        return path if os.path.isabs(path) else os.path.normpath(os.path.join(project, path))

    entries = {}
    with open(args.entries) as f:
        for entry in json.load(f):
            entries[(absolute(entry["path"]), entry["line"])] = entry["markdown"]

    buffer_paths = {}

    def buffer_path(bufid):
        if bufid not in buffer_paths:
            for r in flow("--exec", "get_buffers")[0]:
                buffer_paths[r[1][1]] = absolute(r[2])
        return buffer_paths.get(bufid)

    work = tempfile.mkdtemp(prefix="flow-follow-")
    count = 0

    def show(markdown):
        nonlocal count
        count += 1
        name = f"*follow-{os.getpid()}-{count}*"
        md = os.path.join(work, "box.md")
        script = os.path.join(work, "box.flow")
        with open(md, "w") as f:
            f.write(markdown)
        with open(script, "w") as f:
            f.write(f'show_info_box "{name}"\ndelete_buffer "{name}"\n')
        with open(md) as f:
            _, rc = flow("--no-wait", "--scratch", "--hidden", "--file-name", name, "--exec-file", script, stdin=f)
        if rc != 0:
            flow("--exec", f"delete_buffer:{name}")

    stream = subprocess.Popen(["flow", *connect, "--keep-open", "--json", "--exec", "follow_editors"],
                              stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, text=True)
    end = time.monotonic() + args.timeout
    last = None
    signal.signal(signal.SIGTERM, lambda *_: sys.exit(0))
    try:
        for line in stream.stdout:
            if time.monotonic() > end:
                break
            if not line.startswith("{"):
                continue
            reply = json.loads(line)["reply"]
            if reply == "ok" or reply[0] != "editor":
                continue
            _, bufid, _, event = reply
            if bufid is None:
                continue
            kind = event[1]
            if kind == "open" and event[2]:
                buffer_paths[bufid[1]] = absolute(event[2])
                continue
            if kind == "pos":
                row = event[3]
            elif kind == "sel" and event[2] != "none":
                row = event[2]
            else:
                continue
            key = (buffer_path(bufid[1]), row + 1)
            if key not in entries:
                last = None
            elif key != last:
                last = key
                show(entries[key])
    except KeyboardInterrupt:
        pass
    finally:
        stream.terminate()


if __name__ == "__main__":
    main()
