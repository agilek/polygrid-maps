#!/usr/bin/env python3
"""Output-quality evals for the create-map skill (quality.json).

For each scenario: make an isolated scratch project with the skill copied into
.claude/skills/, optionally run a setup step (creates one real map on
maps.polygrid.dev so pasted-link scenarios have something to point at), run
`claude -p` (plus follow-up turns via --resume), save the stream-json
transcript, then grade every assertion with an LLM grader (claude -p) and write
grading.json in the skill-creator schema (text / passed / evidence).

REAL MAPS ARE PUBLISHED to production. Create count is reported and capped.

  python3 run_quality.py --out DIR [--only 1,4] [--model sonnet] [--grader-model sonnet]
                         [--max-creates 40] [--jobs 4] [--regrade]
"""
import argparse, json, os, re, shutil, subprocess, sys, tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent
SKILL = HERE.parent / "polygrid-maps" / "skills" / "create-map"
SETUP_BODY = {
    "title": "Berlin landmarks",
    "places": [
        {"q": "Brandenburg Gate, Berlin, Germany", "title": "Brandenburg Gate"},
        {"q": "Reichstag building, Berlin, Germany", "title": "Reichstag"},
        {"q": "Checkpoint Charlie, Berlin, Germany", "title": "Checkpoint Charlie"},
    ],
}


def clean_env():
    return {k: v for k, v in os.environ.items() if k != "CLAUDECODE"}


def run_setup(work):
    body = work / "setup-body.json"
    body.write_text(json.dumps(SETUP_BODY))
    out = subprocess.run([sys.executable, str(SKILL / "scripts" / "publish.py"), "create", str(body)],
                         capture_output=True, text=True, timeout=120)
    d = json.loads(out.stdout)
    return {"{{SHARE_URL}}": d["url"], "{{EDIT_URL}}": d["edit_url"], "{{MAP_ID}}": d["id"]}


def claude_turn(prompt, cwd, model, session=None, timeout=600):
    cmd = ["claude", "-p", prompt, "--output-format", "stream-json", "--verbose",
           "--model", model, "--setting-sources", "project", "--strict-mcp-config",
           "--permission-mode", "bypassPermissions"]
    if session:
        cmd += ["--resume", session]
    p = subprocess.run(cmd, cwd=cwd, env=clean_env(), capture_output=True, text=True, timeout=timeout)
    events = []
    for line in p.stdout.splitlines():
        try:
            events.append(json.loads(line))
        except ValueError:
            pass
    sid = next((e.get("session_id") for e in events if e.get("session_id")), None)
    return events, sid


def summarize(turns):
    """Readable transcript: user prompt, tool calls (Bash commands, searches), assistant text."""
    lines, creates, pngs = [], 0, 0
    for i, (prompt, events) in enumerate(turns, 1):
        lines.append(f"=== TURN {i} USER ===\n{prompt}\n")
        for e in events:
            if e.get("type") == "assistant":
                for c in e["message"]["content"]:
                    if c["type"] == "text" and c["text"].strip():
                        lines.append(f"[assistant] {c['text']}")
                    elif c["type"] == "tool_use":
                        inp = c["input"]
                        s = inp.get("command") or inp.get("file_path") or inp.get("query") or inp.get("url") or json.dumps(inp)[:300]
                        if c["name"] == "Write":
                            s += "\n" + str(inp.get("content", ""))[:1500]
                        lines.append(f"[tool {c['name']}] {s}")
                        cmd = inp.get("command", "") or ""
                        if re.search(r"publish\.py\s+(create\b|[^\s-]+\.json)", cmd):
                            creates += 1
                        if re.search(r"publish\.py\s+png", cmd):
                            pngs += 1
            elif e.get("type") == "user":
                content = e["message"]["content"]
                if isinstance(content, list):
                    for c in content:
                        if c.get("type") == "tool_result":
                            t = c.get("content")
                            t = t if isinstance(t, str) else json.dumps(t)
                            lines.append(f"[tool result] {t[:1200]}")
        final = next((e.get("result") for e in reversed(events) if e.get("type") == "result"), "")
        lines.append(f"=== TURN {i} FINAL ANSWER ===\n{final}\n")
    return "\n".join(lines), creates, pngs


