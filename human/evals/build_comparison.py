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
claude_runs = {}
for r in all_runs:
    if "skill" not in r or "model" not in r:
        continue
    model = r.get("model", "")
    skill = r["skill"]
    if "MiniMax-M3" in model or "minimax" in model.lower():
        minimax_runs[skill] = r
    elif "mimo" in model:
        mimo_runs[skill] = r
    elif "claude" in model or "opus" in model.lower():
        claude_runs[skill] = r

GENERATORS = [
    {"key": "mimo", "label": "mimo-v2.5-pro", "runs": mimo_runs},
    {"key": "minimax", "label": "minimax/MiniMax-M3", "runs": minimax_runs},
    {"key": "claude", "label": "claude/opus", "runs": claude_runs},
]

SKILLS = ["human", "none", "humanizer"]
SKILL_LABELS = {"human": "human", "none": "none (baseline)", "humanizer": "humanizer"}
SKILL_COLORS = {"human": "#2d6a4f", "none": "#9b2226", "humanizer": "#3a5a8c"}

TELL_PATTERNS = [
    (r" — ", "em-dash"), (r"— ", "em-dash"), (r"—", "em-dash"),
    (r"\bserves as\b", "stand-in verb"), (r"\bstands as\b", "stand-in verb"),
    (r"\banchors\b", "stand-in verb"), (r"\bunderpins\b", "stand-in verb"),
    (r"\bnot just\b.*?\bbut\b", "false contrast"),
    (r"\bisn't just\b.*?\bit's\b", "false contrast"),
    (r"\bon the other hand\b", "false balance"),
    (r"\blarge enough\b.*?\byet small enough\b", "false contrast"),
    (r"\ba person, not a queue\b", "false contrast"),
    (r"\bwasn't.*?it was\b", "false contrast"),
    (r"\bsimple on the surface\b.*?\bunder the hood\b", "false contrast"),
    (r"\bhonestly\b", "throat-clearing"), (r"\bgenuinely\b", "throat-clearing"),
    (r"\bfrankly\b", "throat-clearing"), (r"\bthe real question is\b", "throat-clearing"),
    (r"\bwhat really matters\b", "throat-clearing"), (r"\bwhich is their loss\b", "throat-clearing"),
    (r"\bnestled\b", "promotional"), (r"\btucked into\b", "promotional"),
    (r"\bvibrant\b", "promotional"), (r"\bauthentic\b", "promotional"),
    (r"\boffers something rare\b", "promotional"), (r"\bwhat sets us apart\b", "promotional"),
    (r"\bthrilled\b", "promotional"), (r"\bbeating heart\b", "promotional"),
    (r"\b\w+, \w+, and \w+\b", "triad"),
    (r"\bnuanced\b", "analytic"), (r"\bgranular\b", "analytic"),
    (r"\bcomprehensive\b", "analytic"), (r"\bdramatically faster\b", "formulaic"),
    (r"\bdiffer significantly\b", "formulaic"), (r"\bthe key is\b", "formulaic"),
    (r"\bthe trade-off is\b", "formulaic"), (r"\bpaints a nuanced picture\b", "formulaic"),
    (r"\bthat is precisely\b", "meta-commentary"), (r"\bunfiltered\b", "promotional"),
    (r"\bquiet anchor\b", "metaphor"), (r"\bheartbeat\b", "metaphor"),
    (r"\bstudies back\b", "canned attribution"), (r"\bresearch backs\b", "canned attribution"),
    (r"\bevidence-based\b", "stacked compound"),
    (r"\bthe lesson is\b", "closer"), (r"\bclosing a chapter\b", "canned aphorism"),
    (r"\bone of the most\b", "opener"), (r"\bfor over three decades\b", "opener"),
]

def highlight_tells(text):
    t = html.escape(text)
    highlights = []
    for pattern, category in TELL_PATTERNS:
        for m in re.finditer(pattern, t, re.IGNORECASE):
            start, end = m.start(), m.end()
            before = t[:start]
            if before.count("`") % 2 == 1:
                continue
            highlights.append((start, end, category, m.group()))
    highlights.sort()
    merged = []
    for h in highlights:
        if merged and h[0] < merged[-1][1]:
            old = merged[-1]
            merged[-1] = (old[0], max(old[1], h[1]), old[2], old[3])
        else:
            merged.append(h)
    result = t
    for start, end, category, _ in reversed(merged):
        tooltip = html.escape(category)
        replacement = f'<span class="tell" title="{tooltip}">{result[start:end]}</span>'
        result = result[:start] + replacement + result[end:]
    return result

