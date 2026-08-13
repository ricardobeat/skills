#!/usr/bin/env python3
"""Generate HTML comparison of eval results with multiple generators."""
import json
import re
import html

with open("results.jsonl") as f:
    lines = f.readlines()

# Find runs by model - scan all lines, keep latest per (model, skill)
all_runs = [json.loads(l) for l in lines if l.strip()]

# Split by generator model, keeping only the latest run per (model, skill)
mimo_runs = {}
minimax_runs = {}
opus_runs = {}
sonnet_runs = {}
for r in all_runs:
    if "skill" not in r or "model" not in r:
        continue
    model = r.get("model", "")
    skill = r["skill"]
    if "MiniMax-M3" in model or "minimax" in model.lower():
        minimax_runs[skill] = r
    elif "mimo" in model:
        mimo_runs[skill] = r
    elif "claude/opus" in model or "claude-opus" in model.lower():
        opus_runs[skill] = r
    elif "claude/sonnet" in model or "claude-sonnet" in model.lower():
        sonnet_runs[skill] = r
    elif "claude" in model or "opus" in model.lower():
        # legacy fallback
        opus_runs[skill] = r

GENERATORS = [
    {"key": "mimo", "label": "mimo-v2.5-pro", "runs": mimo_runs},
    {"key": "minimax", "label": "minimax/MiniMax-M3", "runs": minimax_runs},
    {"key": "claude", "label": "claude/opus", "runs": opus_runs},
    {"key": "sonnet", "label": "claude/sonnet", "runs": sonnet_runs},
]

SKILLS = ["human", "none", "humanizer"]
SKILL_LABELS = {"human": "human", "none": "none", "humanizer": "humanizer"}
SKILL_COLORS = {"human": "#2d6a4f", "none": "#9b2226", "humanizer": "#3a5a8c"}

def highlight_tells(text):
    return html.escape(text)


TELL_LABELS = [
    ("em-dash", "#e76f51"),
    ("stand-in verb", "#e76f51"),
    ("false contrast", "#f4a261"),
    ("throat-clearing", "#f4a261"),
    ("promotional", "#e76f51"),
    ("analytic", "#4ea8de"),
    ("formulaic", "#4ea8de"),
    ("triad", "#c77dff"),
    ("meta-commentary", "#c77dff"),
]

def score_badge(score):
    if score > 80:
        return f'<span class="score pass">{score}</span>'
    elif score >= 70:
        return f'<span class="score borderline">{score}</span>'
    else:
        return f'<span class="score fail">{score}</span>'


def score_badge_inner(score):
    cls = "pass" if score > 80 else "borderline" if score >= 70 else "fail"
    return f'<span class="score {cls}">{score}</span>'

def avg_score(scores):
    if not scores:
        return 0
    return sum(scores) / len(scores)

# Build HTML
ref_gen = GENERATORS[0]
ref_runs = ref_gen["runs"]
cases = ref_runs.get(SKILLS[0], {}).get("cases", [])

