#!/usr/bin/env python3
"""Score the `human` skill evals.

Runs each eval case through `crush run` in a scratch directory whose crushrc
exposes only the skill under test, then grades the output two ways:

1. Hard gates (objective, still enforced):
   - required substrings must be present (names, numbers, dates)
   - no em/en dashes anywhere
2. LLM judgment (the main signal): a neutral judge model grades each
   rewrite for human-likeness, AI tells, fabrication, and fact preservation.

Usage: score.py [human|humanizer]
"""

import datetime
import hashlib
import json
import os
import re
import subprocess
import sys

EVALS_JSON = os.path.join(os.path.dirname(os.path.abspath(__file__)), "evals.json")
RESULTS_LOG = os.path.join(os.path.dirname(os.path.abspath(__file__)), "results.jsonl")
SKILL_MD = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "SKILL.md"
)
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKILLS_ROOT = os.path.dirname(REPO_ROOT)  # dir that contains human/ as a skill
ATTEMPTS = 5  # rewrites per case; majority pass wins (LLM output is stochastic)

JUDGE_PROMPT = """You are a strict writing judge. Below is an ORIGINAL text and several rewrites of it. Grade each rewrite harshly, the way a discerning reader would.

ORIGINAL:
{source}

REWRITES:
{rewrites}

For EACH rewrite decide:
- "human": does it read like a person wrote it? Varied rhythm, plain verbs, specific detail, natural voice. NOT formulaic triads, NOT promotional puff, NOT chatbot framing ("I hope this helps", "Here is an overview"), NOT aphorism formulas ("the real question is", "what really matters"), NOT vacuous send-offs ("the future looks bright", "a step in the right direction").
- "tells": does it contain obvious AI tells? Em/en dashes, words like delve/tapestry/testament/vibrant/showcasing, rule of three, piled-up "Moreover/Additionally", excessive hedging, passive subjectless fragments, narration about loading skills or following instructions.
- "fabrication": does it invent a specific factual claim NOT present in the original, such as a name, number, date, place, event, or verifiable statement about the world? Opinions, reactions, metaphors, and turns of phrase are voice, NOT fabrication.
- "preserves": do the original's key facts (names, numbers, dates, and its main claims) survive the rewrite?

Also grade the ORIGINAL itself as "0" the same way, so we can sanity-check your judgment.

Return ONLY a single JSON object, no prose, no markdown fences, in exactly this shape:
{{"0": {{"human": true, "tells": true, "fabrication": false, "preserves": true, "why": "one short sentence"}}, "1": {{...}}, "2": {{...}}, "3": {{...}}}}
"""


def skill_hash(skill="human"):
    if skill == "humanizer":
        path = os.path.expanduser("~/.config/crush/skills/humanizer/SKILL.md")
    else:
        path = SKILL_MD
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()[:12]


def load_evals():
    with open(EVALS_JSON) as fh:
        return json.load(fh)["evals"]


NARRATION_META = re.compile(
    r"\b(skill|load|loading|loaded|view|apply|applies|matches?|relevant|"
    r"guidance|procedure|instruction|system reminder|todo)\b",
    re.IGNORECASE,
)


def strip_narration(text: str) -> str:
    """MiniMax-M3 sometimes emits chain-of-thought about loading/applying the
    skill as visible text before the actual rewrite (e.g. 'The human skill
    matches this task. Loading it.' or '<system>Load skill</system>'). Cut any
    leading run of short meta-commentary sentences; the judge then grades the
    rewrite itself."""
    text = re.sub(r"<system>.*?</system>", "", text, flags=re.IGNORECASE | re.DOTALL)
    segments = re.split(r"(?<=[.!?])\s*", text.strip())
    kept = []
    cut = 0
    for seg in segments:
        seg = seg.strip()
        if not seg:
            continue
        if cut < 5 and len(seg) < 160 and NARRATION_META.search(seg):
            cut += 1
            continue
        kept.append(seg)
    return " ".join(kept)


def strip_trailer(text: str) -> str:
    """Remove the Crush attribution trailer if the model/config adds one."""
    for marker in ("Generated with Crush", "Assisted by Crush", "Assisted-by: Crush"):
        idx = text.find(marker)
        if idx != -1:
            text = text[:idx]
    return text.strip()


def run_crush(prompt, workdir):
    proc = subprocess.run(
        ["crush", "run", prompt],
        cwd=workdir,
        capture_output=True,
        text=True,
        timeout=600,
    )
    return proc.stdout + "\n" + proc.stderr


def extract_json(text):
    """Pull the first balanced JSON object out of arbitrary model output."""
    start = text.find("{")
    if start == -1:
        return None
    depth, in_str, esc = 0, False, False
    for i in range(start, len(text)):
        ch = text[i]
        if in_str:
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == '"':
                in_str = False
        else:
            if ch == '"':
                in_str = True
            elif ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    try:
                        return json.loads(text[start : i + 1])
                    except json.JSONDecodeError:
                        return None
    return None


