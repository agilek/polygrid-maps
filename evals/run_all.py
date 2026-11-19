#!/usr/bin/env python3
"""One-command regression runner: `npm run evals [-- --quick] [-- --only trigger|quality|followups]`.

Runs trigger evals (3 runs/query; 1 with --quick), quality.json (skill mode; a subset with --quick),
followups.json (both modes), prints one summary and writes results/latest.md.
Raw transcripts go to results/raw/ (gitignored). QUALITY AND FOLLOWUPS PUBLISH REAL MAPS (~20 + ~16 creates; --quick ~5 + ~8).
"""
import argparse, json, os, subprocess, sys, datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
RAW = HERE / "results" / "raw"
QUICK_QUALITY = "1,4,5,9,11"
QUICK_FOLLOWUPS = "101,102,105"


def env():
    return {k: v for k, v in os.environ.items() if k != "CLAUDECODE"}


def run_trigger(a):
    proj = RAW / "trigger-proj"
    (proj / ".claude").mkdir(parents=True, exist_ok=True)
    tdir = HERE / "trigger"
    e = env(); e["PYTHONPATH"] = str(tdir)
    p = subprocess.run([sys.executable, "-m", "scripts.run_eval", "--eval-set", str(tdir / "trigger.json"),
                        "--skill-path", str(HERE.parent / "skills" / "create-map"), "--model", a.model,
                        "--num-workers", "8", "--runs-per-query", "1" if a.quick else "3"],
                       cwd=proj, env=e, capture_output=True, text=True)
    try:
        d = json.loads(p.stdout)
    except ValueError:
        return {"error": p.stderr[-500:]}
    (RAW / "trigger.json").write_text(json.dumps(d, indent=1))
    return trig_summary(d)


def trig_summary(d):
    r = d["results"]
    tp = sum(1 for x in r if x["should_trigger"] and x["pass"]); pos = sum(1 for x in r if x["should_trigger"])
    tn = sum(1 for x in r if not x["should_trigger"] and x["pass"]); neg = len(r) - pos
    fp = neg - tn
    prec = tp / (tp + fp) if tp + fp else 1.0
    return {"total": len(r), "passed": d["summary"]["passed"], "recall": tp / max(1, pos), "precision": prec,
            "fails": [f"{'MISS' if x['should_trigger'] else 'FALSE+'} ({x['triggers']}/{x['runs']}): {x['query'][:90]}" for x in r if not x["pass"]]}


def run_q(a, file, mode, only, sub):
    out = RAW / sub
    cmd = [sys.executable, str(HERE / "run_quality.py"), "--out", str(out), "--file", file, "--mode", mode,
           "--model", a.model, "--grader-model", a.model, "--max-creates", str(a.max_creates)]
    if only:
        cmd += ["--only", only]
    if a.regrade:
        cmd += ["--regrade"]
    p = subprocess.run(cmd, env=env(), capture_output=True, text=True)
    rows = []
    for g in sorted(out.glob("eval-*/grading.json")):
        d = json.loads(g.read_text())
        ex = d["expectations"]
        rows.append({"id": d["eval_id"], "name": d["name"], "mode": d.get("mode", "skill"), "creates": d["creates"],
                     "pngs": d.get("png_calls", 0), "passed": sum(1 for x in ex if x.get("passed")), "n": len(ex),
                     "fails": [f"{x['text'][:110]} -- {str(x.get('evidence'))[:160]}" for x in ex if not x.get("passed")],
                     "dir": str(g.parent.relative_to(HERE / "results"))})
    if not rows:
        return [{"error": (p.stderr or p.stdout)[-500:]}]
    return rows


def table(rows, modes):
    ids = sorted({(r["id"], r["name"]) for r in rows})
    L = ["| id | scenario | " + " | ".join(modes) + " |", "|---|---|" + "---|" * len(modes)]
    for i, n in ids:
        cells = []
        for m in modes:
            r = next((x for x in rows if x["id"] == i and x["mode"] == m), None)
            cells.append(f"{r['passed']}/{r['n']} ({r['creates']}c)" if r else "-")
        L.append(f"| {i} | {n} | " + " | ".join(cells) + " |")
    return L


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true")
    ap.add_argument("--only", choices=["trigger", "quality", "followups"])
    ap.add_argument("--regrade", action="store_true", help="re-grade saved transcripts in results/raw (no new maps; skips trigger)")
    ap.add_argument("--model", default="sonnet")
    ap.add_argument("--max-creates", type=int, default=45)
    a = ap.parse_args()
    RAW.mkdir(parents=True, exist_ok=True)
    want = lambda s: a.only in (None, s)
    L = [f"# Eval results ({datetime.date.today()}, model {a.model}{', quick' if a.quick else ''})", ""]
    creates = 0
    if want("trigger") and (not a.regrade or (RAW / "trigger.json").exists()):
        t = trig_summary(json.loads((RAW / "trigger.json").read_text())) if a.regrade else run_trigger(a)
        L += ["## Trigger", ""]
        if "error" in t:
            L += [f"ERROR: {t['error']}"]
        else:
            L += [f"{t['passed']}/{t['total']} queries; recall {t['recall']:.0%}, precision {t['precision']:.0%}"] + [f"- {f}" for f in t["fails"]]
        L.append("")
    allrows = []
    if want("quality"):
        r = run_q(a, "quality.json", "skill", QUICK_QUALITY if a.quick else "", "quality")
        allrows += r
        L += ["## Quality (skill mode)", ""]
        if "error" in r[0]:
            L += [f"ERROR: {r[0]['error']}"]
        else:
            L += table(r, ["skill"]); creates += sum(x["creates"] for x in r)
        L.append("")
    if want("followups"):
        r = run_q(a, "followups.json", "both", QUICK_FOLLOWUPS if a.quick else "", "followups")
        allrows += r
        L += ["## Followups", ""]
        if "error" in r[0]:
            L += [f"ERROR: {r[0]['error']}"]
        else:
            L += table(r, ["skill", "docs-only"]); creates += sum(x["creates"] for x in r)
        L.append("")
    fails = [x for x in allrows if x.get("fails")]
    if fails:
        L += ["## Failed assertions", ""]
        for x in fails:
            L.append(f"- {x['id']} {x['name']} [{x['mode']}] (transcript: results/{x['dir']})")
            L += [f"  - {f}" for f in x["fails"]]
        L.append("")
    L.append(f"Map creates (incl. setup): {creates}; png calls: {sum(x.get('pngs', 0) for x in allrows)}")
    txt = "\n".join(L) + "\n"
    (HERE / "results" / "latest.md").write_text(txt)
    print(txt)


if __name__ == "__main__":
    main()
