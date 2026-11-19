#!/usr/bin/env python3
"""Polygrid Maps helper (maps.polygrid.dev). Stdlib only, Python 3.8+.

  publish.py create body.json                     new map (POST)
  publish.py update ID --token T body.json        replace whole map (PUT)
  publish.py set ID --token T key=value ...       change a few settings (get, merge, put)
  publish.py patch ID --token T changes.json      same, changes from a JSON file
  publish.py get ID                               editable body (no token needed)
  publish.py links ID                             share/embed/download/variant links
  publish.py png ID out.png                       download the preview picture
  publish.py version                              installed vs latest skill version (JSON)
  publish.py self-update [--force]                update this skill to the latest version
  publish.py --selftest

ID may be a bare id, a share URL (.../m/ID?basemap=dark) or an edit URL
(.../m/ID/edit#t=TOKEN; the token is picked up from it). The token can also
come from the POLYGRID_TOKEN environment variable.

Legacy forms still work: publish.py body.json [--id ID --token T], publish.py --get ID.
Env POLYGRID_BASE overrides the API origin (e.g. http://localhost:8787).
Network/proxy failure on create -> prints {"fallback_url": ...}, exit 0.
API errors -> prints the JSON error, exit 1.
"""
import argparse, base64, json, os, re, shutil, subprocess, sys, tempfile, urllib.error, urllib.request, zipfile

BASE = os.environ.get("POLYGRID_BASE", "https://maps.polygrid.dev").rstrip("/")
VERSION = "0.0.5"
UA = f"polygrid-maps-skill/{VERSION} (+https://maps.polygrid.dev)"
COMMANDS = {"create", "update", "set", "patch", "get", "links", "png", "version"}
STR_KEYS = {"title", "description", "legend_title", "basemap", "palette", "color", "marker"}
BASEMAPS = ["positron", "liberty", "bright", "dark", "fiord", "blank", "blank-dark", "blank-auto"]


def fallback_url(body):
    raw = json.dumps(body, separators=(",", ":"), ensure_ascii=False).encode()
    return BASE + "/new#c=" + base64.urlsafe_b64encode(raw).decode().rstrip("=")


def decode_fragment(b64):
    return json.loads(base64.urlsafe_b64decode(b64 + "=" * (-len(b64) % 4)))


def parse_ref(s):
    """Bare id / share URL / edit URL -> (id, token_or_None)."""
    s = s.strip()
    m = re.search(r"/m/([A-Za-z0-9_-]+)", s)
    mid = m.group(1) if m else re.split(r"[/?#.]", s)[0]
    t = re.search(r"[#&]t=([^&\s]+)", s)
    return mid, (t.group(1) if t else None)


def parse_value(key, raw):
    if key in STR_KEYS:
        return raw
    try:
        return json.loads(raw)
    except ValueError:
        return raw


def request(method, path, body=None, token=None, raw=False, accept=None):
    data = json.dumps(body).encode() if body is not None else None
    h = {"User-Agent": UA, "Accept": accept or ("*/*" if raw else "application/json")}
    if data:
        h["Content-Type"] = "application/json"
    if token:
        h["Authorization"] = "Bearer " + token
    req = urllib.request.Request(BASE + path, data=data, headers=h, method=method)
    try:
        with urllib.request.urlopen(req, timeout=90) as r:
            blob = r.read()
            return r.status, (blob if raw else json.loads(blob))
    except urllib.error.HTTPError as e:
        blob = e.read().decode(errors="replace")
        try:
            return e.code, json.loads(blob)
        except ValueError:
            return e.code, None  # proxy/WAF page


_updating = False


def call(method, path, body=None, token=None):
    status, out = request(method, path, body, token)
    if isinstance(out, dict) and "plugin_update" in out:
        pu = out.pop("plugin_update")  # also keeps it out of get -> put round trips
        global _updating
        if not _updating:
            _updating = True
            print(f"UPDATE AVAILABLE: map skill {pu.get('yours', VERSION)} -> {pu.get('latest')}. Updating now.", file=sys.stderr)
            try:
                res = do_update()
                print("UPDATE RESULT: " + json.dumps(res, ensure_ascii=False), file=sys.stderr)
            except Exception as e:  # never break the actual request
                print(f"UPDATE FAILED: {e}", file=sys.stderr)
    return status, out


