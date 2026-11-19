#!/usr/bin/env python3
"""Output-quality evals for the create-map skill (quality.json).

For each scenario: make an isolated scratch project with the skill copied into
.claude/skills/, optionally run a setup step (creates one real map on
maps.polygrid.dev so pasted-link scenarios have something to point at), run
`claude -p` (plus follow-up turns via --resume), save the stream-json
transcript, then grade every assertion with an LLM grader (claude -p) and write
grading.json in the skill-creator schema (text / passed / evidence).

REAL MAPS ARE PUBLISHED to production. Create count is reported and capped.

  python3 run_quality.py --out DIR [--file quality.json|followups.json] [--mode skill|docs-only|both]
                         [--only 1,4] [--model sonnet] [--grader-model sonnet]
                         [--max-creates 40] [--jobs 4] [--regrade]

Modes: `skill` (default) copies the create-map skill into the scratch project.
`docs-only` installs nothing: the agent only gets a hint that the service is
https://maps.polygrid.dev and must learn the API from /llms.txt or
/docs/agents with WebFetch (tools: Bash + WebFetch), like agents without the plugin.
Scenarios may carry `checks` (see checks.py) that read the API state directly.
"""
import argparse, json, os, re, shutil, subprocess, sys, tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import checks  # API-state checks (GET /v1/maps/{id}), see checks.py

DOCS_HINT = ("The user makes shareable web maps with the service at https://maps.polygrid.dev. "
             "If you need to know how to use it, read https://maps.polygrid.dev/llms.txt or https://maps.polygrid.dev/docs/agents.")
SKILL = HERE.parent / "skills" / "create-map"
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


def claude_turn(prompt, cwd, model, session=None, timeout=600, mode="skill"):
    cmd = ["claude", "-p", prompt, "--output-format", "stream-json", "--verbose",
           "--model", model, "--setting-sources", "project", "--strict-mcp-config",
           "--permission-mode", "bypassPermissions"]
    if mode == "docs-only":
        # no skill: only Bash (curl) and WebFetch, plus the one-line hint about the service
        cmd += ["--tools", "Bash,WebFetch", "--allowedTools", "Bash,WebFetch", "--append-system-prompt", DOCS_HINT]
    else:
        cmd += ["--allowedTools", "WebSearch,WebFetch"]  # real users have web access; the rich-details scenarios need it
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


def summarize(turns):  # -> text, creates, pngs, info
    """Readable transcript: user prompt, tool calls (Bash commands, searches), assistant text."""
    lines, creates, pngs = [], 0, 0
    info = {"finals": [], "results": []}  # results: (turn, full tool_result text)
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
                        if re.search(r"publish\.py\s+(create\b|[^\s-]+\.json)", cmd) or \
                                re.search(r"curl[^|;]*-X\s*POST[^|;]*/v1/maps(?![/\w])", cmd) or \
                                re.search(r"curl[^|;]*/v1/maps(?![/\w])[^|;]*(-d|--data)", cmd) and not re.search(r"-X\s*(PUT|PATCH)", cmd):
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
                            info["results"].append([i, t])
                            lines.append(f"[tool result] {t[:1200]}")
        final = next((e.get("result") for e in reversed(events) if e.get("type") == "result"), "")
        info["finals"].append(final)
        lines.append(f"=== TURN {i} FINAL ANSWER ===\n{final}\n")
    # created maps = distinct ids in tool results that carry an edit token/url (only create responses do)
    created = []
    for _, t in info["results"]:
        if "edit_url" in t or "edit_token" in t:
            for m in re.finditer(r"/m/([A-Za-z0-9]{6,})", t):
                if m.group(1) not in created:
                    created.append(m.group(1))
    info["created_ids"] = created
    info["created_tokens"] = sorted({m for _, t in info["results"] for m in re.findall(r'"edit_token"\s*:\s*"([^"]+)"', t)})
    info["create_calls"] = creates
    creates = max(creates, len(created))
    return "\n".join(lines), creates, pngs, info


def grade(transcript, assertions, model, subs):
    items = "\n".join(f"{i+1}. {a}" for i, a in enumerate(assertions))
    prompt = f"""You are grading a transcript of an AI assistant that makes shareable maps with the Polygrid Maps service (via a skill or from its docs). For each assertion decide pass/fail from the transcript only (tool calls are listed, the user-visible answer is the FINAL ANSWER sections). Be strict: if the evidence is absent, fail. The user is non-technical, so JSON/curl/tokens in the final answer are failures except where an assertion says otherwise (the private edit URL itself is allowed).
Substitutions used in the scenario: {json.dumps(subs)}

ASSERTIONS
{items}

TRANSCRIPT
{transcript[:60000]}

Reply with ONLY a JSON array, one object per assertion in order: {{"text": "<assertion>", "passed": true|false, "evidence": "<short quote or reason>"}}"""
    p = subprocess.run(["claude", "-p", "--model", model, "--setting-sources", "project", "--output-format", "text"],
                       input=prompt, env=clean_env(), capture_output=True, text=True, timeout=300)
    try:
        dec, out = json.JSONDecoder(), p.stdout
        for m in re.finditer(r"\[\s*\{", out):
            try:
                return dec.raw_decode(out[m.start():])[0]
            except ValueError:
                continue
        raise ValueError("no json")
    except Exception:
        return [{"text": a, "passed": False, "evidence": "grader output unparseable: " + p.stdout[:200]} for a in assertions]


