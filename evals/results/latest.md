# Eval results (2026-11-20, model sonnet)

## Trigger

54/58 queries; recall 86%, precision 100%
- MISS (0/3): Here is the map I made yesterday https://maps.polygrid.dev/edit/abc123XYZ?key=k9f2 - can y
- MISS (0/3): i have a list of 40 bakeries from my notes (Poilane, Du Pain et des Idees, Le Grenier a Pa
- MISS (0/3): make a map with just 3 points, Big Ben, Tower of London and Buckingham Palace. tiny, nothi
- MISS (0/3): Can you add a pin for the Sagrada Familia to the map we were working on and give me the li

## Quality (skill mode)

| id | scenario | skill |
|---|---|---|
| 1 | concrete-no-question | 8/8 (1c) |
| 2 | ambiguous-layout-options | 5/6 (0c) |
| 3 | choropleth-berlin | 7/7 (1c) |
| 4 | modify-same-chat | 6/6 (1c) |
| 5 | new-chat-edit-link | 6/6 (1c) |
| 6 | share-link-only | 6/6 (1c) |
| 7 | embed-code | 4/4 (1c) |
| 8 | geojson-export-google-my-maps | 5/5 (1c) |
| 9 | place-not-found | 5/5 (1c) |
| 10 | send-to-friends-with-edit-link | 4/4 (1c) |
| 11 | bike-route | 5/5 (1c) |
| 12 | czech-language | 5/5 (1c) |
| 13 | rich-details-coffee | 5/7 (1c) |
| 14 | rich-details-sights | 3/6 (1c) |

## Followups

| id | scenario | skill | docs-only |
|---|---|---|---|
| 101 | barcelona-add-routes | 10/10 (1c) | 10/10 (1c) |
| 102 | barcelona-make-dark | 8/8 (1c) | 8/8 (1c) |
| 103 | barcelona-separate-map-control | 7/8 (2c) | 8/8 (2c) |
| 104 | pasted-edit-link-add-route | 9/9 (1c) | 7/9 (1c) |
| 105 | road-trip-by-car | 8/8 (1c) | 8/8 (1c) |
| 106 | barcelona-kids-mode-then-drive | 9/10 (1c) | 10/10 (1c) |

## Failed assertions

- 2 ambiguous-layout-options [skill] (transcript: results/raw/quality/eval-02-ambiguous-layout-options.skill)
  - It offers 2 or 3 concrete layouts (e.g. by category, numbered, clustered) each with a one-line reason -- Three layouts are offered. Option 1 has a reason ('my pick for sending to family') and option 2 has one ('cleanest, with no filtering'). Option 3 only describes
- 13 rich-details-coffee [skill] (transcript: results/raw/quality/eval-13-rich-details-coffee.skill)
  - In the map body, most places (at least 70%) have both an `address` and a `url` -- All 8 places have an address but none has a url field; the answer says no website links were added.
  - Places carry 2 or more extra purpose fields beyond title/description (e.g. Known for, Neighbourhood, Price, Op -- Places only have category, marker fields, address and description. There are no Title Case extra fields such as Known for or Neighbourhood.
- 14 rich-details-sights [skill] (transcript: results/raw/quality/eval-14-rich-details-sights.skill)
  - In the map body, most places (at least 70%) have both an `address` and a `url` -- The places in the JSON only have q, title, description, category and marker-symbol. No address or url was supplied. The service may have filled them in, but the
  - Places carry 2 or more extra purpose fields (e.g. Opening hours, Tickets, Time needed) with Title Case keys -- No extra fields like Opening hours, Tickets or Time needed appear in the place data.
  - The final answer says in one line what the popups contain (address, website, hours, photo, Directions) -- The answer says: "Each pin has a short description, and your parents can tap Directions". It doesn't mention an address, website, hours or photo.
- 103 barcelona-separate-map-control [skill] (transcript: results/raw/followups/eval-103-barcelona-separate-map-control.skill)
  - The final answer shows no raw JSON blocks, curl commands, HTTP error codes, or API words (endpoint, oEmbed, to -- Both answers say 'a website embed' and 'a download for QGIS or Google My Maps', which is plain language. But the private edit URLs contain '#t=...' token fragme
- 104 pasted-edit-link-add-route [docs-only] (transcript: results/raw/followups/eval-104-pasted-edit-link-add-route.docs-only)
  - [api] no technical narration (API, token, proxy, plugin, JSON...) in answers -- found=[(1, 'json')]
  - The final answer shows no raw JSON blocks, curl commands, HTTP error codes, or API words (endpoint, oEmbed, to -- The final answer mentions a backup file in code formatting, `/tmp/berlin-backup.json`, and says 'original map data'. This is technical detail that a non-technic
- 106 barcelona-kids-mode-then-drive [skill] (transcript: results/raw/followups/eval-106-barcelona-kids-mode-then-drive.skill)
  - The first answer states the travel mode in one plain line (e.g. walking with metro between areas) and offers t -- The first answer describes modes only inside per-day bullets (metro for Day 1, about 5 km walking plus one metro hop for Day 2). It has no single plain line sta

Map creates (incl. setup): 27; png calls: 0

## Targeted rerun after plugin 0.0.8 (2026-11-20, sonnet, 4 creates, no png)
- Trigger, 4 earlier misses + 10 random negatives x3: all 4 now trigger (3/3, 3/3, 3/3, 2/3), negatives 0/3 each: recall 29/29 on this subset, precision 100%.
- Quality 13 rich-details-coffee: 5/7 -> 5/7 (1 search done, addresses present, still no url and no Title Case extra field).
- Quality 14 rich-details-sights: 3/6 -> 2/6 (Lisbon landmarks are exempt from search under the new fast-mode wording, so no address/url; also edit link inline, not on its own line). Scenario 14 now conflicts with the guidance; use non-landmark places or relax the assertions.
- Followups 106 skill: 9/10 -> 10/10. Followups 104 docs-only: 7/9 -> 9/9.
