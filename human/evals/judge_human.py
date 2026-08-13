#!/usr/bin/env python3
"""Run the eval pipeline with a HUMAN as the judge.

Blind comparison is the default: outputs from several skills are shuffled and
presented with no hint of which skill produced them; you grade blindly and
per-skill scores are revealed at the end. Style-only: no hard gates.

Options (all named):
  --model "provider/id [flags]"   crush model line under test
  --skills a,b,c                  skills to compare (default none,human,humanizer;
                                  a single name judges one skill only)
  --evals FILE                    eval file (default: generation suite)
  --attempts N                    responses per case (default 1)
  --seed N                        shuffle seed for a reproducible order

Answer 'y' if the output reads like a person wrote it, 'n' otherwise.
"""

import argparse
import concurrent.futures
import datetime
import json
import os
import random
import re
import sys
import termios
import tty

import score  # reuse the machinery from score.py

DEFAULT_SKILLS = "none,human,humanizer"


def gen_one(skill, model, case):
    """Generate a single response for one (skill, case) on demand."""
    slug = re.sub(r"[^A-Za-z0-9]+", "-", model).strip("-").lower()
    here = os.path.dirname(os.path.abspath(__file__))
    workdir = os.path.join(here, f".scratch-{slug}-{skill}")
    score.setup_workdir(workdir, skill, model)
    return score.strip_narration(score.strip_trailer(score.run_generation(case["prompt"], skill, model, workdir)))


def read_key():
    """Read a single keypress without waiting for Enter.

    Falls back to line input when stdin is not a tty (piped or redirected),
    so the script still runs unattended.
    """
    if not sys.stdin.isatty():
        return (sys.stdin.readline() or "q").strip().lower()[:1]
    fd = sys.stdin.fileno()
    saved = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        ch = sys.stdin.read(1)
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, saved)
    if ch in ("\x03", "\x04"):  # ctrl-c, ctrl-d
        raise KeyboardInterrupt
    return ch.lower()


def ask(idx, total, out):
    print("\033[2J\033[H", end="")  # clear screen, cursor home
    print("=" * 72)
    print(f"OUTPUT {idx}/{total}")
    print("=" * 72)
    print(f"\n{out}\n")
    while True:
        print("Reads human? [y/n] ", end="", flush=True)
        key = read_key()
        if key in ("y", "n"):
            break
        print("\r\033[K", end="")  # unrecognized key; redraw the prompt
    ok = key == "y"
    print(key)
    note = ""
    if not ok:
        note = input("  one-line reason (optional): ").strip()
    return ok, note


def main():
    parser = argparse.ArgumentParser(description="Blind human judging of the skill evals.")
    parser.add_argument("--model", default=score.DEFAULT_MODEL,
                        help="crush model line, e.g. 'opencode-go/deepseek-v4-flash'")
    parser.add_argument("--skills", default=DEFAULT_SKILLS,
                        help="comma-separated skills to compare; a single name judges one skill")
    parser.add_argument("--evals", default=score.GEN_EVALS_JSON,
                        help="eval file (default: generation suite)")
    parser.add_argument("--attempts", type=int, default=1,
                        help="responses per case (default 1)")
    parser.add_argument("--seed", type=int, default=None,
                        help="shuffle seed for a reproducible order")
    a = parser.parse_args()

    model = a.model
    skills = [s for s in a.skills.split(",") if s]
    blind = len(skills) > 1
    attempts = a.attempts
    seed = a.seed
    evals_path = a.evals
    suite = "gen" if "gen" in os.path.basename(evals_path) else "rewrite"
    cases = score.load_evals(evals_path)

    if blind and seed is not None:
        random.seed(seed)
    print(f"judging skills={skills!r} model={model!r} suite={suite} attempts={attempts} blind={blind}")

    # plan: shuffled (skill, case) pairs; each response is generated on
    # demand, right before it is graded
    plan = [
        (s, case)
        for s in skills
        for case in cases
        for _ in range(attempts)
    ]
    if blind:
        random.shuffle(plan)

    def gen_pair(pair):
        s, case = pair
        return s, case, gen_one(s, model, case)

    judged = []  # (skill, case, ok, note, output)
    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as ex:
            future = ex.submit(gen_pair, plan[0])
            for i, _ in enumerate(plan, 1):
                s, case, out = future.result()
                # pre-generate the next response while the user reads this one
                if i < len(plan):
                    future = ex.submit(gen_pair, plan[i])
                ok, note = ask(i, len(plan), out)
                judged.append((s, case, ok, note, out))
    except KeyboardInterrupt:
        print("\naborted; scoring what was judged so far")

    # per-skill tally
    summary = {}
    for s in skills:
        rows = [j for j in judged if j[0] == s]
        passed = sum(1 for j in rows if j[2])
        summary[s] = {"passed": passed, "total": len(rows),
                      "cases": [(j[1]["id"], j[2], j[3]) for j in rows]}

    print(f"\n{'=' * 72}\nSCORES")
    for s in skills:
        sm = summary[s]
        print(f"{s:<10} {sm['passed']}/{sm['total']}")

    # log one record per skill (skip skills that never got judged)
    for s in skills:
        sm = summary[s]
        if sm["total"] == 0:
            continue
        record = {
            "ts": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "skill": s,
            "model": model,
            "skill_sha": score.skill_hash(s),
            "evals_sha": score.file_hash(evals_path),
            "suite": suite,
            "judge": "human-interactive-blind" if blind else "human-interactive",
            "mode": "full",
            "attempts": attempts,
            "passed": sm["passed"],
            "total": sm["total"],
            "cases": [
                {
                    "id": case["id"],
                    "name": case["name"],
                    "pass": ok,
                    "problems": [],
                    "notes": [{"note": note}],
                    "outputs": [out],
                }
                for (s2, case, ok, note, out) in judged
                if s2 == s
            ],
        }
        with open(score.RESULTS_LOG, "a") as fh:
            fh.write(json.dumps(record) + "\n")
    print(f"logged -> {score.RESULTS_LOG} (judge=human-interactive{'blind' if blind else ''})")


if __name__ == "__main__":
    sys.exit(main())
