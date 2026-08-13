#!/usr/bin/env python3
"""Score the `human` skill evals.

Runs each eval case through `crush run` in a scratch directory whose crushrc
exposes only the skill under test, then grades the output two ways:

1. Hard gates (objective): required substrings must be present, no em/en
   dashes anywhere.
2. LLM judgment (the main signal): a neutral judge model grades each output
   on ONE question only: does it read like a person or like an AI?

Two suites: rewrite (evals.json) and generation (evals-gen.json).

Usage:
  score.py [human|humanizer|none] [model line] [--quick] [--evals=FILE]
"""

import concurrent.futures
import datetime
import hashlib
import json
import os
import re
import subprocess
import sys

DEFAULT_MODEL = "minimax/MiniMax-M3 --reasoning-effort minimal"
JUDGE_MODEL = "opencode-go/deepseek-v4-pro"

EVALS_JSON = os.path.join(os.path.dirname(os.path.abspath(__file__)), "evals.json")
GEN_EVALS_JSON = os.path.join(os.path.dirname(os.path.abspath(__file__)), "evals-gen.json")
RESULTS_LOG = os.path.join(os.path.dirname(os.path.abspath(__file__)), "results.jsonl")
SKILL_MD = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "SKILL.md"
)
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKILLS_ROOT = os.path.dirname(REPO_ROOT)  # dir that contains human/ as a skill
ATTEMPTS = 2  # rewrites per case; 5 cases x 2 = 10 rewrites + 10 judge calls
WORKERS = 10  # concurrent crush invocations (rewrites and judges each run as a batch)

JUDGE_PROMPT = """You are a strict writing judge. Below is an ORIGINAL text and several rewrites of it. Grade each rewrite on a single 0-100 score: how human does it read?

ORIGINAL:
{source}

REWRITES:
{rewrites}

Scoring guide:
- 0-20: Obviously AI. Every sentence has tells: promotional puff, formulaic triads, chatbot framing, canned aphorisms, em-dash clusters, throat-clearing filler.
- 20-40: Heavy AI patterns. Corporate synonyms, balanced false contrasts, stand-in verbs ("serves as"), "not just X, it's Y" formulas, rule-of-three lists, vacuous send-offs.
- 40-60: Mixed. Some human qualities but clear AI fingerprints: analytic vocabulary, tutor voice, synthesis closers, meta-commentary on the prose, or promotional travel filler.
- 60-75: Mostly human but with noticeable AI residue. A stray em-dash cluster, a throat-clearing opener, a false contrast, or a stand-in verb that a person wouldn't use.
- 75-85: Reads mostly human. Minor tells: one or two phrases that feel slightly formulaic or hedged, but the voice is largely natural.
- 85-100: Reads like a person wrote it. Varied rhythm, plain verbs, specific detail, natural voice. No promotional puff, no chatbot framing, no canned aphorisms, no formulaic structures.

Current-model fingerprints count heavily: em-dash clusters; balanced false contrasts ("it's not X, it's Y", "not just X, but Y", "more than just X", "less like X, more like Y", "what was once X has become Y"); meta-commentary on the prose itself ("that is precisely what", "worth chasing", "how it lands"); conversational filler as throat-clearing ("honestly", "frankly", "to be honest", "genuinely"); Claude-isms ("load-bearing", "quietly does", "the actual X"); literary hedging ("on balance", "one could argue", "it's worth noting"); analytic vocabulary (comprehensive, nuanced, fundamentally, paradigm, in essence, robust, essentially); tutor/guide voice ("let's break this down", "here's the thing", "let me walk you through"); false balance ("on one hand... on the other hand"); paragraph-final synthesis closers ("taken together, these factors suggest that"); systematic rule-of-three triads; stand-in verbs instead of plain "is" ("serves as", "stands as", "marks", "represents"); throat-clearing openers ("in today's X world", "one of the most", "it's important to note", "at its core"); corporate synonyms (utilise, initiate, commence, facilitate, "poised to"); stacked compound-noun phrases ("evidence-based policymaking", "cost-effective solutions"); empty authenticity or travel filler ("off-the-beaten-path experience", "authentic", "gateway to"); canned attribution ("industry reports say"); and narration about loading skills or following instructions. Older ChatGPT-era tells (delve, tapestry, "I hope this helps", piled-up "Moreover/Additionally") count if present but are no longer the main signal. A single stray instance is not a failure, but two or more distinct tell categories in one response means the score should drop below 85.

Do not consider factual accuracy, completeness, or invention at all. Only style and voice.

Also score a plain, neutral, unadorned restatement of the task as "0", so we can sanity-check your judgment.

Return ONLY a single JSON object, no prose, no markdown fences, in exactly this shape:
{{"0": {{"score": 50, "why": "one short sentence"}}, "1": {{"score": 85, "why": "one short sentence"}}, "2": {{"score": 90, "why": "one short sentence"}}}}
"""

