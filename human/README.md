# Human

A skill to help avoid signs of AI writing from your text. Works with any agent.

Inspired by [humanizer](https://github.com/blader/humanizer/tree/main), but developed to be a single instruction that consumes almost no context at all.

The prompt is a single, <200 words paragraph. Can be relayed to subagents at no cost.

## Performance

See the eval results in [the comparison page](https://htmlpreview.github.io/?https://raw.githubusercontent.com/ricardobeat/skills/refs/heads/main/human/evals/comparison.html). Human evals + auto evals by multiple
models. Wins over humanizer (and no skill) with most models, significantly reducing classic AI tells.

## Installation

Install with `npx skills add ricardobeat/skills --skill human`. Symlink method recommended.