html_out = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Human Skill Eval Comparison</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Literata:ital,wght@0,400;0,500;1,400&display=swap" rel="stylesheet">
<style>
  :root {
    --bg: #0f1117;
    --surface: #161922;
    --surface-2: #1c2030;
    --border: #262a3a;
    --border-subtle: #1e2233;
    --text: #c9cdd8;
    --text-muted: #6b7194;
    --text-bright: #e8eaf0;
    --green: #34d399;
    --green-dim: rgba(52,211,153,0.12);
    --red: #d44545;
    --red-dim: rgba(212,69,69,0.14);
    --amber: #c79102;
    --amber-dim: rgba(199,145,2,0.14);
    --blue: #60a5fa;
    --blue-dim: rgba(96,165,250,0.12);
    --purple: #a78bfa;
    --purple-dim: rgba(167,139,250,0.12);
    --radius: 12px;
    --radius-sm: 8px;
  }
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    background: var(--bg);
    color: var(--text);
    line-height: 1.6;
    min-height: 100vh;
  }

  .container { max-width: 1100px; margin: 0 auto; padding: 2.5rem 1.75rem; }

  /* Header */
  .header { margin-bottom: 2.5rem; }
  .header h1 {
    font-size: 1.75rem;
    font-weight: 700;
    color: var(--text-bright);
    letter-spacing: -0.025em;
    margin-bottom: 0.35rem;
  }
  .header .subtitle {
    color: var(--text-muted);
    font-size: 0.8125rem;
    font-weight: 400;
  }
  .header .subtitle .sep { color: var(--border); margin: 0 0.5rem; }

  /* Generator selector - pill tabs */
  .gen-selector {
    display: inline-flex;
    gap: 2px;
    margin-bottom: 1.5rem;
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 3px;
  }
  .gen-btn {
    padding: 0.4rem 0.9rem;
    border: none;
    border-radius: 6px;
    background: transparent;
    color: var(--text-muted);
    cursor: pointer;
    font-weight: 500;
    font-size: 0.75rem;
    font-family: inherit;
    transition: all 0.15s ease;
  }
  .gen-btn:hover { color: var(--text); }
  .gen-btn.active {
    color: var(--text-bright);
    background: var(--border);
  }

  /* Summary table */
  .summary-wrap {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    overflow: hidden;
    margin-bottom: 2rem;
  }
  .overall-wrap {
    margin-bottom: 1.25rem;
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    overflow: hidden;
  }
  .overall-table th:first-child,
  .overall-table td:first-child {
    text-align: left !important;
    padding-left: 1.25rem !important;
  }
  .summary { width: 100%; border-collapse: collapse; }
  .summary th {
    padding: 0.6rem 0.75rem;
    text-align: center;
    color: var(--text-muted);
    font-weight: 500;
    font-size: 0.6875rem;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    border-bottom: 1px solid var(--border);
    background: var(--surface-2);
  }
  .summary td {
    padding: 0.65rem 0.75rem;
    text-align: center;
    font-size: 0.8125rem;
    border-bottom: 1px solid var(--border-subtle);
  }
  .summary tr:last-child td { border-bottom: none; }
  .skill-label { font-weight: 600; text-align: left !important; color: var(--text-bright); padding-left: 1.25rem !important; }
  .pass-count { font-size: 0.9375rem; font-weight: 600; font-variant-numeric: tabular-nums; }
  .pass-count.good { color: var(--green); }
  .pass-count.mid { color: var(--amber); }
  .pass-count.bad { color: var(--red); }

  /* Section divider */
  .section-label {
    font-size: 0.6875rem;
    color: var(--text-muted);
    text-transform: uppercase;
    letter-spacing: 0.08em;
    font-weight: 600;
    margin: 2.5rem 0 1rem 0;
    padding-bottom: 0.5rem;
    border-bottom: 1px solid var(--border-subtle);
  }

  /* Case cards */
  .case {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    margin-bottom: 1rem;
    overflow: hidden;
  }
  .case-header {
    padding: 0.75rem 1.25rem;
    background: var(--surface-2);
    display: flex;
    justify-content: space-between;
    align-items: center;
    border-bottom: 1px solid var(--border);
  }
  .case-name { font-weight: 600; font-size: 0.9375rem; color: var(--text-bright); }
  .case-id { color: var(--text-muted); font-weight: 400; margin-right: 0.5rem; font-variant-numeric: tabular-nums; }

  /* Tabs */
  .tabs { display: flex; border-bottom: 1px solid var(--border); padding: 0 1rem; }
  .tab {
    padding: 0.55rem 1rem;
    cursor: pointer;
    font-weight: 500;
    font-size: 0.75rem;
    font-family: inherit;
    transition: color 0.15s;
    border-bottom: 2px solid transparent;
    margin-bottom: -1px;
    color: var(--text-muted);
    background: transparent;
    border-top: none; border-left: none; border-right: none;
    text-transform: uppercase;
    letter-spacing: 0.04em;
  }
  .tab:first-child { padding-left: 0.25rem; }
  .tab:hover { color: var(--text); }
  .tab-mark { font-size: 0.7rem; margin-left: 0.25rem; opacity: 0.6; }
  .tab-mark.pass { color: var(--green); }
  .tab-mark.fail { color: var(--red); }
  .tab.active[data-skill="human"] { border-bottom-color: var(--green); color: var(--green); }
  .tab.active[data-skill="none"] { border-bottom-color: var(--red); color: var(--red); }
  .tab.active[data-skill="humanizer"] { border-bottom-color: var(--blue); color: var(--blue); }

  /* Tab content */
  .tab-content { display: none; padding: 1.25rem; }
  .tab-content.active { display: block; }
  .attempt-text {
    white-space: pre-wrap;
    font-family: -apple-system, BlinkMacSystemFont, 'Inter', sans-serif;
    font-size: 0.875rem;
    line-height: 1.65;
    color: var(--text);
  }
  .footer {
    margin-top: 0.85rem;
    display: flex;
    justify-content: flex-start;
    align-items: center;
    gap: 0.5rem;
    font-size: 0.6875rem;
    color: var(--text-muted);
    text-transform: uppercase;
    letter-spacing: 0.06em;
    font-weight: 600;
  }

  /* AI tell highlights */
  .tell {
    background: var(--red-dim);
    border-bottom: 1px solid rgba(248,113,113,0.35);
    padding: 0 2px;
    cursor: help;
    border-radius: 2px;
    transition: background 0.15s;
  }
  .tell:hover { background: rgba(248,113,113,0.22); }

  /* Tell category labels (below table) */
  .tell-labels {
    margin: 0 0 2rem 0;
    display: flex;
    flex-wrap: wrap;
    gap: 0.4rem;
    align-items: center;
  }
  .tell-label {
    display: inline-flex;
    align-items: center;
    gap: 0.4rem;
    font-size: 0.6875rem;
    color: var(--text-muted);
    background: var(--surface);
    border: 1px solid var(--border-subtle);
    padding: 0.25rem 0.55rem;
    border-radius: 5px;
  }
  .tell-label-dot { width: 7px; height: 7px; border-radius: 2px; }

  /* Score badges */
  .score {
    display: inline-block;
    padding: 0.15em 0.5em;
    border-radius: 5px;
    font-weight: 600;
    font-size: 0.75rem;
    font-variant-numeric: tabular-nums;
    min-width: 2.2em;
  }
  .score.pass { background: var(--green-dim); color: var(--green); }
  .score.borderline { background: var(--amber-dim); color: var(--amber); }
  .score.fail { background: var(--red-dim); color: var(--red); }

  /* Legend */
  .legend {
    display: flex;
    flex-wrap: wrap;
    gap: 0.4rem;
    margin-bottom: 1.5rem;
  }
  .legend-item {
    display: inline-flex;
    align-items: center;
    gap: 0.4rem;
    font-size: 0.6875rem;
    color: var(--text-muted);
    background: var(--surface);
    border: 1px solid var(--border-subtle);
    padding: 0.25rem 0.55rem;
    border-radius: 5px;
  }
  .legend-swatch { width: 7px; height: 7px; border-radius: 2px; }
