# Eval cases

`evals.json` contains historical 0.8.2 prompts and remains unchanged. Each case folder named `c3-lang-<legacy-case-name>` overrides its corresponding legacy entry under the skill-creator eval schema. Those folders use C3 0.8.6 prompts and expectations.

The `v086-*` folders add coverage for current language forms, stale standard-library APIs, and source-library workflows. Add new tests as case folders; do not add entries to `evals.json`.

Run `c3c --version` before grading version-sensitive answers. The expected compiler baseline is 0.8.6.
