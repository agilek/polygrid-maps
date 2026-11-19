# Rich place details (default for every map)

A pin with only a name and one line is not useful. Give every place a popup someone can act on.

## Always
- `title`, plus `description`: 1-2 friendly sentences on why it is worth going (what to order or see, the vibe). No marketing filler.
- `category` and an emoji `marker-symbol` (when there are several kinds).
- `address`: street and number, as the venue or a reliable source writes it. Also use it in `q` for geocoding.
- `url`: the official website; if none, a reliable page about it (Wikipedia, the city's tourism page). Optional keys when a source confirms them: `phone`, `email`, `instagram`, `opening_hours`, `price`, `rating`.
- `image`: only a real https photo you found on the venue's own site or Wikimedia Commons (upload.wikimedia.org). It must load (check it returns an image), not be hotlink-protected, and not be a tracking or signed URL. No photo found: omit it.
- 2-4 extra fields for the map's purpose. Use human-readable Title Case keys with spaces ("Known for", not `known_for`); values are short strings.

## Recipes (extra fields by purpose)
| Map | Extra fields |
|---|---|
| Coffee, cafes, bars | Known for, Neighbourhood, Price, Opening hours |
| Restaurants | Cuisine, Price, Book ahead? |
| Sights, museums | Opening hours, Tickets, Time needed |
| Trip / itinerary | Day, Time, Duration |
| Hikes, runs, rides | Distance, Elevation, Surface |
| Hotels | Area, Price per night |
| Events | Date, Time, Tickets |
Pick the 2-4 that a source confirms; skip the rest. Other purposes: choose the fields a visitor would ask about.

## Research rules
- Use web search / fetch when you have it: the venue's own site first, then a reliable guide or map listing. Fill a field only when a source confirms it.
- Never invent addresses, hours, prices, ratings, URLs or photos. Unknown means omit the field; a missing field beats a wrong one.
- Opening hours change: when shown, end the description with "check before you go". Prices: write them as the source does ("EUR 4.50 espresso", "$$") or as a range.
- Speed: research at most ~10 places in depth (all fields). For longer lists do the top ones fully and the rest basic (title, description, address, url).
- No web access: use only what you reliably know (well-known landmarks, their address and official site), do not guess for small venues, and say once in the answer that details were not verified.

## Example place
```json
{"q":"Kaffeefabrik, Gumpendorfer Strasse 7, Vienna","title":"Example Roasters","category":"Specialty coffee","marker-symbol":"☕",
 "description":"Small roastery with a bright flat white and house-baked cake. Check before you go: hours change.",
 "address":"Examplegasse 1, 1010 Vienna","url":"https://example.com","image":"https://upload.wikimedia.org/.../photo.jpg",
 "Known for":"Single-origin filter","Neighbourhood":"Neubau","Price":"Espresso about EUR 3.50","Opening hours":"Mon-Fri 8-18, Sat 9-17"}
```
(Illustrative only; use real sources.)
