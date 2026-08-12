#!/usr/bin/env python3
"""Print the eval run history stored in results.jsonl (oldest first)."""

import json
import os

LOG = os.path.join(os.path.dirname(os.path.abspath(__file__)), "results.jsonl")


def main():
    rows = [json.loads(l) for l in open(LOG) if l.strip()]
    if not rows:
        print("no runs logged yet")
        return 0
    print(f"{'time':<10} {'skill':<10} {'model':<30} {'score':<8} cases")
    for r in rows:
        ts = r["ts"][11:19]
        m = r.get("model", "-")
        per = " ".join(f"{c['id']}:{'P' if c['pass'] else 'F'}" for c in r["cases"])
        print(f"{ts:<10} {r.get('skill','-'):<10} {m:<30} {r['passed']}/{r['total']:<4} {per}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
