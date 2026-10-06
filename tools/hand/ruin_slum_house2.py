"""ruin_slum_house2: a collapsed slum shack: leaning boards, sheet panels, a tyre and junk (Expansion mapping).

(Opus, 6 Oct, e1; Astra Boyle/McClintock/Feynman) four routes left stiff sheets, pointed flaps or tall sheets on the
broken panels: the volumetric cap, the wreck route (35 degrees), the rough heap route and the blanket. Selective
instead: only the big, nearly flat panels hold snow (0.15 m2 or more of top within about 35 degrees); every other
board, rod and junk piece lets the snow through. Snow to 30 degrees (full depth to 18), a short lip, ledges bare."""
# (e1e, Astra Chandrasekhar) the corrugated tin sheets (parts 25, 26, 27, 32, 33, 34: 300-520 triangles each) kept
# blade-like strips on their crests: they let the snow through too
import snow_hand as H

TIN = (25, 26, 27, 32, 33, 34)


def build(m, v):
    n = int(m.part_t.max()) + 1
    big = [p for p in range(n) if H.part_top_area(m, p, ny_min=0.8) >= 0.15 and p not in TIN]
    H.through(m, [p for p in range(n) if p not in big])
    m._sz_parts = tuple(big)
    m._sz_rails = ([], [])
    H.ledges(m, 0.08, 0.4)
    return H.consts(m, v, A7_OVL=0.15, A7_LIPDROP=0.03, A5_STEEP_SMOOTH=30.0, A5_FULL_SMOOTH=18.0)