JUDGE_PROMPT_GEN = """You are a strict writing judge. Below is a WRITING TASK and several responses to it. Grade each response on a single 0-100 score: how human does it read?

WRITING TASK:
{task}

RESPONSES:
{rewrites}

Scoring guide:
- 0-20: Obviously AI. Every sentence has tells: promotional puff, formulaic triads, chatbot framing, canned aphorisms, em-dash clusters, throat-clearing filler.
- 20-40: Heavy AI patterns. Corporate synonyms, balanced false contrasts, stand-in verbs ("serves as"), "not just X, it's Y" formulas, rule-of-three lists, vacuous send-offs.
- 40-60: Mixed. Some human qualities but clear AI fingerprints: analytic vocabulary, tutor voice, synthesis closers, meta-commentary on the prose, or promotional travel filler.
- 60-75: Mostly human but with noticeable AI residue. A stray em-dash cluster, a throat-clearing opener, a false contrast, or a stand-in verb that a person wouldn't use.
- 75-85: Reads mostly human. Minor tells: one or two phrases that feel slightly formulaic or hedged, but the voice is largely natural.
- 85-100: Reads like a person wrote it. Varied rhythm, plain verbs, specific detail, natural voice. No promotional puff, no chatbot framing, no canned aphorisms, no formulaic structures.

Current-model fingerprints count heavily: em-dash clusters; balanced false contrasts ("it's not X, it's Y", "not just X, but Y", "more than just X", "less like X, more like Y", "what was once X has become Y"); meta-commentary on the prose itself ("that is precisely what", "worth chasing", "how it lands"); conversational filler as throat-clearing ("honestly", "frankly", "to be honest", "genuinely"); Claude-isms ("load-bearing", "quietly does", "the actual X"); literary hedging ("on balance", "one could argue", "it's worth noting"); analytic vocabulary (comprehensive, nuanced, fundamentally, paradigm, in essence, robust, essentially); tutor/guide voice ("let's break this down", "here's the thing", "let me walk you through"); false balance ("on one hand... on the other hand"); paragraph-final synthesis closers ("taken together, these factors suggest that"); systematic rule-of-three triads; stand-in verbs instead of plain "is" ("serves as", "stands as", "marks", "represents"); throat-clearing openers ("in today's X world", "one of the most", "it's important to note", "at its core"); corporate synonyms (utilise, initiate, commence, facilitate, "poised to"); stacked compound-noun phrases ("evidence-based policymaking", "cost-effective solutions"); empty authenticity or travel filler ("off-the-beaten-path experience", "authentic", "gateway to"); canned attribution ("industry reports say"); and narration about loading skills or following instructions. Older ChatGPT-era tells (delve, tapestry, "I hope this helps", piled-up "Moreover/Additionally") count if present but are no longer the main signal. A single stray instance is not a failure, but two or more distinct tell categories in one response means the score should drop below 85.

Do not consider factual accuracy, completeness, or invention at all. Only style and voice.

Also score a plain, neutral, unadorned restatement of the task as "0", so we can sanity-check your judgment.

Return ONLY a single JSON object, no prose, no markdown fences, in exactly this shape:
{{"0": {{"score": 50, "why": "one short sentence"}}, "1": {{"score": 85, "why": "one short sentence"}}, "2": {{"score": 90, "why": "one short sentence"}}}}
"""


def file_hash(path):
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()[:12]


def skill_hash(skill="human"):
    if skill == "humanizer":
        path = os.path.expanduser("~/.config/crush/skills/humanizer/SKILL.md")
    elif skill == "none":
        return "none"  # no skill loaded; baseline
    else:
        path = SKILL_MD
    return file_hash(path)


def load_evals(path):
    with open(path) as fh:
        return json.load(fh)["evals"]


NARRATION_META = re.compile(
    r"\b(skill|load|loading|loaded|view|apply|applies|matches?|relevant|"
    r"guidance|procedure|instruction|system reminder|todo)\b",
    re.IGNORECASE,
)