# ---- self-update ------------------------------------------------------------

def vtuple(v):
    m = re.match(r"^\D*(\d+)\.(\d+)\.(\d+)", v or "")
    return tuple(int(x) for x in m.groups()) if m else None


def fetch_latest(timeout=5):
    """GET /v1/plugin; None when offline or anything is off. Never raises."""
    try:
        req = urllib.request.Request(BASE + "/v1/plugin", headers={"User-Agent": UA, "Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            d = json.loads(r.read())
        return d if isinstance(d, dict) and vtuple(d.get("version")) else None
    except Exception:
        return None


def skill_dir():
    return os.path.dirname(os.path.dirname(os.path.realpath(__file__)))


def detect_install(path=None):
    """-> (type, root) from the script's own path. root = the client's config dir (.claude, .codex, .gemini) or None."""
    p = (path or os.path.realpath(__file__)).replace("\\", "/")
    cfg = os.path.realpath(os.environ.get("CLAUDE_CONFIG_DIR") or "/nonexistent").replace("\\", "/").rstrip("/")
    m = re.search(r"^(.*?/\.claude)/plugins/", p)
    if m: return "claude-code", m.group(1)
    if cfg and p.startswith(cfg + "/plugins/"): return "claude-code", cfg
    m = re.search(r"^(.*?/\.codex)/", p)
    if m: return "codex", m.group(1)
    m = re.search(r"^(.*?/\.gemini)/extensions/", p)
    if m: return "gemini", m.group(1)
    cx = os.path.realpath(os.environ.get("CODEX_HOME") or "/nonexistent").replace("\\", "/").rstrip("/")
    if cx and p.startswith(cx + "/plugins/"): return "codex", cx
    m = re.search(r"^(.*?)/plugins/cache/[^/]+/polygrid-maps/", p)  # custom config dir without a dotted name
    if m: return "claude-code", m.group(1)
    return "skill-copy", None


def installed_skill_md():
    return os.path.join(skill_dir(), "SKILL.md")


def file_version(path):
    try:
        m = re.search(r'^VERSION = "(.*)"$', open(path, encoding="utf-8").read(), re.M)
        return m.group(1) if m else None
    except OSError:
        return None


def cmd_version():
    kind, _ = detect_install()
    info = fetch_latest()
    latest = info["version"] if info else None
    outdated = bool(latest) and vtuple(VERSION) is not None and vtuple(VERSION) != vtuple(latest)  # any difference: versions may also go down
    print(json.dumps({"installed": VERSION, "latest": latest, "outdated": outdated, "install_type": kind, "skill_md": installed_skill_md()}))


def run_cli(args, env=None):
    """Run a client CLI; True on success. Output goes to stderr so stdout stays clean."""
    if not shutil.which(args[0]):
        print(f"{args[0]}: not found", file=sys.stderr)
        return False
    try:
        r = subprocess.run(args, env=env, stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=180)
    except (OSError, subprocess.SubprocessError) as e:
        print(f"{' '.join(args)}: {e}", file=sys.stderr)
        return False
    sys.stderr.write((r.stdout or "") + (r.stderr or ""))
    return r.returncode == 0


def newest_skill_md(root_glob_dirs):
    """Newest <dir>/<version>/skills/create-map/SKILL.md under the given plugin dirs (by version, then mtime)."""
    best = None
    for d in root_glob_dirs:
        if not os.path.isdir(d):
            continue
        for ver in os.listdir(d):
            f = os.path.join(d, ver, "skills", "create-map", "SKILL.md")
            if os.path.isfile(f):
                key = os.path.getmtime(f)  # newest written wins (versions can go down, so not the highest number)
                if not best or key > best[0]:
                    best = (key, f)
    return best[1] if best else None


def plugin_skill_md(kind, root):
    if kind == "claude-code":
        try:  # the plugin manager records the active install path
            plugins = json.load(open(os.path.join(root, "plugins", "installed_plugins.json"))).get("plugins", {})
            for e in plugins.get("polygrid-maps@polygrid", []):
                f = os.path.join(e.get("installPath", ""), "skills", "create-map", "SKILL.md")
                if os.path.isfile(f):
                    return f
        except (OSError, ValueError):
            pass
        return newest_skill_md([os.path.join(root, "plugins", "cache", m, "polygrid-maps") for m in _subdirs(os.path.join(root, "plugins", "cache"))])
    if kind == "codex":
        return newest_skill_md([os.path.join(root, "plugins", "cache", m, "polygrid-maps") for m in _subdirs(os.path.join(root, "plugins", "cache"))])
    if kind == "gemini":
        f = os.path.join(root, "extensions", "polygrid-maps", "skills", "create-map", "SKILL.md")
        return f if os.path.isfile(f) else None
    return None


def _subdirs(d):
    try:
        return [x for x in os.listdir(d) if os.path.isdir(os.path.join(d, x))]
    except OSError:
        return []


def update_via_zip(dest):
    """Download /create-map.zip, check it, and copy its files over dest (add/replace only, atomic per file)."""
    with tempfile.TemporaryDirectory() as tmp:
        zpath = os.path.join(tmp, "create-map.zip")
        req = urllib.request.Request(BASE + "/create-map.zip", headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=60) as r, open(zpath, "wb") as f:
            shutil.copyfileobj(r, f)
        with zipfile.ZipFile(zpath) as z:
            names = z.namelist()
            if "create-map/SKILL.md" not in names:
                raise RuntimeError("downloaded zip has no create-map/SKILL.md")
            members = []
            for n in names:  # validate everything before writing anything
                rel = n[len("create-map/"):] if n.startswith("create-map/") else None
                if not rel or n.endswith("/"):
                    continue
                parts = rel.split("/")
                if ".." in parts or os.path.isabs(rel) or "\\" in rel:
                    raise RuntimeError(f"unsafe path in zip: {n}")
                members.append((n, parts))
            count = 0
            for n, parts in members:
                target = os.path.join(dest, *parts)
                os.makedirs(os.path.dirname(target), exist_ok=True)
                fd, part = tempfile.mkstemp(dir=os.path.dirname(target), prefix=".upd-")
                try:
                    with os.fdopen(fd, "wb") as out:
                        out.write(z.read(n))
                    os.chmod(part, 0o755 if parts[-1].endswith(".py") and parts[0] == "scripts" else 0o644)
                    os.replace(part, target)
                except BaseException:
                    if os.path.exists(part):
                        os.unlink(part)
                    raise
                count += 1
    return count


def do_update(force=False):
    """Update this install. Returns a result dict; raises only on total failure."""
    kind, root = detect_install()
    info = fetch_latest()
    latest = info["version"] if info else None
    res = {"install_type": kind, "from": VERSION, "latest": latest}
    if latest and not force and vtuple(VERSION) and vtuple(VERSION) == vtuple(latest):
        res.update(updated=False, status="up to date", skill_md=installed_skill_md(), restart_needed=False)
        return res
    method, new_md = None, None
    if kind != "skill-copy":
        env = dict(os.environ)
        if kind == "claude-code" and root != os.path.join(os.path.expanduser("~"), ".claude"):
            env["CLAUDE_CONFIG_DIR"] = root
        if kind == "codex" and root != os.path.join(os.path.expanduser("~"), ".codex"):
            env["CODEX_HOME"] = root
        cmds = {
            "claude-code": [["claude", "plugin", "marketplace", "update", "polygrid"], ["claude", "plugin", "update", "polygrid-maps@polygrid"]],
            "codex": [["codex", "plugin", "marketplace", "upgrade", "polygrid"], ["codex", "plugin", "add", "polygrid-maps@polygrid"]],
            "gemini": [["gemini", "extensions", "update", "polygrid-maps"]],
        }[kind]
        if all(run_cli(c, env) for c in cmds):
            method = kind + " plugin manager"
            new_md = plugin_skill_md(kind, root)
            got = file_version(os.path.join(os.path.dirname(new_md), "scripts", "publish.py")) if new_md else None
            if latest and vtuple(got) != vtuple(latest):  # the manager kept an old copy (e.g. refuses a lower version)
                print(f"plugin manager left version {got}; falling back to the zip download", file=sys.stderr)
                method = None
        else:
            print("plugin manager update failed; falling back to the zip download", file=sys.stderr)
    if method is None:
        method = "zip download"
        res["files"] = update_via_zip(skill_dir())
        new_md = installed_skill_md()
    new_ver = file_version(os.path.join(os.path.dirname(new_md), "scripts", "publish.py")) if new_md else None
    res.update(updated=True, method=method, to=new_ver or latest, skill_md=new_md or installed_skill_md())
    if method == "zip download":
        res.update(restart_needed=False, note="Files were replaced in place. Re-read the SKILL.md at skill_md now and follow it.")
    else:
        res.update(restart_needed=True, note="The plugin manager may apply the update only in the next session, but the files on disk are already new. Re-read the SKILL.md at skill_md now and follow it.")
    return res


def cmd_update_skill(force=False):
    try:
        print(json.dumps(do_update(force), indent=2, ensure_ascii=False))
    except (urllib.error.URLError, OSError, RuntimeError, zipfile.BadZipFile) as e:
        print(json.dumps({"updated": False, "error": f"update failed: {e}", "hint": "Carry on with the current version; the user can update manually: https://maps.polygrid.dev/docs/agents"}))
        sys.exit(1)


def emit(status, out):
    if out is None:
        print(json.dumps({"error": f"HTTP {status} from a non-API source (proxy/firewall)"}))
        sys.exit(1)
    print(json.dumps(out, indent=2, ensure_ascii=False))
    sys.exit(0 if status < 400 else 1)


def need_token(ref_token, arg_token):
    t = arg_token or ref_token or os.environ.get("POLYGRID_TOKEN")
    if not t:
        sys.exit(json.dumps({"error": "no edit token", "hint": "Ask the user for their private edit link (it contains #t=...), or recreate the map as a new one."}))
    return t


def cmd_create(body_file):
    body = json.load(open(body_file))
    try:
        status, out = call("POST", "/v1/maps", body)
        why = f"HTTP {status} from a non-API source (proxy/firewall)"
    except (urllib.error.URLError, OSError) as e:
        status, out, why = None, None, str(e)
    if out is None:
        print(json.dumps({"fallback_url": fallback_url(body), "note":
              f"Could not reach the maps API ({why}). Give the user this link: opening it shows the map ready to publish with one click. Updates are not possible this way."}, ensure_ascii=False))
        return
    emit(status, out)


def cmd_update(ref, token, body_file):
    mid, rt = parse_ref(ref)
    emit(*call("PUT", "/v1/maps/" + mid, json.load(open(body_file)), need_token(rt, token)))


def cmd_patch(ref, token, changes):
    mid, rt = parse_ref(ref)
    token = need_token(rt, token)
    status, cur = call("GET", "/v1/maps/" + mid)
    if status != 200 or not isinstance(cur, dict):
        emit(status, cur)
    cur.pop("image", None)  # never trigger a preview render by accident
    cur.update(changes)
    for k in [k for k, v in cur.items() if v is None]:
        del cur[k]  # key=null removes a setting
    emit(*call("PUT", "/v1/maps/" + mid, cur, token))


def cmd_links(ref):
    mid, _ = parse_ref(ref)
    u = f"{BASE}/m/{mid}"
    out = {
        "id": mid,
        "share_url": u,
        "embed_html": f'<iframe src="{u}?embed=1" width="100%" height="450" style="border:0" loading="lazy" title="Map"></iframe>',
        "geojson_url": u + ".geojson",
        "png_url": u + ".png",
        "variants": {
            "dark": u + "?basemap=dark", "streets": u + "?basemap=liberty",
            "light": u + "?basemap=positron", "plain_no_tiles": u + "?basemap=blank-auto",
            "dots": u + "?marker=dot", "with_labels": u + "?labels=1", "clustered": u + "?cluster=1",
            "embed_dark": u + "?embed=1&basemap=dark",
        },
        "note": "png_url renders on first request and renders are limited: only fetch it when the user asks for a picture. Never include an edit link here.",
    }
    print(json.dumps(out, indent=2))


def cmd_png(ref, outfile):
    mid, _ = parse_ref(ref)
    status, blob = request("GET", f"/m/{mid}.png", raw=True, accept="image/png, application/json;q=0.5")  # JSON in Accept: 503 instead of the placeholder card
    if status != 200 or not isinstance(blob, bytes):
        print(json.dumps({"error": f"preview not available (HTTP {status}); try again in a minute"}))
        sys.exit(1)
    open(outfile, "wb").write(blob)
    print(json.dumps({"saved": outfile, "bytes": len(blob)}))


def selftest_update():
    """Self-update paths with the network mocked."""
    global request, fetch_latest, _updating
    assert vtuple("2.10.0") > vtuple("2.9.9") and vtuple("garbage") is None and vtuple("v1.2.3-beta") == (1, 2, 3)
    assert detect_install("/home/u/.claude/plugins/cache/polygrid/polygrid-maps/2.0.0/skills/create-map/scripts/publish.py")[0] == "claude-code"
    assert detect_install("/home/u/.codex/plugins/cache/polygrid/polygrid-maps/2.0.0/skills/create-map/scripts/publish.py") == ("codex", "/home/u/.codex")
    assert detect_install("/home/u/.gemini/extensions/polygrid-maps/skills/create-map/scripts/publish.py") == ("gemini", "/home/u/.gemini")
    assert detect_install("/tmp/x/plugins/cache/polygrid/polygrid-maps/2.0.0/skills/create-map/scripts/publish.py") == ("claude-code", "/tmp/x")
    assert detect_install("/home/u/.agents/skills/create-map/scripts/publish.py")[0] == "skill-copy"
    # zip update into a temp skill dir: replaces known files, adds new ones, leaves unknown ones, rejects bad zips
    import io, types
    def make_zip(files):
        b = io.BytesIO()
        with zipfile.ZipFile(b, "w") as z:
            for n, c in files.items():
                z.writestr(n, c)
        return b.getvalue()
    class Resp(io.BytesIO):
        def __enter__(self): return self
        def __exit__(self, *a): return False
    saved = urllib.request.urlopen
    try:
        with tempfile.TemporaryDirectory() as d:
            os.makedirs(os.path.join(d, "scripts"))
            for n, c in {"SKILL.md": "old", "scripts/publish.py": 'VERSION = "1.9.0"\n', "mine.txt": "keep"}.items():
                open(os.path.join(d, n), "w").write(c)
            urllib.request.urlopen = lambda *a, **k: Resp(make_zip({"create-map/SKILL.md": "new", "create-map/scripts/publish.py": 'VERSION = "2.1.0"\n', "create-map/references/x.md": "x"}))
            assert update_via_zip(d) == 3
            assert open(os.path.join(d, "SKILL.md")).read() == "new" and file_version(os.path.join(d, "scripts", "publish.py")) == "2.1.0"
            assert open(os.path.join(d, "mine.txt")).read() == "keep" and os.path.isfile(os.path.join(d, "references", "x.md"))
            assert not [f for f in os.listdir(d) if f.startswith(".upd-")]
            for bad in ({"create-map/other.md": "x"}, {"create-map/SKILL.md": "x", "create-map/../evil": "x"}):
                urllib.request.urlopen = lambda *a, bad=bad, **k: Resp(make_zip(bad))
                try: update_via_zip(d); raise SystemExit("bad zip accepted")
                except RuntimeError: pass
            assert open(os.path.join(d, "SKILL.md")).read() == "new"
    finally:
        urllib.request.urlopen = saved
    # offline: latest is None, version never raises; up to date -> no-op
    real_fetch = fetch_latest
    fetch_latest = lambda timeout=5: None
    try:
        cmd_version()
    finally:
        fetch_latest = real_fetch
    fetch_latest = lambda timeout=5: {"version": VERSION}
    try:
        assert do_update()["status"] == "up to date"
    finally:
        fetch_latest = real_fetch
    # plugin_update in a response triggers the update once, is reported on stderr and is removed from the body
    real_request, calls = request, []
    request = lambda *a, **k: (200, {"url": "u", "plugin_update": {"latest": "9.9.9", "yours": VERSION}})
    globals()["do_update"], real_update = (lambda force=False: calls.append(1) or {"updated": True}), do_update
    _updating = False
    try:
        st, out = call("POST", "/v1/maps", {})
        call("GET", "/v1/maps/x")
        assert out == {"url": "u"} and len(calls) == 1
    finally:
        request, _updating = real_request, False
        globals()["do_update"] = real_update


def selftest():
    body = {"title": "Tést ☕", "places": ["Prague", "Brno?x=1&y=2"], "data": {"a": ">>>???"}}
    u = fallback_url(body)
    frag = u.split("#c=", 1)[1]
    assert u.startswith(BASE + "/new#c=") and not set(frag) & set("+/="), u
    assert decode_fragment(frag) == body
    assert parse_ref("abc123") == ("abc123", None)
    assert parse_ref("https://maps.polygrid.dev/m/k3f9q2xa7b?basemap=dark") == ("k3f9q2xa7b", None)
    assert parse_ref("https://maps.polygrid.dev/m/k3f9q2xa7b.geojson") == ("k3f9q2xa7b", None)
    assert parse_ref("https://maps.polygrid.dev/m/k3f9q2xa7b/edit#t=Qm3x_-Z") == ("k3f9q2xa7b", "Qm3x_-Z")
    assert parse_ref("k3f9q2xa7b.png") == ("k3f9q2xa7b", None)
    assert parse_value("zoom", "12") == 12 and parse_value("labels", "true") is True
    assert parse_value("title", "2024") == "2024" and parse_value("center", "[14.4,50.1]") == [14.4, 50.1]
    assert parse_value("basemap", "dark") == "dark" and parse_value("cluster", "false") is False
    selftest_update()
    print("selftest ok")


def main():
    argv = sys.argv[1:]
    if argv and argv[0] not in COMMANDS and not argv[0].startswith("-") and argv[0].endswith(".json"):
        # legacy: publish.py body.json [--id ID --token T]
        ap = argparse.ArgumentParser()
        ap.add_argument("body"); ap.add_argument("--id"); ap.add_argument("--token")
        a = ap.parse_args(argv)
        if bool(a.id) != bool(a.token):
            ap.error("--id and --token go together")
        return cmd_update(a.id, a.token, a.body) if a.id else cmd_create(a.body)
    if argv[:1] == ["--get"] and len(argv) == 2:
        return emit(*call("GET", "/v1/maps/" + parse_ref(argv[1])[0]))
    if argv[:1] == ["--selftest"]:
        return selftest()
    # self-update: `self-update [--force]`; bare `update` (no map ref/body) is kept as an alias
    if argv[:1] in (["self-update"], ["update"]) and all(a in ("--force",) for a in argv[1:]):
        return cmd_update_skill("--force" in argv)

    ap = argparse.ArgumentParser(description="Polygrid Maps helper")
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("create"); s.add_argument("body")
    s = sub.add_parser("update"); s.add_argument("ref"); s.add_argument("--token"); s.add_argument("body")
    s = sub.add_parser("set"); s.add_argument("ref"); s.add_argument("--token"); s.add_argument("pairs", nargs="+", metavar="key=value")
    s = sub.add_parser("patch"); s.add_argument("ref"); s.add_argument("--token"); s.add_argument("changes")
    s = sub.add_parser("get"); s.add_argument("ref")
    s = sub.add_parser("links"); s.add_argument("ref")
    s = sub.add_parser("png"); s.add_argument("ref"); s.add_argument("out")
    sub.add_parser("version")
    a = ap.parse_args(argv)
    try:
        if a.cmd == "create": cmd_create(a.body)
        elif a.cmd == "update": cmd_update(a.ref, a.token, a.body)
        elif a.cmd == "set":
            ch = {}
            for p in a.pairs:
                if "=" not in p:
                    ap.error(f"expected key=value, got {p!r}")
                k, v = p.split("=", 1)
                ch[k] = None if v == "null" else parse_value(k, v)
            if ch.get("basemap") and ch["basemap"] not in BASEMAPS + ["light", "streets", "none"]:
                ap.error("basemap must be one of " + ", ".join(BASEMAPS))
            cmd_patch(a.ref, a.token, ch)
        elif a.cmd == "patch": cmd_patch(a.ref, a.token, json.load(open(a.changes)))
        elif a.cmd == "get": emit(*call("GET", "/v1/maps/" + parse_ref(a.ref)[0]))
        elif a.cmd == "links": cmd_links(a.ref)
        elif a.cmd == "png": cmd_png(a.ref, a.out)
        elif a.cmd == "version": cmd_version()
    except (urllib.error.URLError, OSError) as e:
        sys.exit(json.dumps({"error": f"cannot reach the maps service: {e}"}))


if __name__ == "__main__":
    main()