def hard_gates(case, output):
    """Objective checks. Return (ok, problems)."""
    problems = []
    out_low = output.lower()
    for need in case.get("checks", {}).get("required", []):
        if isinstance(need, dict):
            alts = [a.lower() for a in need.get("any", [])]
            if not any(a in out_low for a in alts):
                problems.append(f"required missing (any of): {alts!r}")
        elif need.lower() not in out_low:
            problems.append(f"required missing: {need!r}")
    for em in ("—", "–"):
        if em in output:
            problems.append(f"em/en dash present: {em!r}")
    if not output:
        problems.append("empty output")
    return (not problems, problems)


def judge_one(source, output, judge_workdir):
    """LLM-judge a single rewrite. Returns (verdict dict, parse_ok)."""
    prompt = JUDGE_PROMPT.format(source=source, rewrites=f"1. {output}")
    for _ in range(2):  # retry once on unparseable output
        raw = run_crush(prompt, judge_workdir)
        data = extract_json(raw)
        if data:
            return data.get("1", {}), True
    return {}, False


def setup_workdir(base, skill):
    os.makedirs(base, exist_ok=True)
    if skill == "human":
        skill_path, disable = SKILLS_ROOT, "humanizer"
    elif skill == "humanizer":
        skill_path = os.path.expanduser("~/.config/crush/skills")
        disable = "human"
    else:
        raise SystemExit(f"unknown skill: {skill}")
    with open(os.path.join(base, "crushrc"), "w") as fh:
        fh.write(f'option skill-path "{skill_path}"\n')
        fh.write(f"option disable-skill {disable}\n")
        fh.write("model large minimax/MiniMax-M3 --reasoning-effort minimal\n")
        fh.write("permissions allow view ls grep edit bash write\n")


def main():
    skill = sys.argv[1] if len(sys.argv) > 1 else "human"
    workdir = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".scratch")
    judge_dir = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), ".scratch-judge"
    )
    setup_workdir(workdir, skill)
    # judge must be neutral: no skills loaded
    os.makedirs(judge_dir, exist_ok=True)
    with open(os.path.join(judge_dir, "crushrc"), "w") as fh:
        fh.write("option disable-skill humanizer\n")
        fh.write("option disable-skill human\n")
        fh.write("model large minimax/MiniMax-M3 --reasoning-effort minimal\n")
        fh.write("permissions allow view ls grep edit bash write\n")

    cases = load_evals()
    results = []
    for case in cases:
        source = case.get("source", "") or case["prompt"].split("\n\n", 1)[1]
        outputs = [
            strip_narration(strip_trailer(run_crush(case["prompt"], workdir)))
            for _ in range(ATTEMPTS)
        ]
        gates = [hard_gates(case, o) for o in outputs]
        passes = 0
        problems = []
        for i, (out, (gok, gprobs)) in enumerate(zip(outputs, gates)):
            v, parse_ok = judge_one(source, out, judge_dir)
            # 3 of 4 judge criteria must hold (dampens judge noise)
            criteria = [
                v.get("human") is True,
                v.get("tells") is False,
                v.get("fabrication") is False,
                v.get("preserves") is True,
            ]
            ok = gok and parse_ok and sum(criteria) >= 3
            if ok:
                passes += 1
            else:
                probs = list(gprobs)
                if not parse_ok:
                    probs.append("judge verdict missing")
                for k, want in (
                    ("human", True),
                    ("tells", False),
                    ("fabrication", False),
                    ("preserves", True),
                ):
                    if v.get(k) is not want:
                        probs.append(f"judge: {k}={v.get(k)} (want {want})")
                        why = v.get("why")
                        if why:
                            probs.append(f"      judge said: {why}")
                problems = probs
        passed = passes >= (ATTEMPTS + 1) // 2
        results.append((case, passed, problems, outputs))
        status = "PASS" if passed else "FAIL"
        print(f"[{status}] {case['id']} {case['name']} ({passes}/{ATTEMPTS})")
        if not passed:
            for p in problems:
                print(f"        - {p}")

    failed = [r for r in results if not r[1]]
    print(f"\n{len(results) - len(failed)}/{len(results)} passed")

    record = {
        "ts": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "skill": skill,
        "model": "minimax/MiniMax-M3 (reasoning minimal)",
        "skill_sha": skill_hash(skill),
        "passed": len(results) - len(failed),
        "total": len(results),
        "cases": [
            {
                "id": r[0]["id"],
                "name": r[0]["name"],
                "pass": r[1],
                "problems": r[2],
                "outputs": r[3],
            }
            for r in results
        ],
    }
    with open(RESULTS_LOG, "a") as fh:
        fh.write(json.dumps(record) + "\n")
    print(f"logged -> {RESULTS_LOG} (skill_sha={record['skill_sha']})")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
