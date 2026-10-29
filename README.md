# AI test gate

A CI quality gate for the parts of your product that an AI model answers.
It runs next to Sonar, not instead of it.

Sonar checks the code.
This gate checks what the model actually says.

## Why a different kind of gate

Static analysis can't tell you what a prompt will do. You have to run it.

And AI answers vary. The same prompt can give different answers on identical runs, even at temperature 0 ([Atil et al., 2024](https://arxiv.org/abs/2408.04667) found accuracy varying by up to 15% between identical runs).
So "one red test fails the build" doesn't work: the build would be flaky for ever.

This gate does what you already do for latency: it measures a distribution and sets tolerances.

- Every test case runs several times (`--repeat 5`).
- **Overall pass rate** must stay above a threshold (default 90%).
- **No single case** may drop below a floor (default 60%), so one broken behaviour can't hide inside a good average.
- **Stability** (how often a case gives its most common answer) is reported, and can be gated too.

| What you know | What it becomes for AI |
|---|---|
| Unit test | Test case with properties the answer must have, not an exact string |
| Quality gate | Pass rate at or above a threshold, over repeated runs |
| SAST / security rules | Prompt-injection and data-leak cases (see `tests/triage.yaml`) |
| Flaky test | Normal behaviour: measure it, don't hide it |

## What's in here

```
promptfooconfig.yaml          the eval: prompt, model, shared checks
prompts/triage.txt            example prompt: support-ticket triage, JSON out
tests/triage.yaml             test cases: correctness, priority, injection, card-number leak
providers/mock_model.py       a deliberately unreliable mock model (no API key, no cost)
providers/local-openai-compatible.yaml   llama.cpp / vLLM / Ollama
scripts/gate.py               reads the results and passes or fails the build
.github/workflows/ai-test-gate.yml        GitHub Actions: Sonar + AI test gate
.gitlab-ci.yml                GitLab CI: Sonar + AI test gate
```

The tests use [promptfoo](https://www.promptfoo.dev/) (MIT licence), which needs Node.js 22.22 or later. Recent promptfoo versions already print a "repeat stability" summary. The gate turns those numbers into a pass or fail the pipeline can act on. It is plain Python with no dependencies.

## Try it in two minutes (no API key)

```sh
npx promptfoo@0.125.1 eval --repeat 5 --no-cache -o results.json
python3 scripts/gate.py results.json
```

The mock model gets about 5% of answers wrong on purpose, so the gate passes.
Make it worse and watch the gate fail:

```sh
MOCK_ERROR_RATE=0.3 npx promptfoo@0.125.1 eval --repeat 5 --no-cache -o results.json
python3 scripts/gate.py results.json
```

## Use a real model

Pass `--providers` (or set the `PROMPTFOO_PROVIDERS` variable in CI):

```sh
# A model you host (llama.cpp llama-server, vLLM, Ollama): edit apiBaseUrl first
npx promptfoo@0.125.1 eval --repeat 5 -o results.json --providers file://providers/local-openai-compatible.yaml

# Hosted models (set OPENAI_API_KEY or ANTHROPIC_API_KEY)
npx promptfoo@0.125.1 eval --repeat 5 -o results.json --providers openai:chat:YOUR_MODEL
npx promptfoo@0.125.1 eval --repeat 5 -o results.json --providers anthropic:messages:claude-haiku-5-5
```

Check provider IDs against the [promptfoo provider docs](https://www.promptfoo.dev/docs/providers/) for your version.

## In CI

- **GitHub Actions**: `.github/workflows/ai-test-gate.yml`. Add `SONAR_TOKEN` (and `SONAR_HOST_URL` for SonarQube Server) to enable the Sonar job. Add the repository variable `PROMPTFOO_PROVIDERS` and the model's API key secret to test a real model. The gate writes its table to the job summary.
- **GitLab CI**: `.gitlab-ci.yml`. Same variables, as CI/CD variables.

## Make it yours

1. Replace `prompts/triage.txt` with your prompt.
2. Write 10-30 cases in `tests/`: the common path, the edge cases, and the ones that would embarrass you (injection, leaks, refusals).
3. Run it a few times against your real model, then set thresholds a little below what it achieves today.
4. Every time something goes wrong in production, add it as a case. The suite gets better each time something breaks.

Testing before release is half the job. The other half is monitoring the answers in production. That's the next template.

---

From [Netlinux](https://netlinux.co.uk). We build AI that is understood, built properly and still running next year.
MIT licence.