def score_badge(score):
    if score > 80:
        return f'<span class="score pass">{score}</span>'
    elif score >= 80:
        return f'<span class="score borderline">{score}</span>'
    else:
        return f'<span class="score fail">{score}</span>'

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
<title>Human Skill Eval Comparison</title>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #1a1a2e; color: #e0e0e0; padding: 2rem; line-height: 1.6; }
  h1 { text-align: center; margin-bottom: 0.5rem; color: #f0f0f0; font-size: 1.8rem; }
  .subtitle { text-align: center; color: #888; margin-bottom: 1.5rem; font-size: 0.9rem; }

  /* Generator selector */
  .gen-selector { display: flex; justify-content: center; gap: 0.5rem; margin-bottom: 2rem; }
  .gen-btn { padding: 0.6rem 1.5rem; border: 2px solid #333; border-radius: 6px; background: #16213e; color: #aaa; cursor: pointer; font-weight: 600; font-size: 0.85rem; transition: all 0.2s; }
  .gen-btn:hover { border-color: #555; color: #ddd; }
  .gen-btn.active { border-color: #4ea8de; color: #4ea8de; background: rgba(78,168,222,0.1); }

  /* Summary table */
  .summary { width: 100%; border-collapse: collapse; margin-bottom: 2.5rem; }
  .summary th, .summary td { padding: 0.6rem 1rem; text-align: center; border-bottom: 1px solid #333; }
  .summary th { background: #16213e; color: #aaa; font-weight: 600; font-size: 0.85rem; text-transform: uppercase; letter-spacing: 0.05em; }
  .summary td { font-size: 0.9rem; }
  .summary tr:hover { background: #16213e; }
  .skill-label { font-weight: 700; text-align: left !important; }
  .pass-count { font-size: 1.4rem; font-weight: 700; }
  .pass-count.good { color: #52b788; }
  .pass-count.mid { color: #f4a261; }
  .pass-count.bad { color: #e76f51; }

  .case { background: #16213e; border-radius: 8px; margin-bottom: 2rem; overflow: hidden; }
  .case-header { padding: 1rem 1.5rem; background: #0f3460; display: flex; justify-content: space-between; align-items: center; }
  .case-name { font-weight: 700; font-size: 1.1rem; }
  .case-scores { display: flex; gap: 1rem; font-size: 0.85rem; }
  .case-scores .skill-score { display: flex; align-items: center; gap: 0.3rem; }
  .case-scores .dot { width: 8px; height: 8px; border-radius: 50%; display: inline-block; }

  .tabs { display: flex; border-bottom: 2px solid #333; }
  .tab { flex: 1; padding: 0.7rem 1rem; text-align: center; cursor: pointer; font-weight: 600; font-size: 0.85rem; transition: all 0.2s; border-bottom: 3px solid transparent; margin-bottom: -2px; }
  .tab:hover { background: rgba(255,255,255,0.05); }
  .tab.active[data-skill="human"] { border-bottom-color: #52b788; color: #52b788; }
  .tab.active[data-skill="none"] { border-bottom-color: #e76f51; color: #e76f51; }
  .tab.active[data-skill="humanizer"] { border-bottom-color: #4ea8de; color: #4ea8de; }

  .tab-content { display: none; padding: 1.5rem; }
  .tab-content.active { display: block; }
  .attempt-label { font-size: 0.75rem; color: #888; text-transform: uppercase; letter-spacing: 0.08em; margin-bottom: 0.5rem; }
  .attempt-text { white-space: pre-wrap; font-family: 'Charter', 'Georgia', serif; font-size: 0.95rem; line-height: 1.7; color: #d4d4d4; }
  .problems { margin-top: 1rem; font-size: 0.8rem; color: #e76f51; background: rgba(231,111,81,0.1); padding: 0.6rem 0.8rem; border-radius: 4px; border-left: 3px solid #e76f51; }
  .problems .gate { color: #f4a261; }

  .tell { background: rgba(231,111,81,0.2); border-bottom: 1px solid #e76f51; padding: 0.05em 0; cursor: help; transition: background 0.2s; }
  .tell:hover { background: rgba(231,111,81,0.4); }

  .score { display: inline-block; padding: 0.15em 0.5em; border-radius: 4px; font-weight: 700; font-size: 0.85rem; }
  .score.pass { background: rgba(82,183,136,0.2); color: #52b788; }
  .score.borderline { background: rgba(244,162,97,0.2); color: #f4a261; }
  .score.fail { background: rgba(231,111,81,0.2); color: #e76f51; }

  .legend { display: flex; flex-wrap: wrap; gap: 0.8rem; margin-bottom: 2rem; justify-content: center; }
  .legend-item { display: flex; align-items: center; gap: 0.3rem; font-size: 0.75rem; color: #888; }
  .legend-swatch { width: 12px; height: 12px; border-radius: 2px; }
</style>
</head>
<body>

<h1>Human Skill Eval Comparison</h1>
<div class="subtitle">Generator model comparison | Judge: mimo-v2.5-pro | Score > 80 = pass</div>

<div class="gen-selector">
"""

for gen in GENERATORS:
    active = " active" if gen["key"] == "mimo" else ""
    html_out += f'<div class="gen-btn{active}" data-gen="{gen["key"]}">{gen["label"]}</div>\n'

html_out += "</div>\n\n"

# Legend
legend_items = [
    ("em-dash", "#e76f51"), ("stand-in verb", "#e76f51"), ("false contrast", "#f4a261"),
    ("throat-clearing", "#f4a261"), ("promotional", "#e76f51"), ("analytic", "#4ea8de"),
    ("formulaic", "#4ea8de"), ("triad", "#c77dff"), ("meta-commentary", "#c77dff"),
]
html_out += '<div class="legend">\n'
for name, color in legend_items:
    html_out += f'<div class="legend-item"><div class="legend-swatch" style="background:{color};opacity:0.5;"></div>{name}</div>\n'
html_out += "</div>\n\n"

# Summary tables - one per generator
for gen in GENERATORS:
    runs = gen["runs"]
    hidden = ' style="display:none"' if gen["key"] != "mimo" else ""
    gen_key = gen["key"]
    html_out += f'<table class="summary" data-gen="{gen_key}"{hidden}><tr><th>Skill</th><th>Passed</th>'
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
    html_out += '</table>\n\n'

# Case sections
for ci, ref_case in enumerate(cases):
    case_name = ref_case["name"]
    case_id = ref_case["id"]

    html_out += f'<div class="case" id="case-{case_id}">\n'
    html_out += f'<div class="case-header"><span class="case-name">{case_id}. {case_name}</span></div>\n'

    # Tabs
    html_out += '<div class="tabs">\n'
    for skill in SKILLS:
        html_out += f'<div class="tab" data-skill="{skill}" data-case="{case_id}">{SKILL_LABELS[skill]}</div>\n'
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
            if scores:
                worst_idx = scores.index(min(scores))
            else:
                worst_idx = 0
            output = outputs[worst_idx] if worst_idx < len(outputs) else outputs[0]
            score = scores[worst_idx] if worst_idx < len(scores) else 0

            html_out += f'<div class="attempt-label">attempt {worst_idx+1} (worst: {score})</div>\n'
            html_out += f'<div class="attempt-text">{highlight_tells(output)}</div>\n'

            if case_data.get("problems"):
                html_out += '<div class="problems">'
                for p in case_data["problems"]:
                    cls = ' class="gate"' if p.startswith("(gate)") else ""
                    html_out += f'<div{cls}>{html.escape(p)}</div>'
                html_out += '</div>\n'

            html_out += '</div>\n'

    html_out += '</div>\n\n'

# JavaScript
html_out += """
<script>
// Generator selector
document.querySelectorAll('.gen-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    const gen = btn.dataset.gen;
    document.querySelectorAll('.gen-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    // Toggle summary tables
    document.querySelectorAll('.summary').forEach(t => {
      t.style.display = t.dataset.gen === gen ? '' : 'none';
    });
    // Toggle tab contents
    document.querySelectorAll('.tab-content').forEach(tc => {
      if (tc.dataset.gen === gen) {
        tc.style.display = tc.classList.contains('active') ? '' : 'none';
      } else {
        tc.style.display = 'none';
      }
    });
  });
});

// Skill tabs
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
</script>
</body>
</html>
"""

with open("comparison.html", "w") as f:
    f.write(html_out)
print("Written to comparison.html")
