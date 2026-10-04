# SeasonZ changelog

## 0.5.0 (MVP release candidate)

The mod is now called SeasonZ everywhere (mod folder `@SeasonZ`, key `SeasonZ.bikey`, profile folder
`SeasonZ`). A server that ran the mod under its old name keeps its settings and its season: `config.json` and
`state.json` are taken over once from the old profile folder. Replace the old key with `SeasonZ.bikey`.

Snow on buildings and objects
- Roof snow reaches the corners of roofs, the valleys between roof planes and the junctions of two roofs.
- Snow reaches up to chimneys and masts that stand out of a roof.
- Far buildings (90 to 220 m) carry snow up to the rim of the roof.
- Ramps and loading platforms keep their snow; stairs still show their steps.
- Small buildings (outhouses, coops, kennels), loose stones, bins, well pumps, sandboxes and the corner pieces of
  walls carry snow; structures without fire geometry are sampled on their collision geometry.
- No snow bridging the gaps of fences, benches, sawhorses and racks; no snow slabs over stairs; no snow on barrels;
  no white blocks at the ends of the long straw stack.

Snow on the ground
- No ground snow inside buildings: small sheds and outhouses, greenhouses and polytunnels, halls without a roof
  in their view geometry, the corners of large halls, and under platforms inside halls.
- Snow under raised floors stays hidden; floors no longer lift the snow cover.

Other
- Footprints last longer during snowfall (10 minutes at full snowfall, up to an hour in light snow) and are not
  made while sitting in a vehicle.
- Grass cleanup no longer causes a short hitch every second while standing still.
- README: defaults of every setting, restart after changing config.json, what a reset of state.json does, crop
  limits (greenhouses protect down to -12 C), supported maps and install steps.

