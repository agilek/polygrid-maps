# publish.py and API cheatsheet (for you)

Set `POLYGRID_BASE=http://localhost:8787` to test against `npx wrangler dev`.

```
publish.py create body.json                      -> {id,url,edit_token,edit_url,embed_html,warnings,route,...}
publish.py update ID --token T body.json         full replace, same link
publish.py set ID --token T key=value ...        merge into current body, PUT (key=null deletes a key)
publish.py patch ID --token T changes.json       same, changes from a file
publish.py get ID                                editable body (public)
publish.py links ID                              share_url, embed_html, geojson_url, png_url, variants{}
publish.py png ID out.png                        download preview (limited renders)
publish.py --selftest
legacy: publish.py body.json [--id ID --token T]; publish.py --get ID
```
`ID` = bare id, share URL, or edit URL (token read from `#t=`). Token also from `POLYGRID_TOKEN`. Exit 0 ok, 1 API error. If the API is unreachable `create` prints `fallback_url` (a `/new#c=` publish page); updates are impossible in that case.

## REST (when no Python)
- `POST /v1/maps` body -> create. `PUT /v1/maps/{id}` with `Authorization: Bearer TOKEN` -> replace. `GET /v1/maps/{id}` -> editable body (no `areas` field: shapes are already resolved; includes `image`, which `set` drops so no render is triggered).
- Files: `/m/{id}.geojson`, `/m/{id}.png`, `/oembed?url=`.
- View params: `?basemap=`, `marker=dot|pin|circle|none`, `color=hex`, `cluster=1`, `labels=1`, `embed=1`.
- Errors: 400 bad input (read `hint`), 401/403 token, 404 unknown or expired, 413 over 2 MB, 429 rate limit (`Retry-After`), 503 preview temporarily unavailable.
- Limits: 50 places, 60 creates/min/IP, maps expire after 30 days without views, cannot be deleted.

## MCP equivalents
`create_map` = create; `get_map` = get (editable body); `update_map` = update with the edit token (merge the change into the `get_map` body first). Use only when Python is unavailable.

## Rich place body (default shape)
```json
{"title":"Specialty coffee in Vienna","places":[{"q":"Gumpendorfer Strasse 11, Vienna","title":"Cafe Sperl","description":"Classic coffee house; check before you go.","category":"Coffee house","marker-symbol":"☕","address":"Gumpendorfer Str. 11, 1060 Wien","url":"https://www.cafesperl.at/","image":"https://upload.wikimedia.org/...jpg","Known for":"Apple strudel","Opening hours":"Mon-Sat 7-22"}]}
```
Standard keys: `address`, `phone`, `opening_hours`, `price`, `rating`, `website` (alias of `url`), `email`, `instagram`. Any other key (Title Case, e.g. `Known for`) shows as a detail line. Map option `directions` (default on) adds a Directions button. See `place-details.md`.
