# SeasonZ - Dynamic Seasons (v0.4.0)

Seasons for DayZ Chernarus, driven by the real date or by an adjustable season clock, with a climate based on Kyiv.

## What changes with the season

- Calendar date, day length, air and water temperature (continental climate: freezing winters, warm summers)
- Weather: seasonal chances for clear/bad weather, storms, fog; precipitation falls as snow below freezing
- Winter haze while snow lies: the air is rarely clear to the horizon, which also keeps the frame rate up
- Snow cover that builds up during snowfall and melts above freezing, tracked at 0 / 250 / 500 m altitude
  - ground: follows the terrain out to 3.2 km and runs up to the walls of buildings in a straight line; it rises
    over roads and squares, while steps, porches and low blocks keep their own snow. From 4-6 cm the grass
    disappears, and from 5 cm footpaths, road decals, the kerbs around trees on squares, the grass in airfield
    panels and the reeds and weeds along ponds are buried
  - roofs: a slab of snow on every roof plane, ending in straight lines at the rim, along ridges and hips and around
    chimneys and dormers; thin on steep roofs, none on the steepest
  - ledges, walls, fences, car wrecks, open sheds, containers, platforms, bridges and big rocks carry snow too, and
    near the player so do small structures: benches, boxes, hay bales, concrete blocks and barriers
  - trees and bushes: swapped for snow laden Frostline (Sakhal) models while there is snow, out to 1.6 km in clear
    air and as far as the fog lets the game draw them
- Trees: bare branches in late autumn and early spring, fresh green foliage (Livonia summer models) in late spring and summer
- Ponds and lakes freeze over and carry players once the ice is thick enough
- Winter food: crops stop growing in frost and die in hard frost outdoors (greenhouses keep them alive); wild berries
  and mushrooms spawn spoiled or dried in the cold
- Lighting and colour grading per season and snow cover
- Footsteps sound and puff like snow on the snow cover; footprints and tyre tracks fill up again during snowfall

Tree swaps and all snow are client side visuals: the real map objects stay where they are for collision, chopping and
persistence. Snow on trees needs the Frostline data (all DayZ 1.29 installs have it), summer foliage the Livonia data.
The tree swaps are mapped for the Chernarus tree species.

## Known limits

- Grass stays on pond banks and on coastal ground below the sea's water line: the game ignores grass cutters there.
- Every snow piece is its own object, so the big towns (Chernogorsk, Elektrozavodsk) cost noticeably more frame rate
  in winter than villages and open country.
- Walls and fences carry snow out to 160 m (fences with an uneven top to 80 m), small structures out to 90 m.
- Under bridges the edge of the snow cover is jagged.

## Server configuration

`$profile/DynamicSeasons/config.json` (created on first start, profile folder = the server's `-profiles` folder):

| Setting | Meaning |
| --- | --- |
| `Mode` | `"RealTime"`: follow the real calendar date of the server machine. `"Multiplier"`: own season clock |
| `SeasonSpeedMultiplier` | Multiplier mode: 1 = one season year per real year, 12 = per real month, 52 = per week, 365 = per day |
| `SpringLengthMultiplier` ... `WinterLengthMultiplier` | Multiplier mode: relative length of each season (2 = twice as long) |
| `StartDayOfYear` | Multiplier mode: day of year (1-365) the clock starts at on the very first run |
| `SnowBuildupMultiplier` / `SnowMeltMultiplier` | how fast snow builds up and melts |
| `WinterHaze` | haze while snow lies: 1 = default, 0 = off, up to 2 = thicker. Less haze shows more of the snowy world at a lower frame rate |
| `ConfigVersion` | managed by the mod: a config.json from an older version gets the new settings at their defaults once |

`state.json` holds the running season clock and snow depths; delete it (server stopped) to restart the clock at
`StartDayOfYear` without snow.

## Install

Server: `@DynamicSeasons` in the mod list (-mod), `keys/DynamicSeasons.bikey` in the server keys folder.
Clients load the same mod.
