# human

A skill that makes an agent write like a person.

It is one paragraph of context. No tooling, no post-processing pass, no
rewriter mode. You add it to an agent and everything the agent writes comes out
plainer: fewer em dashes, fewer "stands as a testament to", fewer closing lines
that restate the paragraph above them. It applies to prose, code comments and
documentation alike.

## Install

```
npx skills add ricardobeat/skills/human
```

## What it does

The paragraph tells the model to say the thing and stop. Don't greet the
reader, don't announce what you're about to do. Plain verb over impressive one.
Leave a small fact small. Keep every name and number you were given and invent
none. Let sentence length wander instead of settling into a rhythm.

Most of it is a list of tells to avoid, because that is what actually moves the
output: triads, contrasts that resolve too neatly ("not just X, it's Y"),
throat-clearing, promotional words like "vibrant" and "nestled", and claims
about caring or quality with nothing in them to check.

## Results

`evals/comparison.html` scores nine generated-writing cases across four models,
under three conditions: with `human`, with nothing, and with
[humanizer](https://github.com/ricardobeat/skills) as a comparison. Two judges
scored the same outputs blind and shuffled, on human-likeness only.

Cases passed out of 9, judged by mimo-v2.5-pro:

| Generator | human | none | humanizer |
|---|---|---|---|
| mimo-v2.5-pro | 7 | 0 | 1 |
| minimax/MiniMax-M3 | 0 | 0 | 0 |
| claude/opus | 3 | 0 | 2 |
| claude/sonnet | 9 | 3 | 9 |

Same outputs, judged by claude-opus-5:

| Generator | human | none | humanizer |
|---|---|---|---|
| mimo-v2.5-pro | 5 | 0 | 1 |
| minimax/MiniMax-M3 | 6 | 0 | 0 |
| claude/opus | 2 | 0 | 0 |
| claude/sonnet | 7 | 5 | 6 |

The baseline is the clearest part: with no skill, three of the four generators
pass nothing at all under either judge. Sonnet is the exception and passes 3
and 5 unaided.

`human` beats or ties `humanizer` in every cell except sonnet-under-mimo, where
both hit 9/9. The two judges disagree enough that individual cells should not
be read too closely. Mimo gives minimax a 0 where opus gives it 6, and mimo
scores opus's own output at 3 where opus scores it 2. What survives both judges
is the ordering: human above humanizer, humanizer above nothing.

Opus is the weakest generator here under both judges, 3 and 2. I don't have a
good explanation for that.

Open `evals/comparison.html` to read the actual rewrites with the detected
tells highlighted. The numbers are less interesting than the text.

## Running the evals

```
python3 evals/score.py human "<model line>"
python3 evals/build_comparison.py
```

Results append to `evals/results.jsonl`, one record per run, tagged with the
skill and eval SHAs so old rows stay interpretable after the prompt changes.
