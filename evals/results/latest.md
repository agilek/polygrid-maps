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
| 2 | ambiguous-layout-options | 6/6 (0c) |
| 3 | choropleth-berlin | 7/7 (1c) |
| 4 | modify-same-chat | 6/6 (1c) |
| 5 | new-chat-edit-link | 6/6 (1c) |
| 6 | share-link-only | 6/6 (1c) |
| 7 | embed-code | 4/4 (1c) |
| 8 | geojson-export-google-my-maps | 5/5 (1c) |
| 9 | place-not-found | 5/5 (1c) |
| 10 | send-to-friends-with-edit-link | 4/4 (1c) |
| 11 | bike-route | 5/5 (1c) |
| 12 | czech-language | 4/5 (1c) |
| 13 | rich-details-coffee | 5/6 (1c) |
| 14 | rich-details-sights | 2/5 (1c) |

## Followups

| id | scenario | skill | docs-only |
|---|---|---|---|
| 101 | barcelona-add-routes | 10/10 (1c) | 10/10 (1c) |
| 102 | barcelona-make-dark | 8/8 (1c) | 8/8 (1c) |
| 103 | barcelona-separate-map-control | 8/8 (2c) | 8/8 (2c) |
| 104 | pasted-edit-link-add-route | 9/9 (1c) | 9/9 (1c) |
| 105 | road-trip-by-car | 8/8 (1c) | 8/8 (1c) |
| 106 | barcelona-kids-mode-then-drive | 10/10 (1c) | 10/10 (1c) |

## Failed assertions

- 12 czech-language [skill] (transcript: results/raw/quality/eval-12-czech-language.skill)
  - Only real, verifiable pubs are included (no invented URLs in popups) -- The popups contain no URLs. But 'Malý pivo' was geocoded from a street address the search results never showed, and the claim 'hodnocení 4.9 na Firmy.cz' is not
- 13 rich-details-coffee [skill] (transcript: results/raw/quality/eval-13-rich-details-coffee.skill)
  - No invented-looking data: fields are omitted when no source confirmed them; if there was no web access the ans -- Only one search is visible, and its results are truncated. The Viennese Coffee Roastery pin was moved to a guessed address ('Praterstraße 80, which is my guess'
- 14 rich-details-sights [skill] (transcript: results/raw/quality/eval-14-rich-details-sights.skill)
  - Fast mode (owner prefers speed): every place has a short description saying why it is on the map; at least hal -- All six places have descriptions, but the answer says 'I added no addresses or websites' and no web search was done, so none of the places has an address or url
  - The answer offers in one line to add more detail (e.g. hours, photos) on request, instead of researching every -- The answer lists possible changes (route, restaurants, dark map) and other formats. It has no one-line offer to add more detail such as hours or photos.
  - The share link is on its own line and the edit link is separate and labelled private -- The share link is on its own line in the heading. The edit link is in a paragraph, after text: 'Keep it to yourself and don't send it to your parents: https://.

Map creates (incl. setup): 27; png calls: 0

## Targeted rerun after plugin 0.0.8 (2026-11-20)
Trigger: the 4 earlier misses now trigger (3/3, 3/3, 3/3, 2/3), 10 random negatives 0/3 (precision 100%). The Trigger section above is the pre-0.0.8 full run. Rows 13, 14, 104 (docs-only) and 106 (skill) above are from the 0.0.8 rerun transcripts, regraded with the fast-mode assertions. 12 flipped to a fail on regrade only through grader noise (earlier 5/5).
