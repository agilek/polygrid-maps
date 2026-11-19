# Polygrid Maps

Polygrid Maps turns places, trips, routes and data per area into a live, shareable, editable web map. The `polygrid-maps` MCP server (https://maps.polygrid.dev/mcp, no account or API key) provides the tools; the bundled `create-map` skill holds the full workflow.

- When the user asks to "make a map of", pin or plot places, build a trip or itinerary map, or map numbers per region/country, activate the `create-map` skill and call the `create_map` tool (`get_map` / `update_map` to read or change a map made earlier).
- Give the user the share link. Keep the private edit link for later changes; do not post it publicly.
- Never invent data for shaded (choropleth) maps. Talk about places, pins and colors, not JSON or tokens.
- Not for charts, diagrams, mind maps, sitemaps, code maps, or directions the user only wants to read.