def grade(transcript, assertions, model, subs):
    items = "\n".join(f"{i+1}. {a}" for i, a in enumerate(assertions))
    prompt = f"""You are grading a transcript of an AI assistant using a map-making skill. For each assertion decide pass/fail from the transcript only (tool calls are listed, the user-visible answer is the FINAL ANSWER sections). Be strict: if the evidence is absent, fail. The user is non-technical, so JSON/curl/tokens in the final answer are failures except where an assertion says otherwise (the private edit URL itself is allowed).
Substitutions used in the scenario: {json.dumps(subs)}

ASSERTIONS
{items}

TRANSCRIPT
{transcript[:60000]}

Reply with ONLY a JSON array, one object per assertion in order: {{"text": "<assertion>", "passed": true|false, "evidence": "<short quote or reason>"}}"""
    p = subprocess.run(["claude", "-p", "--model", model, "--setting-sources", "project", "--output-format", "text"],
                       input=prompt, env=clean_env(), capture_output=True, text=True, timeout=300)
    m = re.search(r"\[.*\]", p.stdout, re.S)
    try:
        return json.loads(m.group(0))
    except Exception:
        return [{"text": a, "passed": False, "evidence": "grader output unparseable: " + p.stdout[:200]} for a in assertions]


def run_one(ev, common, out, model, gmodel, regrade):
    d = out / f"eval-{ev['id']:02d}-{ev['name']}"
    d.mkdir(parents=True, exist_ok=True)
    subs = {}
    tpath = d / "transcript.json"
    if regrade and tpath.exists():
        saved = json.loads(tpath.read_text())
        text, subs, creates, pngs = saved["text"], saved["subs"], saved["creates"], saved["pngs"]
    else:
        work = Path(tempfile.mkdtemp(prefix=f"q{ev['id']}-", dir=out))
        sk = work / ".claude" / "skills"
        sk.mkdir(parents=True)
        shutil.copytree(SKILL, sk / "create-map", ignore=shutil.ignore_patterns("__pycache__"))
        n_setup = 0
        if ev.get("setup"):
            subs = run_setup(work)
            n_setup = 1
        def sub(s):
            for k, v in subs.items():
                s = s.replace(k, v)
            return s
        turns, sid = [], None
        for prompt in [ev["prompt"]] + ev.get("followups", []):
            prompt = sub(prompt)
            events, sid = claude_turn(prompt, work, model, sid)
            turns.append((prompt, events))
        text, creates, pngs = summarize(turns)
        creates += n_setup
        tpath.write_text(json.dumps({"text": text, "subs": subs, "creates": creates, "pngs": pngs}, ensure_ascii=False, indent=1))
        (d / "transcript.txt").write_text(text)
        shutil.rmtree(work, ignore_errors=True)
    asserts = [a.replace("{{SHARE_URL}}", subs.get("{{SHARE_URL}}", "{{SHARE_URL}}")).replace("{{EDIT_URL}}", subs.get("{{EDIT_URL}}", "{{EDIT_URL}}")) for a in ev["assertions"] + common]
    res = grade(text, asserts, gmodel, {k: v for k, v in subs.items()})
    passed = sum(1 for r in res if r.get("passed"))
    g = {"eval_id": ev["id"], "name": ev["name"], "creates": creates, "png_calls": pngs,
         "expectations": res, "pass_rate": passed / max(1, len(res))}
    (d / "grading.json").write_text(json.dumps(g, ensure_ascii=False, indent=1))
    return g


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--only", default="")
    ap.add_argument("--model", default="sonnet")
    ap.add_argument("--grader-model", default="sonnet")
    ap.add_argument("--max-creates", type=int, default=40)
    ap.add_argument("--jobs", type=int, default=4)
    ap.add_argument("--regrade", action="store_true", help="re-grade saved transcripts, no new maps")
    a = ap.parse_args()
    q = json.loads((HERE / "quality.json").read_text())
    evs = q["evals"]
    if a.only:
        ids = {int(x) for x in a.only.split(",")}
        evs = [e for e in evs if e["id"] in ids]
    out = Path(a.out).resolve()
    out.mkdir(parents=True, exist_ok=True)
    with ThreadPoolExecutor(a.jobs) as ex:
        res = list(ex.map(lambda e: run_one(e, q.get("common_assertions", []), out, a.model, a.grader_model, a.regrade), evs))
    total_creates = sum(r["creates"] for r in res)
    tot = sum(len(r["expectations"]) for r in res)
    ok = sum(sum(1 for x in r["expectations"] if x.get("passed")) for r in res)
    print(f"{'id':>3} {'name':36} pass  creates")
    for r in res:
        n = len(r["expectations"]); p = sum(1 for x in r["expectations"] if x.get("passed"))
        print(f"{r['eval_id']:>3} {r['name']:36} {p}/{n}  {r['creates']}")
        for x in r["expectations"]:
            if not x.get("passed"):
                print(f"      FAIL: {x['text'][:110]}\n            {str(x.get('evidence'))[:200]}")
    print(f"TOTAL {ok}/{tot} assertions, map creates (incl. setup): {total_creates}, png calls: {sum(r['png_calls'] for r in res)}")
    if total_creates > a.max_creates:
        print("WARNING: create budget exceeded", file=sys.stderr)


if __name__ == "__main__":
    main()
