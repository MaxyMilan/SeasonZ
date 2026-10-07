"""workshop_fuelstation: a small workshop with a flat roof, a railing and a side stair (Expansion mapping).

(Astra Socrates, 7 Oct 2026, e2) the volumetric roof retained a deep angular trough and diagonal folds beside the
parapet even when early depths reused v3. Each exposed roof surface now gets a surface-following blanket at its
actual depth, with short lips and smoothing. Separate parapet levels do not bury snow down onto the inner roof.
(Astra Euclid, 7 Oct 2026, e2) review #3 found tall sheets filling the sign's open brace triangles. The diagonal
braces, upright sign posts and slender lower crossbars now let snow through. The broad top sign beam remains eligible."""
import snow_hand as H


def build(m, v):
    sign = (54, 55, 56, 57, 58, 59, 78, 85, 86, 87, 88, 89, 90, 91, 92, 93, 94)
    H.through(m, sign)
    # The explicit log/beam routes also read source geometry, so exclude the sign
    # fittings there as well as in the raster and occlusion tables.
    eligible = [p for p in range(int(m.part_t.max()) + 1) if p not in sign]
    logs = [p for p in eligible if m.is_log(p)]
    beams = [p for p in eligible if p not in logs and m.is_beam(p)]
    out = [m.log(p, v) for p in logs] + [m.beam(p, v) for p in beams]
    out.append(m.cover(v, m.tops(v, exclude=logs + beams), over=0.025,
                       smooth=0.05, bury=False))
    # The high top bar must not be a wall in the roof blanket's height map.
    # Give that actual 12 cm horizontal support its own narrow beam ridge.
    out.append(m.beam(92, v, step=0.2))
    return H.join(out)
