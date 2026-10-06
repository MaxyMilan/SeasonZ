"""wreck_hmmwv: a wrecked Humvee (Expansion mapping).

(Opus, 6 Oct, e1; Astra Boyle) a bulbous lobe over the open front wheel (the tyre's round top held snow up to 45
degrees) and torn patches at v1. Panels hold snow to 38 degrees, full weight to 22; ledges reaching 80 cm stay bare."""
import snow_hand as H


def build(m, v):
    return H.wreck(m, v, LEDGES=[0.08, 0.8], A5_STEEP_SMOOTH=38.0, A5_FULL_SMOOTH=22.0)
