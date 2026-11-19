#!/usr/bin/env python3
"""Polygrid Maps helper (maps.polygrid.dev). Stdlib only, Python 3.8+.

  publish.py create body.json                     new map (POST)
  publish.py update ID --token T body.json        replace whole map (PUT)
  publish.py set ID --token T key=value ...       change a few settings (get, merge, put)
  publish.py patch ID --token T changes.json      same, changes from a JSON file
  publish.py get ID                               editable body (no token needed)
  publish.py links ID                             share/embed/download/variant links
  publish.py png ID out.png                       download the preview picture
  publish.py --selftest

ID may be a bare id, a share URL (.../m/ID?basemap=dark) or an edit URL
(.../m/ID/edit#t=TOKEN; the token is picked up from it). The token can also
come from the POLYGRID_TOKEN environment variable.

Legacy forms still work: publish.py body.json [--id ID --token T], publish.py --get ID.
Env POLYGRID_BASE overrides the API origin (e.g. http://localhost:8787).
Network/proxy failure on create -> prints {"fallback_url": ...}, exit 0.
API errors -> prints the JSON error, exit 1.
"""
import argparse, base64, json, os, re, sys, urllib.error, urllib.request

BASE = os.environ.get("POLYGRID_BASE", "https://maps.polygrid.dev").rstrip("/")
UA = "create-map-skill/2.0 (+https://maps.polygrid.dev)"
COMMANDS = {"create", "update", "set", "patch", "get", "links", "png"}
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


def request(method, path, body=None, token=None, raw=False):
    data = json.dumps(body).encode() if body is not None else None
    h = {"User-Agent": UA, "Accept": "*/*" if raw else "application/json"}
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


def call(method, path, body=None, token=None):
    return request(method, path, body, token)


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
    status, blob = request("GET", f"/m/{mid}.png", raw=True)
    if status != 200 or not isinstance(blob, bytes):
        print(json.dumps({"error": f"preview not available (HTTP {status}); try again in a minute"}))
        sys.exit(1)
    open(outfile, "wb").write(blob)
    print(json.dumps({"saved": outfile, "bytes": len(blob)}))


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

    ap = argparse.ArgumentParser(description="Polygrid Maps helper")
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("create"); s.add_argument("body")
    s = sub.add_parser("update"); s.add_argument("ref"); s.add_argument("--token"); s.add_argument("body")
    s = sub.add_parser("set"); s.add_argument("ref"); s.add_argument("--token"); s.add_argument("pairs", nargs="+", metavar="key=value")
    s = sub.add_parser("patch"); s.add_argument("ref"); s.add_argument("--token"); s.add_argument("changes")
    s = sub.add_parser("get"); s.add_argument("ref")
    s = sub.add_parser("links"); s.add_argument("ref")
    s = sub.add_parser("png"); s.add_argument("ref"); s.add_argument("out")
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
    except (urllib.error.URLError, OSError) as e:
        sys.exit(json.dumps({"error": f"cannot reach the maps service: {e}"}))


if __name__ == "__main__":
    main()
