"""ruin_slum_house4: a collapsed slum shack: leaning boards, sheet panels, a tyre and junk (Expansion mapping).

(Astra Socrates, 7 Oct 2026, e1) the reviewer could not resolve the bare rear panels' slope. Geometry confirms
parts 3 and 22 each have about 2.7 m2 facing within 37 degrees, and substantial further area within 45 degrees;
the old 30-degree cutoff removed legitimate snow. Keep the selective large-panel filter, then blanket exposed
cells within about 44 degrees. Small rods and steep junk let snow through; short lips do not bury down their sides."""
import snow_hand as H


def build(m, v):
    n = int(m.part_t.max()) + 1
    big = [p for p in range(n) if H.part_top_area(m, p, ny_min=0.8) >= 0.15]
    H.through(m, [p for p in range(n) if p not in big])
    tops = m.tops(v, parts=big, ny_min=0.72) & (m.NYF >= 0.7)
    return m.cover(v, tops, over=0.02, smooth=0.04, bury=False)
