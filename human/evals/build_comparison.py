#!/usr/bin/env python3
"""Generate HTML comparison of eval results with multiple generators and judges."""
import json
import re
import html
import os

HERE = os.path.dirname(os.path.abspath(__file__))
results_path = os.path.join(HERE, "results.jsonl")

with open(results_path) as f:
    lines = f.readlines()

all_runs = [json.loads(l) for l in lines if l.strip()]

JUDGES = [
    {"key": "mimo", "label": "Mimo v2.5 Pro"},
    {"key": "opus", "label": "Claude Opus"},
]

GENERATORS = [
    {"key": "mimo", "label": "mimo-v2.5-pro"},
    {"key": "minimax", "label": "minimax/MiniMax-M3"},
    {"key": "claude", "label": "claude/opus"},
    {"key": "sonnet", "label": "claude/sonnet"},
]

SKILLS = ["human", "none", "humanizer"]
SKILL_LABELS = {"human": "human", "none": "none", "humanizer": "humanizer"}
SKILL_COLORS = {"human": "#2d6a4f", "none": "#9b2226", "humanizer": "#3a5a8c"}

runs_by_judge = {"mimo": {}, "opus": {}}

for r in all_runs:
    if "skill" not in r or "model" not in r:
        continue
    model = r.get("model", "")
    skill = r["skill"]
    judge_raw = r.get("judge", "")

    if judge_raw and "opus" in str(judge_raw).lower():
        j_key = "opus"
    else:
        j_key = "mimo"

    if "MiniMax-M3" in model or "minimax" in model.lower():
        g_key = "minimax"
    elif "mimo" in model.lower():
        g_key = "mimo"
    elif "claude/sonnet" in model.lower() or "claude-sonnet" in model.lower():
        g_key = "sonnet"
    elif "claude/opus" in model.lower() or "claude-opus" in model.lower() or "claude" in model.lower():
        g_key = "claude"
    else:
        continue

    if g_key not in runs_by_judge[j_key]:
        runs_by_judge[j_key][g_key] = {}
    runs_by_judge[j_key][g_key][skill] = r


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