def run_one(ev, common, out, model, gmodel, regrade, mode="skill"):
    d = out / f"eval-{ev['id']:02d}-{ev['name']}.{mode}"
    d.mkdir(parents=True, exist_ok=True)
    subs, info = {}, {}
    tpath = d / "transcript.json"
    if regrade and tpath.exists():
        saved = json.loads(tpath.read_text())
        text, subs, creates, pngs, info = saved["text"], saved["subs"], saved["creates"], saved["pngs"], saved.get("info", {})
    else:
        work = Path(tempfile.mkdtemp(prefix=f"q{ev['id']}-", dir=out))
        if mode == "skill":
            sk = work / ".claude" / "skills"
            sk.mkdir(parents=True)
            shutil.copytree(SKILL, sk / "create-map", ignore=shutil.ignore_patterns("__pycache__"))
        else:
            (work / ".claude").mkdir()
        n_setup = 0
        snaps = []  # API snapshots (GET /v1/maps/{id}) after setup and after each turn
        if ev.get("setup"):
            subs = run_setup(work)  # always uses the repo's publish.py: harness plumbing, not the agent
            n_setup = 1
            snaps.append({subs["{{MAP_ID}}"]: checks.get_map(subs["{{MAP_ID}}"])})
        def sub(s):
            for k, v in subs.items():
                s = s.replace(k, v)
            return s
        turns, sid = [], None
        for prompt in [ev["prompt"]] + ev.get("followups", []):
            prompt = sub(prompt)
            events, sid = claude_turn(prompt, work, model, sid, mode=mode)
            turns.append((prompt, events))
            final = next((e.get("result") for e in reversed(events) if e.get("type") == "result"), "") or ""
            ids = set(checks.share_ids(final)) | set(k for sn in snaps for k in sn)
            snaps.append({i: checks.get_map(i) for i in ids})
        text, creates, pngs, info = summarize(turns)
        info["snapshots"] = snaps
        info["has_setup"] = bool(n_setup)
        creates += n_setup
        tpath.write_text(json.dumps({"text": text, "subs": subs, "creates": creates, "pngs": pngs, "info": info}, ensure_ascii=False, indent=1))
        (d / "transcript.txt").write_text(text)
        shutil.rmtree(work, ignore_errors=True)
    asserts = [a.replace("{{SHARE_URL}}", subs.get("{{SHARE_URL}}", "{{SHARE_URL}}")).replace("{{EDIT_URL}}", subs.get("{{EDIT_URL}}", "{{EDIT_URL}}")) for a in ev["assertions"] + common]
    res = []
    if ev.get("checks"):  # deterministic API-state checks first
        res += checks.run_checks(ev["checks"], info, subs)
    res += grade(text, asserts, gmodel, {k: v for k, v in subs.items()})
    passed = sum(1 for r in res if r.get("passed"))
    g = {"eval_id": ev["id"], "name": ev["name"], "mode": mode, "creates": creates, "png_calls": pngs,
         "expectations": res, "pass_rate": passed / max(1, len(res))}
    (d / "grading.json").write_text(json.dumps(g, ensure_ascii=False, indent=1))
    return g


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--file", default="quality.json", help="scenario file in plugins/evals (quality.json or followups.json)")
    ap.add_argument("--mode", default="skill", choices=["skill", "docs-only", "both"])
    ap.add_argument("--only", default="")
    ap.add_argument("--model", default="sonnet")
    ap.add_argument("--grader-model", default="sonnet")
    ap.add_argument("--max-creates", type=int, default=40)
    ap.add_argument("--jobs", type=int, default=4)
    ap.add_argument("--regrade", action="store_true", help="re-grade saved transcripts, no new maps")
    a = ap.parse_args()
    q = json.loads((HERE / a.file).read_text())
    evs = q["evals"]
    if a.only:
        ids = {int(x) for x in a.only.split(",")}
        evs = [e for e in evs if e["id"] in ids]
    out = Path(a.out).resolve()
    out.mkdir(parents=True, exist_ok=True)
    with ThreadPoolExecutor(a.jobs) as ex:
        modes = ["skill", "docs-only"] if a.mode == "both" else [a.mode]
        jobs = [(e, m) for e in evs for m in modes]
        res = list(ex.map(lambda j: run_one(j[0], q.get("common_assertions", []), out, a.model, a.grader_model, a.regrade, j[1]), jobs))
    total_creates = sum(r["creates"] for r in res)
    tot = sum(len(r["expectations"]) for r in res)
    ok = sum(sum(1 for x in r["expectations"] if x.get("passed")) for r in res)
    print(f"{'id':>3} {'name':36} {'mode':9} pass  creates")
    for r in res:
        n = len(r["expectations"]); p = sum(1 for x in r["expectations"] if x.get("passed"))
        print(f"{r['eval_id']:>3} {r['name']:36} {r['mode']:9} {p}/{n}  {r['creates']}")
        for x in r["expectations"]:
            if not x.get("passed"):
                print(f"      FAIL: {x['text'][:110]}\n            {str(x.get('evidence'))[:200]}")
    print(f"TOTAL {ok}/{tot} assertions, map creates (incl. setup): {total_creates}, png calls: {sum(r['png_calls'] for r in res)}")
    if total_creates > a.max_creates:
        print("WARNING: create budget exceeded", file=sys.stderr)


if __name__ == "__main__":
    main()
