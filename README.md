# SeasonZ (v0.5.3)

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
  - roofs: a slab of snow on the roof planes of the buildings around the player (out to 220 m), ending in straight
    lines at the rim, along ridges and hips and around chimneys and dormers; thin on steep roofs, none on the steepest
  - ledges, walls, fences, car wrecks, open sheds, containers, platforms, bridges and big rocks carry snow too, and
    near the player so do small structures: benches, boxes, hay bales, concrete blocks and barriers
  - trees and bushes: swapped for snow laden Frostline (Sakhal) models while there is snow, out to 1.6 km in clear
    air and as far as the fog lets the game draw them
- Trees: bare branches in late autumn and early spring, fresh green foliage (Livonia summer models) in late spring and summer
- Ponds and lakes freeze over and carry players once the ice is thick enough (Chernarus); frozen ponds give no water
  and no fish, and the snow can be eaten and melted for water
- Winter food: crops grow only above a daily mean of 5 °C and die outdoors at -2 °C; greenhouses and polytunnels keep
  them alive down to -12 °C outside. Frozen or snowed over ground cannot be sown. Wild berries and most mushrooms
  spawn spoiled or dried in the cold
- Lighting and colour grading per season and snow cover
- Footsteps sound and puff like snow on the snow cover; footprints and tyre tracks fill up again during snowfall

Tree swaps and all snow are client side visuals: the real map objects stay where they are for collision, chopping and
persistence. Snow on trees needs the Frostline data (all DayZ 1.29 installs have it), summer foliage the Livonia data.
The tree swaps are mapped for the Chernarus tree species.

## Known limits

- Made for Chernarus. Livonia gets the climate and weather but no pond ice; on Sakhal the mod stays off. Other maps
  are not tested.
- Grass stays on pond banks and on coastal ground below the sea's water line: the game ignores grass cutters there.
- Every snow piece is its own object, so the big towns (Chernogorsk, Elektrozavodsk) cost noticeably more frame rate
  in winter than villages and open country.
- Walls and fences carry snow out to 160 m (fences with an uneven top to 80 m), small structures out to 90 m.
- Under bridges the edge of the snow cover is jagged.

## Server configuration

`$profile:SeasonZ/config.json`, in the folder the server's `-profiles` parameter points to. It is created with
the defaults on the first start. Stop the server before editing it; the settings are read once at server start. A
config.json with a JSON error is ignored for that session (the defaults apply and the script log says so).

| Setting | Default | Meaning |
| --- | --- | --- |
| `Mode` | `"RealTime"` | `"RealTime"`: follow the calendar date of the server machine. `"Multiplier"`: own season clock |
| `SeasonSpeedMultiplier` | `12` | Multiplier mode: season years per year of server uptime (1 = a year, 12 = a month, 52 = a week, 365 = a day, 0 = hold the date) |
| `SpringLengthMultiplier`, `SummerLengthMultiplier`, `AutumnLengthMultiplier`, `WinterLengthMultiplier` | `1` | Multiplier mode: relative length of each season (2 = twice as long), 0.05 to 20 |
| `StartDayOfYear` | `335` (1 December) | Multiplier mode: day of the year (1-365) a new clock starts at; an existing clock in state.json keeps running |
| `SnowBuildupMultiplier` / `SnowMeltMultiplier` | `1` | how fast snow builds up and melts, 0 to 100 |
| `WinterHaze` | `1` | haze while snow lies: 0 = off, up to 2 = thicker. Less haze shows more of the snowy world at a lower frame rate |
| `ConfigVersion` | `2` | managed by the mod |

Values out of range are clamped and the checked config is saved back. The season clock runs while the server runs.

`$profile:SeasonZ/state.json` holds the running season clock, snow depths and pond ice. To start over at
`StartDayOfYear`, stop the server and move state.json away: the snow and the ice then start from the climate of that
date (deep snow in January, none in summer).

## Install

Server: copy the whole `@SeasonZ` folder, add it to `-mod=` (it must run on the server and on every client),
and copy `@SeasonZ/keys/SeasonZ.bikey` into the server's `keys` folder. Clients load the same mod.

SeasonZ sets the calendar date (the time of day stays) and changes weather, lighting, trees, farming and food. Test it
together with other mods that change the same things.