# Case definitions reference
cases = runs_by_judge["mimo"]["mimo"]["human"]["cases"]

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
  .header { margin-bottom: 2rem; }
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

  /* Selectors row */
  .selectors-bar {
    display: flex;
    flex-wrap: wrap;
    gap: 1.5rem;
    align-items: center;
    margin-bottom: 1.5rem;
  }
  .selector-group {
    display: inline-flex;
    align-items: center;
    gap: 0.6rem;
  }
  .selector-label {
    font-size: 0.75rem;
    font-weight: 600;
    color: var(--text-muted);
    text-transform: uppercase;
    letter-spacing: 0.05em;
  }
  .pill-tabs {
    display: inline-flex;
    gap: 2px;
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 3px;
  }
  .pill-btn {
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
  .pill-btn:hover { color: var(--text); }
  .pill-btn.active {
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
  <div class="subtitle">Comparing generator models <span class="sep">·</span> Avg score > 80 = pass</div>
</div>

<div class="selectors-bar">
  <div class="selector-group">
    <span class="selector-label">Judge:</span>
    <div class="pill-tabs">
"""

for j in JUDGES:
    active = " active" if j["key"] == "mimo" else ""
    html_out += f'      <button class="pill-btn judge-btn{active}" data-judge="{j["key"]}">{j["label"]}</button>\n'

html_out += """    </div>
  </div>
  <div class="selector-group">
    <span class="selector-label">Generator:</span>
    <div class="pill-tabs">
"""

for gen in GENERATORS:
    active = " active" if gen["key"] == "mimo" else ""
    html_out += f'      <button class="pill-btn gen-btn{active}" data-gen="{gen["key"]}">{gen["label"]}</button>\n'

html_out += """    </div>
  </div>
</div>

"""

# Overall summary tables - one per judge
for j in JUDGES:
    jk = j["key"]
    hidden = ' style="display:none"' if jk != "mimo" else ""
    html_out += f'<div class="overall-wrap" data-judge="{jk}"{hidden}><table class="summary overall-table"><tr><th>Generator</th>'
    for skill in SKILLS:
        html_out += f'<th>{SKILL_LABELS[skill]}</th>'
    html_out += '</tr>\n'

    for gen in GENERATORS:
        gk = gen["key"]
        runs = runs_by_judge.get(jk, {}).get(gk, {})
        html_out += f'<tr><td class="skill-label">{gen["label"]}</td>'
        for skill in SKILLS:
            if skill in runs:
                run = runs[skill]
                passed = sum(1 for c in run["cases"] if avg_score(c.get("scores", [])) > 80)
                total = len(run["cases"])
                pc = "good" if passed >= 7 else "mid" if passed >= 4 else "bad"
                html_out += f'<td><span class="pass-count {pc}">{passed}/{total}</span></td>'
            else:
                html_out += '<td><span class="pass-count bad">—</span></td>'
        html_out += '</tr>\n'
    html_out += '</table></div>\n\n'

# Summary tables - one per (judge, generator) combination
for j in JUDGES:
    jk = j["key"]
    for gen in GENERATORS:
        gk = gen["key"]
        runs = runs_by_judge.get(jk, {}).get(gk, {})
        hidden = ' style="display:none"' if (jk != "mimo" or gk != "mimo") else ""
        html_out += f'<div class="summary-wrap" data-judge="{jk}" data-gen="{gk}"{hidden}><table class="summary"><tr><th>Skill</th><th>Passed</th>'
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

# Pre-compute pass_data: pass_data[judge_key][gen_key][case_id][skill] = bool
pass_data = {}
for j in JUDGES:
    jk = j["key"]
    pass_data[jk] = {}
    for gen in GENERATORS:
        gk = gen["key"]
        pass_data[jk][gk] = {}
        for ci in range(len(cases)):
            case_id = cases[ci]["id"]
            pass_data[jk][gk][case_id] = {}
            for skill in SKILLS:
                run = runs_by_judge.get(jk, {}).get(gk, {}).get(skill, {})
                if run and len(run.get("cases", [])) > ci:
                    cs = run["cases"][ci]
                    avg = avg_score(cs.get("scores", []))
                    pass_data[jk][gk][case_id][skill] = avg > 80
                else:
                    pass_data[jk][gk][case_id][skill] = False

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

    # Tab contents - one set per (judge, generator, skill)
    for skill in SKILLS:
        for j in JUDGES:
            jk = j["key"]
            for gen in GENERATORS:
                gk = gen["key"]
                run = runs_by_judge.get(jk, {}).get(gk, {}).get(skill, {})
                if not run or len(run.get("cases", [])) <= ci:
                    continue
                case_data = run["cases"][ci]

                is_active = (jk == "mimo" and gk == "mimo" and skill == "human")
                active_cls = " active" if is_active else ""
                hidden = "" if is_active else ' style="display:none"'

                html_out += f'<div class="tab-content{active_cls}" data-judge="{jk}" data-gen="{gk}" data-skill="{skill}" data-case="{case_id}"{hidden}>\n'

                scores = case_data.get("scores", [])
                outputs = case_data["outputs"]
                if scores:
                    best_idx = scores.index(max(scores))
                else:
                    best_idx = 0
                output = outputs[best_idx] if best_idx < len(outputs) else outputs[0]
                score = round(avg_score(scores))

                html_out += f'<div class="attempt-text">{highlight_tells(output)}</div>\n'

                if score <= 80:
                    html_out += '<div class="footer"><span>Score:</span><span class="footer-score">' + score_badge_inner(score) + '</span></div>\n'

                html_out += '</div>\n'

    html_out += '</div>\n\n'

# JavaScript
html_out += """
</div>
<script>
let activeJudge = 'mimo';
let activeGen = 'mimo';

const passData = {};
document.querySelectorAll('script.case-data').forEach(el => {
  Object.assign(passData, JSON.parse(el.textContent));
});

function updateUI() {
  // 1. Overall table visibility
  document.querySelectorAll('.overall-wrap').forEach(el => {
    el.style.display = el.dataset.judge === activeJudge ? '' : 'none';
  });

  // 2. Generator summary table visibility
  document.querySelectorAll('.summary-wrap').forEach(el => {
    el.style.display = (el.dataset.judge === activeJudge && el.dataset.gen === activeGen) ? '' : 'none';
  });

  // 3. Update tab marks (check/cross) for all cases
  document.querySelectorAll('.tab').forEach(tab => {
    const cid = tab.dataset.case;
    const skill = tab.dataset.skill;
    const passed = passData[activeJudge] && passData[activeJudge][activeGen] && passData[activeJudge][activeGen][cid] && passData[activeJudge][activeGen][cid][skill];
    const markSpan = tab.querySelector('.tab-mark');
    if (markSpan) {
      markSpan.textContent = passed ? '✓' : '✗';
      markSpan.className = 'tab-mark ' + (passed ? 'pass' : 'fail');
    }
  });

  // 4. Update tab content visibility for each case
  document.querySelectorAll('.case').forEach(caseEl => {
    const activeTab = caseEl.querySelector('.tab.active');
    const activeSkill = activeTab ? activeTab.dataset.skill : 'human';
    caseEl.querySelectorAll('.tab-content').forEach(tc => {
      const match = tc.dataset.judge === activeJudge && tc.dataset.gen === activeGen && tc.dataset.skill === activeSkill;
      tc.classList.toggle('active', match);
      tc.style.display = match ? '' : 'none';
    });
  });
}

document.querySelectorAll('.judge-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    activeJudge = btn.dataset.judge;
    document.querySelectorAll('.judge-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    updateUI();
  });
});

document.querySelectorAll('.gen-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    activeGen = btn.dataset.gen;
    document.querySelectorAll('.gen-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    updateUI();
  });
});

document.querySelectorAll('.tab').forEach(tab => {
  tab.addEventListener('click', () => {
    const caseEl = tab.closest('.case');
    caseEl.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
    tab.classList.add('active');
    updateUI();
  });
});

// Set initial active tabs on cases
document.querySelectorAll('.case').forEach(caseEl => {
  const tabs = caseEl.querySelectorAll('.tab');
  if (tabs.length > 0 && !caseEl.querySelector('.tab.active')) {
    tabs[0].classList.add('active');
  }
});

updateUI();
</script>
</body>
</html>
"""

out_path = os.path.join(HERE, "comparison.html")
with open(out_path, "w") as f:
    f.write(html_out)
print(f"Written to {out_path}")
