"""boat_small5: a small wrecked wooden boat, its ribs and broken planks open (Expansion mapping).

(Astra Socrates, 7 Oct 2026, e1) upright ribs and posts grew vertical strips into the hull openings. The floor,
thwarts and broad deck planks alone hold blankets; hull ribs, posts and steep side planks let snow through.
Only nearly flat exposed cells are eligible. Joining adjacent broken planks made pointed end flaps, so each
plank receives its own round blanket with a 5 mm overhang and a small shoulder, without bridges to the hull.
Taper was rejected because its width-dependent fade made deep snow thinner instead of allowing growth."""
import snow_hand as H
import snow_addon as A
import numpy as np

PANELS = (7,) + tuple(p for p in range(12, 45) if p != 30)

def build(m, v):
    H.through(m, [p for p in range(int(m.part_t.max()) + 1) if p not in PANELS])
    out = []
    for p in PANELS:
        tops = m.tops(v, parts=(p,), ny_min=0.8) & (m.NYF >= 0.8)
        for R, Zc in m.regions(tops, v, close=0.0, min_area=0.015):
            out.append(m.blanket(R, Zc, v, over=0.005, shoulder=0.25, smooth=0.02,
                                 fill=0.01, bury=False, holes=0.002))
    cap = H.join(out)
    if cap is not None and len(cap[1]) > 8000:
        return A._err_decimate(np.asarray(cap[0], float), np.asarray(cap[1], np.int64), 8000, 0.0025)
    return cap