</style>
</head>
<body>
<div class="container">

<div class="header">
  <h1>Human Skill Eval</h1>
  <div class="subtitle">Comparing generator models <span class="sep">·</span> Judge: mimo-v2.5-pro <span class="sep">·</span> Avg score > 80 = pass</div>
</div>

"""
# Overall summary - one row per generator, three skill columns
overall_rows = []
for gen in GENERATORS:
    runs = gen["runs"]
    row = {"gen": gen, "cells": []}
    for skill in SKILLS:
        if skill in runs:
            run = runs[skill]
            scores_all = []
            for c in run["cases"]:
                scores_all.extend(c.get("scores", []))
            if scores_all:
                avg = sum(scores_all) / len(scores_all)
                passed = sum(1 for c in run["cases"] if avg_score(c.get("scores", [])) > 80)
                total = len(run["cases"])
                row["cells"].append({"avg": avg, "passed": passed, "total": total})
            else:
                row["cells"].append(None)
        else:
            row["cells"].append(None)
    overall_rows.append(row)

html_out += '<div class="overall-wrap"><table class="summary overall-table"><tr><th>Generator</th>'
for skill in SKILLS:
    html_out += f'<th>{SKILL_LABELS[skill]}</th>'
html_out += '</tr>\n'
for row in overall_rows:
    html_out += f'<tr><td class="skill-label">{row["gen"]["label"]}</td>'
    for cell in row["cells"]:
        if cell is None:
            html_out += '<td><span class="pass-count bad">—</span></td>'
        else:
            passed = cell["passed"]
            total = cell["total"]
            pc = "good" if passed >= 7 else "mid" if passed >= 4 else "bad"
            html_out += f'<td><span class="pass-count {pc}">{passed}/{total}</span></td>'
    html_out += '</tr>\n'
html_out += '</table></div>\n\n'

html_out += '<div class="gen-selector">\n'
for gen in GENERATORS:
    active = " active" if gen["key"] == "mimo" else ""
    html_out += f'<div class="gen-btn{active}" data-gen="{gen["key"]}">{gen["label"]}</div>\n'
html_out += "</div>\n\n"

# Summary tables - one per generator
for gen in GENERATORS:
    runs = gen["runs"]
    hidden = ' style="display:none"' if gen["key"] != "mimo" else ""
    gen_key = gen["key"]
    html_out += f'<div class="summary-wrap" data-gen="{gen_key}"{hidden}><table class="summary"><tr><th>Skill</th><th>Passed</th>'
    for ci in range(len(cases)):
        case_name = cases[ci]["name"]
        html_out += f'<th>{case_name}</th>'
    html_out += '</tr>\n'
    for skill in SKILLS:
        if skill not in runs:
            continue
        run = runs[skill]
        total_cases = len(run["cases"])
        passed = sum(1 for c in run["cases"] if avg_score(c.get("scores", [])) > 80)
        pc = "good" if passed >= 7 else "mid" if passed >= 4 else "bad"
        html_out += f'<tr><td class="skill-label" style="color:{SKILL_COLORS[skill]}">{SKILL_LABELS[skill]}</td>'
        html_out += f'<td><span class="pass-count {pc}">{passed}/{total_cases}</span></td>'
        for c in run["cases"]:
            scores = c.get("scores", [])
            avg = round(avg_score(scores))
            html_out += f'<td>{score_badge(avg)}</td>'
        html_out += '</tr>\n'
    html_out += '</table></div>\n\n'

# Labels below all tables
html_out += '<div class="tell-labels">'
for label, color in TELL_LABELS:
    html_out += f'<span class="tell-label"><span class="tell-label-dot" style="background:{color};opacity:0.5;"></span>{label}</span>'
html_out += "</div>\n\n"

# Pre-compute all pass data: pass_data[gen_key][case_id][skill] = bool
pass_data = {}
for gen in GENERATORS:
    pass_data[gen["key"]] = {}
    for ci in range(len(cases)):
        case_id = cases[ci]["id"]
        pass_data[gen["key"]][case_id] = {}
        for skill in SKILLS:
            if skill in gen["runs"] and len(gen["runs"][skill]["cases"]) > ci:
                cs = gen["runs"][skill]["cases"][ci]
                avg = avg_score(cs.get("scores", []))
                pass_data[gen["key"]][case_id][skill] = avg > 80

# Case sections
html_out += '<div class="section-label">Cases</div>\n'
for ci, ref_case in enumerate(cases):
    case_name = ref_case["name"]
    case_id = ref_case["id"]

    # Add pass data as JSON for JS to read
    html_out += f'<script type="application/json" class="case-data" data-cid="{case_id}">{json.dumps(pass_data)}</script>\n'

    html_out += f'<div class="case" id="case-{case_id}">\n'
    html_out += f'<div class="case-header"><span class="case-name"><span class="case-id">{case_id}.</span>{case_name}</span></div>\n'

    # Tabs
    html_out += '<div class="tabs">\n'
    for skill in SKILLS:
        html_out += f'<div class="tab" data-skill="{skill}" data-case="{case_id}">{SKILL_LABELS[skill]} <span class="tab-mark"></span></div>\n'
    html_out += '</div>\n'

    # Tab contents - one set per generator
    for skill in SKILLS:
        for gen in GENERATORS:
            runs = gen["runs"]
            if skill not in runs:
                continue
            case_data = runs[skill]["cases"][ci]
            is_first_gen = gen["key"] == "mimo"
            is_first_skill = skill == "human"
            active = " active" if is_first_gen and is_first_skill else ""
            hidden = "" if is_first_gen else ' style="display:none"'

            html_out += f'<div class="tab-content{active}" data-skill="{skill}" data-case="{case_id}" data-gen="{gen["key"]}"{hidden}>\n'

            scores = case_data.get("scores", [])
            outputs = case_data["outputs"]
            # show the best attempt, but score the cell on the average of all
            if scores:
                best_idx = scores.index(max(scores))
            else:
                best_idx = 0
            output = outputs[best_idx] if best_idx < len(outputs) else outputs[0]
            score = round(avg_score(scores))
            whys = case_data.get("whys", [])
            if not whys:
                notes = case_data.get("notes", [])
                whys = [n.get("note", "") for n in notes]
            why = whys[best_idx] if best_idx < len(whys) else ""

            html_out += f'<div class="attempt-text">{highlight_tells(output)}</div>\n'

            if score <= 80:
                html_out += '<div class="footer"><span>Score:</span><span class="footer-score">' + score_badge_inner(score) + '</span></div>\n'

            html_out += '</div>\n'

    html_out += '</div>\n\n'

# JavaScript
html_out += """
</div>
<script>
// Parse all case-data JSON blocks into a map
const passData = {};
document.querySelectorAll('script.case-data').forEach(el => {
  Object.assign(passData, JSON.parse(el.textContent));
});

