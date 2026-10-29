#!/usr/bin/env python3
"""AI test gate: pass or fail a build from promptfoo results.

A traditional test suite fails on one red test. AI answers vary between
identical runs, so this gate runs each case several times (promptfoo
--repeat) and checks rates instead:

  --min-pass-rate       share of all runs that passed       (default 0.90)
  --min-case-pass-rate  floor for any single test case      (default 0.60)
  --min-stability       share of runs giving a case's most
                        common answer; 0 reports only       (default 0)

Usage: gate.py results.json [options]
Exit code 0 = gate passed, 1 = gate failed, 2 = bad input.
"""

import argparse
import collections
import json
import os
import sys


def load_runs(path):
    with open(path) as f:
        data = json.load(f)
    results = data.get("results", data)
    if isinstance(results, dict):
        results = results.get("results", [])
    if not results:
        sys.exit("gate: no results found in " + path)
    runs = []
    for r in results:
        case = (r.get("testCase") or {}).get("description") or "test %s" % r.get("testIdx")
        output = (r.get("response") or {}).get("output")
        runs.append({
            "case": case,
            "passed": bool(r.get("success")) and not r.get("error"),
            "output": output if isinstance(output, str) else json.dumps(output),
        })
    return runs


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("results")
    ap.add_argument("--min-pass-rate", type=float, default=0.90)
    ap.add_argument("--min-case-pass-rate", type=float, default=0.60)
    ap.add_argument("--min-stability", type=float, default=0.0)
    args = ap.parse_args()

    try:
        runs = load_runs(args.results)
    except (OSError, ValueError) as e:
        print("gate: cannot read results: %s" % e, file=sys.stderr)
        return 2

    by_case = collections.OrderedDict()
    for run in runs:
        by_case.setdefault(run["case"], []).append(run)

    total_pass = sum(r["passed"] for r in runs)
    pass_rate = total_pass / len(runs)
    problems = []
    rows = []
    for case, case_runs in by_case.items():
        n = len(case_runs)
        case_rate = sum(r["passed"] for r in case_runs) / n
        top = collections.Counter(r["output"] for r in case_runs).most_common(1)[0][1]
        stability = top / n
        flag = ""
        if case_rate < args.min_case_pass_rate:
            flag = "FAIL"
            problems.append("'%s' passed %.0f%% of runs (floor %.0f%%)" % (case, 100 * case_rate, 100 * args.min_case_pass_rate))
        if args.min_stability and stability < args.min_stability:
            flag = "FAIL"
            problems.append("'%s' gave its most common answer in %.0f%% of runs (floor %.0f%%)" % (case, 100 * stability, 100 * args.min_stability))
        rows.append("| %s | %d | %.0f%% | %.0f%% | %s |" % (case, n, 100 * case_rate, 100 * stability, flag))
    if pass_rate < args.min_pass_rate:
        problems.insert(0, "overall pass rate %.1f%% is below %.0f%%" % (100 * pass_rate, 100 * args.min_pass_rate))

    verdict = "FAILED" if problems else "PASSED"
    lines = [
        "## AI test gate: %s" % verdict,
        "",
        "Overall: %d of %d runs passed (%.1f%%); threshold %.0f%%." % (total_pass, len(runs), 100 * pass_rate, 100 * args.min_pass_rate),
        "",
        "| Test case | Runs | Passed | Stability | |",
        "|---|---|---|---|---|",
    ] + rows
    if problems:
        lines += ["", "Why it failed:"] + ["- " + p for p in problems]
    report = "\n".join(lines)
    print(report)

    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a") as f:
            f.write(report + "\n")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
