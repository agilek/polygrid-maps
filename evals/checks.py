"""Deterministic checks against the real API state (GET /v1/maps/{id}), used by run_quality.py
next to the LLM grader. A scenario lists them as `"checks": [{"name": "same_share_url"}, ...]`.
`info` comes from run_quality.summarize(): finals (answer per turn), created_ids / create_calls
(maps the agent created), snapshots (API state after setup and after each turn)."""
import json, re, urllib.request

BASE = "https://maps.polygrid.dev"
SHARE_RE = re.compile(r"maps\.polygrid\.dev/m/([A-Za-z0-9]+)(?![A-Za-z0-9]|/edit)")
URL_RE = re.compile(r"https?://\S+")
TOKEN_RE = re.compile(r"(?<![A-Za-z0-9_-])[A-Za-z0-9_-]{22}(?![A-Za-z0-9_-])")
NARRATION_RE = re.compile(r"\b(api|apis|token|tokens|proxy|plugin|endpoint|curl|json|geojson api|edit_token|bearer)\b", re.I)


def share_ids(text):
    out = []
    for m in SHARE_RE.finditer(text or ""):
        if m.group(1) not in out:
            out.append(m.group(1))
    return out


def get_map(map_id):
    try:
        with urllib.request.urlopen(urllib.request.Request(f"{BASE}/v1/maps/{map_id}", headers={"User-Agent": "polygrid-evals"}), timeout=30) as r:
            return json.loads(r.read())
    except Exception as e:
        return {"_error": str(e)}


def count_lines(body):
    """Routed/connected lines in a map body: LineString members of data, or entries of a `routes` field."""
    n = 0
    data = body.get("data") or {}
    feats = data.get("features", []) if data.get("type") == "FeatureCollection" else [data] if data else []
    for f in feats:
        g = f.get("geometry", f) or {}
        if g.get("type") == "LineString":
            n += 1
        elif g.get("type") == "MultiLineString":
            n += len(g.get("coordinates", []))
    return max(n, len(body.get("routes") or []))


def _strip_urls(t):
    return URL_RE.sub(" ", t or "")


def _res(text, ok, ev):
    return {"text": "[api] " + text, "passed": bool(ok), "evidence": ev}


def run_checks(specs, info, subs):
    finals = info.get("finals", [])
    snaps = info.get("snapshots", [])
    created = [i for i in info.get("created_ids", []) if i != "k3f9q2xa7b"]  # k3f9q2xa7b = example id in llms.txt, leaked from WebFetch results in older transcripts
    n_created = max(len(created), info.get("create_calls", 0))
    first_ids = share_ids(finals[0]) if finals else []
    last_ids = share_ids(finals[-1]) if finals else []
    setup_id = subs.get("{{MAP_ID}}")
    # map the follow-up is about: the first share link (or the pasted one)
    target = setup_id or (first_ids[0] if first_ids else None)
    final_id = last_ids[0] if last_ids else None
    live = get_map(final_id) if final_id else {}
    out = []
    for sp in specs:
        n = sp["name"]
        if n == "same_share_url":
            ok = bool(target) and last_ids == [target] if setup_id else (len(first_ids) == 1 and last_ids == first_ids)
            out.append(_res("follow-up answer shows the same share URL as the first answer", ok, f"first={first_ids} last={last_ids} setup={setup_id}"))
        elif n == "created_count":
            out.append(_res(f"agent created exactly {sp['n']} map(s)", n_created == sp["n"], f"created ids={created} create calls={info.get('create_calls')}"))
        elif n == "lines_min":
            k = count_lines(live) if final_id else 0
            out.append(_res(f"final map has >= {sp['n']} routed lines", k >= sp["n"], f"id={final_id} lines={k} routes_field={bool(live.get('routes'))} err={live.get('_error')}"))
        elif n == "lines_increased":
            before = count_lines(snaps[0].get(setup_id, {})) if snaps and setup_id else 0
            k = count_lines(live) if final_id else 0
            out.append(_res("final map has more lines than before the request", k > before, f"before={before} after={k}"))
        elif n == "no_raw_token":
            bad = []
            for i, t in enumerate(finals, 1):
                clean = _strip_urls(t)  # edit URLs (private edit link) are allowed
                for tok in info.get("created_tokens", []):
                    if tok in clean:
                        bad.append((i, tok[:4] + "..."))
                for m in TOKEN_RE.findall(clean):
                    if re.search(r"\d", m) and re.search(r"[A-Za-z]", m):
                        bad.append((i, m[:4] + "..."))
            out.append(_res("no raw edit token outside an edit link in any answer", not bad, f"found={bad}"))
        elif n == "no_narration":
            bad = [(i, m.group(0)) for i, t in enumerate(finals, 1) for m in NARRATION_RE.finditer(_strip_urls(t))]
            out.append(_res("no technical narration (API, token, proxy, plugin, JSON...) in answers", not bad, f"found={bad[:5]}"))
        elif n == "basemap_dark":
            b = live.get("basemap")
            out.append(_res("final map basemap is dark", b in ("dark", "blank-dark"), f"id={final_id} basemap={b}"))
        elif n == "in_place_setup":
            ok = final_id == setup_id and n_created == 0
            out.append(_res("pasted-link map updated in place, no new map", ok, f"final={final_id} setup={setup_id} agent creates={n_created}"))
        elif n == "new_url_for_followup":
            first = first_ids[0] if first_ids else None
            ok = bool(final_id) and final_id != first and n_created == 2
            out.append(_res("separate-map request got a NEW url (2 creates total)", ok, f"first={first} final={final_id} creates={n_created}"))
        elif n == "original_unchanged":
            first = first_ids[0] if first_ids else None
            idx = 1 if info.get("has_setup") else 0  # snapshot right after the first agent turn
            before = (snaps[idx] if len(snaps) > idx else {}).get(first, {}) if first else {}
            now = get_map(first) if first else {}
            sig = lambda b: json.dumps([b.get("title"), b.get("basemap"), b.get("data")], sort_keys=True)
            out.append(_res("original map unchanged after the follow-up", bool(before) and "_error" not in before and sig(before) == sig(now), f"id={first} err={now.get('_error')}"))
        else:
            out.append(_res(f"unknown check {n}", False, "not implemented"))
    return out
