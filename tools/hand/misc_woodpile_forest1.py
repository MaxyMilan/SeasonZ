"""misc_woodpile_forest1: a pile of 24 round logs. hybrid takes every round log it detects (and sees from above) as a
log crescent; the knobbly top log 20 (branch stubs, 362 triangles) was not detected and went to the volumetric cap, which
hung down its front as a ragged fringe at every depth (r10). It gets a crescent like the rest."""
import snow_hand as H

FORCE_LOGS = (20,)


def build(m, v):
    if not hasattr(m, '_sz_rails'):
        n = int(m.part_t.max()) + 1
        logs = [p for p in range(n) if (p in FORCE_LOGS or m.is_log(p)) and H._sky_share(m, p, slant=True) >= 0.1]
        beams = [p for p in range(n) if p not in logs and m.is_beam(p) and H._sky_share(m, p) >= 0.5]
        m._sz_rails = (logs, beams)
        if logs or beams:
            m._sz_exclude = tuple(logs + beams)
    return H.hybrid(m, v)