def strip_narration(text: str) -> str:
    """Some models emit chain-of-thought about loading/applying the skill as
    visible text before the actual output (e.g. 'The human skill matches this
    task. Loading it.' or '<system>Load skill</system>'). Cut any leading run
    of short meta-commentary sentences; the judge then grades the output
    itself."""
    text = re.sub(r"<system>.*?</system>", "", text, flags=re.IGNORECASE | re.DOTALL)
    # Sentence-splitting mangles code (redis.get -> "redis. get") and drops
    # short lines like `def f():`. Strip narration only from the prose before
    # the first fence, and pass the code through untouched.
    fence = text.find("```")
    if fence != -1:
        head, code = text[:fence], text[fence:]
        return (strip_narration(head) + "\n\n" + code.strip()).strip()
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


CLAUDE_RE = re.compile(r"^claude/")

_SKILL_TEXT = {}


def skill_text(skill):
    """Body of the skill (frontmatter and heading stripped) for injection."""
    if skill not in _SKILL_TEXT:
        if skill == "humanizer":
            path = os.path.expanduser("~/.config/crush/skills/humanizer/SKILL.md")
        else:
            path = SKILL_MD
        raw = open(path).read()
        if raw.startswith("---"):
            raw = raw.split("---", 2)[2]
        _SKILL_TEXT[skill] = raw.strip()
    return _SKILL_TEXT[skill]


def run_generation(prompt, skill, model, workdir):
    """Generate one response.

    Claude (`claude/sonnet`, `claude/opus`, ...) is run with the `claude` CLI
    (`claude -p`) directly; the skill under test is injected as context.
    Everything else goes through `crush run` in the scratch dir with the skill
    loaded.
    """
    if CLAUDE_RE.match(model.strip().split()[0]):
        claude_model = model.strip().split()[0].split("/", 1)[1]
        if skill in ("human", "humanizer"):
            prompt = skill_text(skill) + "\n\n" + prompt
        proc = subprocess.run(
            ["claude", "-p", "--model", claude_model, prompt],
            capture_output=True,
            text=True,
            timeout=600,
        )
        return proc.stdout + "\n" + proc.stderr
    proc = subprocess.run(
        ["crush", "run", prompt],
        cwd=workdir,
        capture_output=True,
        text=True,
        timeout=600,
    )
    return proc.stdout + "\n" + proc.stderr


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


# Unambiguous AI-ism patterns: a single hit fails the hard gate.
TELL_STRONG = [
    "more than just", "honestly", "frankly", "to be honest", "genuinely",
    "truthfully", "load-bearing", "the real question is", "what really matters",
    "on balance", "one could argue", "it's worth noting", "at its core",
    "let's break this down", "here's the thing", "let me walk you through",
    "taken together", "in today's", "delve", "tapestry", "testament to",
    "off-the-beaten-path", "evidence-based", "showcas", "nestled", "vibrant",
]
# Context-dependent: only fails when two or more distinct ones co-occur.
TELL_WEAK = [
    "not just", "not only", "serves as", "stands as", "on one hand",
    "on the other hand", "used to be", "it's important to note",
    "one of the most", "endeavor", "facilitate", "comprehensive",
    "nuanced", "paradigm", "fundamentally", "quietly",
]


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
    for pat in TELL_STRONG:
        if pat in out_low:
            problems.append(f"AI tell (strong): {pat!r}")
    weak_hits = [p for p in TELL_WEAK if p in out_low]
    if len(weak_hits) >= 2:
        problems.append(f"AI tells (cluster): {weak_hits!r}")
    if not output:
        problems.append("empty output")
    return (not problems, problems)


def judge_one(prompt_text, judge_workdir):
    """LLM-judge a single output. Returns (verdict dict, parse_ok)."""
    for _ in range(2):  # retry once on unparseable output
        raw = run_crush(prompt_text, judge_workdir)
        data = extract_json(raw)
        if data:
            return data.get("1", {}), True
    return {}, False


def setup_workdir(base, skill, model):
    os.makedirs(base, exist_ok=True)
    if skill == "human":
        skill_path, disable = SKILLS_ROOT, "humanizer"
    elif skill == "humanizer":
        skill_path = os.path.expanduser("~/.config/crush/skills")
        disable = "human"
    elif skill == "none":
        skill_path, disable = None, None  # baseline: no skill visible
    else:
        raise SystemExit(f"unknown skill: {skill}")
    with open(os.path.join(base, "crushrc"), "w") as fh:
        if skill_path:
            fh.write(f'option skill-path "{skill_path}"\n')
        if disable:
            fh.write(f"option disable-skill {disable}\n")
        if skill == "none":
            fh.write("option disable-skill human\n")
            fh.write("option disable-skill humanizer\n")
        fh.write(f"model large {model}\n")
        fh.write("permissions allow view ls grep edit bash write\n")