function updateMarks(gen) {
  document.querySelectorAll('.tab').forEach(tab => {
    const cid = tab.dataset.case;
    const skill = tab.dataset.skill;
    const passed = passData[gen] && passData[gen][cid] && passData[gen][cid][skill];
    const markSpan = tab.querySelector('.tab-mark');
    if (markSpan) {
      markSpan.textContent = passed ? '✓' : '✗';
      markSpan.className = 'tab-mark ' + (passed ? 'pass' : 'fail');
    }
  });
}

document.querySelectorAll('.gen-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    const gen = btn.dataset.gen;
    document.querySelectorAll('.gen-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    document.querySelectorAll('.summary-wrap').forEach(t => {
      t.style.display = t.dataset.gen === gen ? '' : 'none';
    });
    // Reset all cases: activate first tab for new generator
    document.querySelectorAll('.case').forEach(caseEl => {
      const tabs = caseEl.querySelectorAll('.tab');
      tabs.forEach(t => t.classList.remove('active'));
      tabs[0].classList.add('active');
      caseEl.querySelectorAll('.tab-content').forEach(tc => {
        const match = tc.dataset.gen === gen && tc.dataset.skill === tabs[0].dataset.skill;
        tc.classList.toggle('active', match);
        tc.style.display = match ? '' : 'none';
      });
    });
    updateMarks(gen);
  });
});

document.querySelectorAll('.tab').forEach(tab => {
  tab.addEventListener('click', () => {
    const caseId = tab.dataset.case;
    const skill = tab.dataset.skill;
    const activeGen = document.querySelector('.gen-btn.active').dataset.gen;
    tab.parentElement.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
    tab.classList.add('active');
    const caseEl = tab.closest('.case');
    caseEl.querySelectorAll('.tab-content').forEach(tc => {
      const match = tc.dataset.skill === skill && tc.dataset.case === caseId && tc.dataset.gen === activeGen;
      tc.classList.toggle('active', match);
      tc.style.display = match ? '' : 'none';
    });
  });
});

// Initial marks
updateMarks('mimo');
</script>
</body>
</html>
"""

with open("comparison.html", "w") as f:
    f.write(html_out)
print("Written to comparison.html")
