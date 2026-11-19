# Layout catalog

Pick by data signal. Offer the 2-3 best fits, best first. Mockups are for the `preview` field of AskUserQuestion (or a numbered list).

| Data signal | Layout |
|---|---|
| Mixed types (food, sights, hotels) | Categories + filter legend |
| Ordered stops | Numbered itinerary |
| Multi-day trip | Day by day |
| One kind, few (<=15) | Labeled pins |
| One kind, many (>40) | Clustered |
| Ranked or priced | Highlight the best |
| Areas or zones | Shaded areas |

## Categories + filter legend
Why: different kinds of places, viewers can show only what they want.
```
+------------------------------+
| Lisbon highlights            |
|   (R)      (M)               |
|        (R)       (P)         |
|   (M)         (R)            |
|                              |
| [Eat 6] [Sights 4] [Parks 2] |
+------------------------------+
```
```json
{"title":"Lisbon highlights","legend_title":"Type","places":[
 {"q":"Time Out Market, Lisbon","title":"Time Out Market","description":"Best food hall to sample many dishes","category":"Eat","marker-symbol":"🍴","marker-color":"#dc2626"},
 {"q":"Belem Tower, Lisbon","title":"Belem Tower","description":"Iconic riverside fortress","category":"Sights","marker-symbol":"🏰","marker-color":"#2563eb","url":"https://www.torrebelem.gov.pt/"}]}
```

## Numbered itinerary
Why: stops have an order; numbers and a line show the path.
```
+------------------------------+
|   1                          |
|    \                  3      |
|     \               /        |
|      2 ------------+         |
|                              |
|  1 Castle  2 Bridge  3 Square|
+------------------------------+
```
```json
{"title":"Prague old town walk","connect":true,"places":["Prague Castle, Prague","Charles Bridge, Prague","Old Town Square, Prague"]}
```
Use `"route":"foot"` (or car/bike) instead of `connect` to follow roads. Numbers are automatic.

## Day by day
Why: multi-day trip; one color per day, filter by day.
```
+------------------------------+
|  (1)--(2)        (4)--(5)    |
|        \          /          |
|        (3)      (6)         |
|                              |
|  [Day 1] [Day 2] [Day 3]     |
+------------------------------+
```
```json
{"title":"Rome in 3 days","legend_title":"Day","places":[
 {"q":"Colosseum, Rome","category":"Day 1","title":"Colosseum","description":"Book the first slot"},
 {"q":"Vatican Museums, Rome","category":"Day 2","title":"Vatican Museums","description":"Go early to skip queues"}]}
```
For a route per day, build `data` with one styled LineString per day, `stroke` matching the day color, and `category` "Day n".

## Labeled pins
Why: a handful of places of one kind; names visible without tapping.
```
+------------------------------+
|   (o) Cafe A                 |
|              (o) Cafe B      |
|   (o) Cafe C                 |
|                              |
+------------------------------+
```
```json
{"title":"Coffee in Vienna","labels":true,"color":"#b45309","places":["Cafe Central, Vienna","Cafe Sperl, Vienna"]}
```

## Clustered
Why: many places of one kind; groups merge into counts when zoomed out.
```
+------------------------------+
|     (12)          (7)        |
|                       .      |
|  (25)       .  .             |
|                      (9)     |
+------------------------------+
```
```json
{"title":"All our stores","cluster":true,"marker":"dot","places":["..."]}
```
Max 50 places via `places`; larger sets need `data` GeoJSON points (no geocoding).

## Highlight the best
Why: ranked or priced; the top picks stand out.
```
+------------------------------+
|   (*)          (o)           |
|        (o)           (*)     |
|   (.)       (o)              |
|                              |
| [Top pick 2] [Good 3] [OK 1] |
+------------------------------+
```
```json
{"title":"Where to stay","legend_title":"Rating","places":[
 {"q":"Hotel X, Porto","category":"Top pick","marker-color":"#16a34a","marker-symbol":"⭐"},
 {"q":"Hotel Y, Porto","category":"OK","marker-color":"#9ca3af","marker-symbol":"🛏"}]}
```

## Shaded areas
Why: zones, neighborhoods, parks, service areas.
```
+------------------------------+
|  +-------+                   |
|  | Zone A|   +-----+         |
|  +-------+   |  B  |         |
|              +-----+         |
+------------------------------+
```
```json
{"title":"Parks of Prague","labels":true,"data":{"type":"FeatureCollection","features":[
 {"type":"Feature","properties":{"title":"Letna Park","fill":"#16a34a","fill-opacity":0.3,"stroke":"#15803d"},
  "geometry":{"type":"Polygon","coordinates":[[[14.410,50.096],[14.432,50.096],[14.432,50.100],[14.410,50.100],[14.410,50.096]]]}}]}}
```

## Good-map rules
- At most 7 categories (merge the rest into "Other"); legend shown whenever there are 2+.
- Colors mean something (green parks, red food, blue sights); no near-identical colors.
- One emoji per category, consistent.
- Every popup: title plus one line saying why it is there. Add `url` / `image` (https only) only when real.
- Title says what and where. Basemap: light by default, dark for night/nightlife, streets for walking.
- Fit all places; drop far-away outliers with a warning.
