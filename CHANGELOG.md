# SeasonZ changelog

## 0.5.2

- 1,377 active snow caps in seven depths, with 27 intentional skips. The hand register contains
  1,381 approved models and one skipped compatible model; four approved caps remain archived only.
- Ground snow is built and removed in smaller batches to reduce movement stutter. Reviewed roof,
  tree, pond and cleanup fixes are included. These budgets cannot interrupt an individual engine call.
- Grass maintenance in smaller batches is included but defaults to OFF. Existing snow detail and
  distance settings are retained. Experimental chunk streaming and mesh batching are not shipped.
- Saves validate their contents and retain recovery copies. High season speeds now process snow and
  ice in steps, saving unfinished work across restarts. One-time old-profile migration and leap-date
  handling are included; independent-account join-in-progress and leap-day injection remain untested.
- Pond carrying history is saved and sent to clients. Missing server ice coverage can be rebuilt
  before rescuing a swimmer; the reported restart failure passed targeted native retests.
- Snow creation can retry failures; roof rescans resume and lost owners are removed. Movable snow
  responds to roll and scale. Hard frost affects living paused crops. Footprints and tyre tracks fill
  according to snowfall exposure and retain their age order; snowy-ice prints clear on thaw.
- All visual LODs of footprint and tyre-track models have shadow casting disabled. The generator
  already preserved this setting; no model correction was needed.
- Released to the server and PC as 18 signed PBOs, each below 2 GB, with flat prefixes. Signatures,
  local script loading and deployment hashes passed. Detailed QA still has open cases, including
  snow actions under bare shelter; model polish can continue from user reports.

## 0.5.1 (snow caps, second pass)

Every cap was made again with a stricter generator, checked by geometric measurements on all 1,285 models and
depths and by a visual review of every model.

Snow caps
- Tents, camouflage nets and polytunnels: the snow follows the shape of the whole sheet and ends in one soft line
  down the canvas; no more hanging tongues along quilted tent walls, no blobs in the pockets of a net, and the snow
  lies on the canvas under the tent poles instead of standing on them as posts. Canvas and the face of the dam
  shed snow from about 47 degrees.
- Stairs: every tread gets its own strip of snow with a rounded front; no false step halfway up each riser and no
  torn sheet over the stairs.
- Flat roofs with a parapet, kerbs and beam tops: the narrow level strips carry snow (the parapets of large flat
  roofed blocks, schools and garages showed dark).
- Stacks of pallets, logs, timbers and planks: each board and log has its own cap; the snow bridges the narrow gaps
  between them instead of tearing into flaps and tents over them. Brick stacks are made on a finer grid.
- Heaps of junk and rubble: the snow drapes over the small steps between their parts; boxes standing on a heap no
  longer pull the snow up into a spike.
- Earth mounds (bunker berms, blast covers, craters): the snow line follows the mound, not every lump of earth.
- Fuselages, curved tanks and walls rising beside a roof: the snow ends along them in one line instead of a row of
  small teeth; no more dark slits along the crease where a bunker dome meets its berm.
- Lids, slabs and signs: the top of the snow runs out to its rounded edge without a dark band and dark corner
  wedges; narrow tops (the top edge of a sign board) hold a strip of snow in proportion instead of a round sausage.
- Small holes in a cover, pits between boards and bolt holes the grid fell into are bridged.

Seasonal trees
- A map tree that had been shown as its Livonia summer twin (willows, among others) no longer disappears when its
  leaves turn in autumn.

## 0.5.0 (MVP release candidate)

The mod is now called SeasonZ everywhere (mod folder `@SeasonZ`, key `SeasonZ.bikey`, profile folder
`SeasonZ`). A server that ran the mod under its old name keeps its settings and its season: `config.json` and
`state.json` are taken over once from the old profile folder. Replace the old key with `SeasonZ.bikey`.

Snow caps made for every model (new)
- The snow on 912 Chernarus models is now a cap made for that model from its own visible geometry, in seven
  depths from a light dusting to 25 cm and more. The cap follows the real surface: it covers ridge tiles, fills
  valleys and the grooves of corrugated sheet, gives chimneys, dormers, porch roofs, window sills, battlements and
  tower ledges their own snow, ends at the eaves with a rounded edge (a small cornice in deep snow) and tucks
  under walls and chimneys rising out of a roof. Rocks get a cap that thins out into the stone and grows over
  steeper faces as the snow deepens; walls and fences a small cap per post, picket and plank. Heaps, sandbags,
  HESCO barriers, camouflage nets, rubble and graves get a cap that thins out like on a rock and bridges the gaps
  between their parts.
- No floating plates, white boards on round tanks or flat lids on barriers any more: snow lies only where the model
  is.
- Clean edges: the snow ends along ledges, eaves and broken wall tops in one rounded edge, without teeth, notches,
  flaps or a dotted line of pits along the joints of roof sheets.
- One object per model instead of hundreds of sampled snow pieces. Together with the lighter ground snow below:
  Chernogorsk 27.7 to 45-47 fps in the test scene (+65%, no more frames over 8 ms from the roof snow),
  Elektrozavodsk 41.4 to 55 fps (+33%), a village 40.2 to 42 fps (+4%).
- A new snow depth reaches all baked caps around the player within a few seconds (it took up to a minute while
  other roofs were being built).
- 405 models carry no snow on purpose (road signs, ropes, decals, thin railings, models made of proxies only), and
  the manure heap stays bare (it is warm).
- Models standing tilted more than 12 degrees, or under another object, keep the sampled roof snow.

Ground snow at a distance
- Level 0 snow cover more than 70 m from the camera is cut around buildings with 1.9 m triangles instead of 0.94 m
  (still along the walls): a third fewer ground snow objects in a town (Chernogorsk 41,900 to 26,900), +23% frame
  rate there, without a visible difference.

Names
- All assets and code use the SeasonZ name (sz_ instead of ds_ for models, materials and textures).

Snow on buildings and objects (sampled roof snow, still used for tilted and covered models)
- Roof snow reaches the corners of roofs, the valleys between roof planes and the junctions of two roofs.
- Snow reaches up to chimneys and masts that stand out of a roof.
- No folded flaps or pyramids where a mast foot, a vent or a lightning rod stands on a roof, also close to the
  eaves.
- At roof corners and the foot of a hip the snow follows the overhang down instead of standing out as a level
  shelf.
- Valleys between roof planes are filled smoothly instead of in a row of steps.
- No tilted snow slabs on HESCO barriers.
- Snow on the Livonia objects placed on Chernarus (wrapped hay bales, tractor wrecks, sheds, pipes, bus stops)
  and on transformers.
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
- Less script time per frame in towns: structures whose snow is built are checked in turns (Elektro: 1.4 ms per
  frame before).
- Footprints last longer during snowfall (10 minutes at full snowfall, up to an hour in light snow) and are not
  made while sitting in a vehicle.
- Grass cleanup no longer causes a short hitch every second while standing still.
- README: defaults of every setting, restart after changing config.json, what a reset of state.json does, crop
  limits (greenhouses protect down to -12 C), supported maps and install steps.

