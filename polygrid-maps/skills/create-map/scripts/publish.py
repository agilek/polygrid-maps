#!/usr/bin/env python3
"""Publish a map to maps.polygrid.dev. Stdlib only.

  publish.py body.json                        create (POST)
  publish.py body.json --id ID --token TOKEN  update (PUT)
  publish.py --get ID                         fetch editable body
  publish.py --selftest

Network/proxy failure -> prints {"fallback_url": ...} and exits 0.
API 4xx/5xx JSON error -> prints it and exits 1.
"""
import argparse, base64, json, sys, urllib.error, urllib.request

BASE = "https://maps.polygrid.dev"
UA = "create-map-skill/1.0 (+https://maps.polygrid.dev)"


def fallback_url(body):
    raw = json.dumps(body, separators=(",", ":"), ensure_ascii=False).encode()
    return BASE + "/new#c=" + base64.urlsafe_b64encode(raw).decode().rstrip("=")


def decode_fragment(b64):
    return json.loads(base64.urlsafe_b64decode(b64 + "=" * (-len(b64) % 4)))


def call(method, path, body=None, token=None):
    data = json.dumps(body).encode() if body is not None else None
    h = {"User-Agent": UA, "Accept": "application/json"}
    if data:
        h["Content-Type"] = "application/json"
    if token:
        h["Authorization"] = "Bearer " + token
    req = urllib.request.Request(BASE + path, data=data, headers=h, method=method)
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return r.status, json.load(r)
    except urllib.error.HTTPError as e:
        raw = e.read().decode(errors="replace")
        try:
            return e.code, json.loads(raw)
        except ValueError:
            return e.code, None  # not API JSON: proxy/WAF page


def selftest():
    body = {"title": "Tést ☕", "places": ["Prague", "Brno?x=1&y=2"], "data": {"a": ">>>???"}}
    u = fallback_url(body)
    frag = u.split("#c=", 1)[1]
    assert u.startswith(BASE + "/new#c=") and not set(frag) & set("+/="), u
    assert decode_fragment(frag) == body
    print("selftest ok")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("body", nargs="?")
    ap.add_argument("--id")
    ap.add_argument("--token")
    ap.add_argument("--get")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    if a.get:
        status, out = call("GET", "/v1/maps/" + a.get)
        print(json.dumps(out, indent=2, ensure_ascii=False) if out else f"HTTP {status}")
        sys.exit(0 if status == 200 else 1)
    if not a.body:
        ap.error("body.json required")
    if bool(a.id) != bool(a.token):
        ap.error("--id and --token go together")
    body = json.load(open(a.body))
    method, path = ("PUT", "/v1/maps/" + a.id) if a.id else ("POST", "/v1/maps")
    try:
        status, out = call(method, path, body, a.token)
    except (urllib.error.URLError, OSError) as e:  # DNS, proxy, timeout
        status, out = None, None
        why = str(e)
    else:
        why = f"HTTP {status} from a non-API source (proxy/firewall)"
    if out is None:  # network failure or non-JSON (proxy 403 page)
        print(json.dumps({"fallback_url": fallback_url(body), "note":
              f"Could not reach the maps API ({why}). Give the user this link: opening it shows the map ready to publish with one click. Updates via PUT are not possible this way."}, ensure_ascii=False))
        return
    print(json.dumps(out, indent=2, ensure_ascii=False))
    sys.exit(0 if status < 400 else 1)


if __name__ == "__main__":
    main()
