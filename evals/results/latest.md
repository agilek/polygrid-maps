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
| 9 | place-not-found | 4/5 (1c) |
| 10 | send-to-friends-with-edit-link | 3/4 (1c) |
| 11 | bike-route | 5/5 (1c) |
| 12 | czech-language | 4/5 (1c) |
| 13 | rich-details-coffee | 4/6 (1c) |
| 14 | rich-details-sights | 4/5 (1c) |

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

- 9 place-not-found [skill] (transcript: results/raw/quality/eval-09-place-not-found.skill)
  - The final answer tells the user in plain words which place could not be found (Zzyqx...) and offers to try ano -- Says: "I couldn't find \"Zzyqx Quorbel Cafe 99\", so it isn't on the map. If you send me its street address or the spelling you have, I'll add it." This names t
- 10 send-to-friends-with-edit-link [skill] (transcript: results/raw/quality/eval-10-send-to-friends-with-edit-link.skill)
  - The final answer shows no raw JSON blocks, curl commands, HTTP error codes, or API words (endpoint, oEmbed, to -- The answer says "That part is the secret edit token", which uses the API word "token". It also code-formats `/edit` and `#t=…`, though the `#t=` part is allowed
- 12 czech-language [skill] (transcript: results/raw/quality/eval-12-czech-language.skill)
  - Only real, verifiable pubs are included (no invented URLs in popups) -- Only the Vinohradský pivovar popup has a URL, and it comes from a search result. The transcript doesn't verify the other four places. The assistant admits it fo
- 13 rich-details-coffee [skill] (transcript: results/raw/quality/eval-13-rich-details-coffee.skill)
  - Fast mode: every place has a short description; at least half have address or url from search results -- All 9 places have descriptions, but addresses were typed from memory/not clearly from search results; Jonas Reindl (Währinger) has no address. Also no evidence 
  - No invented-looking data; omitted when unconfirmed; say if not verified -- Addresses like Kaffemik Zollergasse 5, Akrap Königsklostergasse 7, Café Exchange Georg-Coch-Platz 2 appear without visible source confirmation; descriptions lik
- 14 rich-details-sights [skill] (transcript: results/raw/quality/eval-14-rich-details-sights.skill)
  - Fast mode (owner prefers speed): every place has a short description saying why it is on the map; at least hal -- All six places have short descriptions, but none has an address or url. No search was done, and the answer says 'I left them out'. Half the places must have an 

Map creates (incl. setup): 27; png calls: 0

## Plugin 0.0.9 run (2026-11-20, 5-line answer template; ~18 creates, no png)
Quality rows above and followups 101/106 (skill) are from 0.0.9 transcripts, regraded. Trigger section is pre-0.0.8. First-grade quality total 74/78; regrade moves 12 and 13 by grader noise (13 was 6/6, now 4/6).