def main():
    skill = sys.argv[1] if len(sys.argv) > 1 else "human"
    model = sys.argv[2] if len(sys.argv) > 2 else DEFAULT_MODEL
    quick = False
    global ATTEMPTS
    evals_path = GEN_EVALS_JSON  # generation suite is the default
    for a in sys.argv[3:]:
        if a == "--quick":
            quick = True
        elif a.startswith("--evals="):
            evals_path = a.split("=", 1)[1]
        elif a.startswith("--attempts="):
            ATTEMPTS = int(a.split("=", 1)[1])
    suite = "gen" if "gen" in os.path.basename(evals_path) else "rewrite"
    slug = re.sub(r"[^A-Za-z0-9]+", "-", model).strip("-").lower()
    here = os.path.dirname(os.path.abspath(__file__))
    workdir = os.path.join(here, f".scratch-{slug}")
    judge_dir = os.path.join(here, f".scratch-judge-{slug}")
    setup_workdir(workdir, skill, model)
    # judge must be neutral: no skills loaded, and pinned so scores are
    # comparable across models under test
    os.makedirs(judge_dir, exist_ok=True)
    with open(os.path.join(judge_dir, "crushrc"), "w") as fh:
        fh.write("option disable-skill humanizer\n")
        fh.write("option disable-skill human\n")
        fh.write(f"model large {JUDGE_MODEL}\n")
        fh.write("permissions allow view ls grep edit bash write\n")

    cases = load_evals(evals_path)
    if quick:
        cases = [c for c in cases if c["id"] in (3, 4)]

    def rewrite(case):
        return strip_narration(strip_trailer(run_crush(case["prompt"], workdir)))

    def judge(task):
        case, out = task
        if suite == "gen":
            prompt = JUDGE_PROMPT_GEN.format(task=case["prompt"], rewrites=f"1. {out}")
        else:
            source = case.get("source", "") or case["prompt"].split("\n\n", 1)[1]
            prompt = JUDGE_PROMPT.format(source=source, rewrites=f"1. {out}")
        return judge_one(prompt, judge_dir)

    # phase 1: all rewrites in parallel; phase 2: all judgments in parallel
    with concurrent.futures.ThreadPoolExecutor(max_workers=WORKERS) as ex:
        flat_outputs = list(ex.map(rewrite, [c for c in cases for _ in range(ATTEMPTS)]))
    tasks = [
        (case, flat_outputs[ci * ATTEMPTS + ai])
        for ci, case in enumerate(cases)
        for ai in range(ATTEMPTS)
    ]
    with concurrent.futures.ThreadPoolExecutor(max_workers=WORKERS) as ex:
        flat_verdicts = list(ex.map(judge, tasks))

    results = []
    for ci, case in enumerate(cases):
        outputs = flat_outputs[ci * ATTEMPTS : (ci + 1) * ATTEMPTS]
        verdicts = flat_verdicts[ci * ATTEMPTS : (ci + 1) * ATTEMPTS]
        gates = [hard_gates(case, o) for o in outputs]
        passes = 0
        problems = []
        scores = []
        problems = []
        for out, (gok, gprobs), (v, parse_ok) in zip(outputs, gates, verdicts):
            score = v.get("score", 0) if parse_ok else 0
            scores.append(score)
            if not parse_ok:
                problems.append("judge verdict missing")
            if gprobs:
                problems.extend(f"(gate) {p}" for p in gprobs)
        avg = sum(scores) / len(scores) if scores else 0
        passed = avg > 80
        results.append((case, passed, problems, outputs, scores))
        status = "PASS" if passed else "FAIL"
        print(f"[{status}] {case['id']} {case['name']} avg={avg:.0f} scores={scores}")
        if not passed:
            for p in problems:
                print(f"        - {p}")

    failed = [r for r in results if not r[1]]
    print(f"\n{len(results) - len(failed)}/{len(results)} passed")

    record = {
        "ts": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "skill": skill,
        "model": model,
        "skill_sha": skill_hash(skill),
        "evals_sha": file_hash(evals_path),
        "suite": suite,
        "mode": "quick" if quick else "full",
        "attempts": ATTEMPTS,
        "passed": len(results) - len(failed),
        "total": len(results),
        "cases": [
            {
                "id": r[0]["id"],
                "name": r[0]["name"],
                "pass": r[1],
                "scores": r[4],
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
