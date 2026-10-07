"""boat_small6: a large broken wooden hull with exposed ribs, decks and floor planks (Expansion mapping).

(Astra Socrates, 7 Oct 2026, e2) the ribs carried tall strips and blobs; deck edges folded down around holes.
Only the broad deck and floor panels hold snow. Ribs, posts, keel and small fittings let snow through. Nearly
flat exposed cells receive separate blankets per panel with 5 mm lips. Narrow side fragments are excluded from
the broad hull panel's regions, without burial down adjoining vertical faces."""
import numpy as np
import snow_hand as H
import snow_addon as A

PANELS = (0, 2, 3, 14, 15, 37, 38)


def build(m, v):
    H.through(m, [p for p in range(int(m.part_t.max()) + 1) if p not in PANELS])
    out = []
    for p in PANELS:
        tops = m.tops(v, parts=(p,), ny_min=0.8) & (m.NYF >= 0.8)
        if p == 3:
            # Hull-shell rim fragments beside the upper deck are not floor panels.
            deck_bottom = float(m.V[m.T[m.part_t == 2], 1].min())
            tops &= m.Z < deck_bottom - 0.1
            tops &= H.dilate(H.erode(tops, 2), 2)
        for R, Zc in m.regions(tops, v, close=0.0, min_area=0.025):
            cap = m.blanket(R, Zc, v, over=0.005, shoulder=0.25, smooth=0.02,
                            fill=0.01, bury=False, holes=0.002)
            out.append(cap)
    cap = H.join(out)
    if cap is not None and len(cap[1]) > 10000:
        return A._err_decimate(np.asarray(cap[0], float), np.asarray(cap[1], np.int64), 10000, 0.0025)
    return cap
