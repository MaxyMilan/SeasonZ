"""wreck_hmmwv: a wrecked Humvee (Expansion mapping).

(Opus, 6 Oct, e1; Astra Boyle) a bulbous lobe over the open front wheel (the tyre's round top held snow up to 45
degrees) and torn patches at v1. Panels hold snow to 38 degrees, full weight to 22.
(e1b, Astra McClintock) ledges reaching 80 cm also stripped the equipment blocks beside the engine housing, and the
door lying in front still hung a lobe over its edge: ledges only within 25 cm, a shorter overhang (OVL .15).
(e1c) the lobe sat on the tilted front wheel (part 240, 0.19 m2 of tread looking up) and the rear wheel (220) took a
crumb: both wheels let the snow through. The small battery box (about 20 by 15 cm) stays bare (under 1 dm2)."""
import snow_hand as H


def build(m, v):
    H.through(m, (220, 240))
    return H.wreck(m, v, LEDGES=[0.08, 0.25], A5_STEEP_SMOOTH=38.0, A5_FULL_SMOOTH=22.0, A7_OVL=0.15)
