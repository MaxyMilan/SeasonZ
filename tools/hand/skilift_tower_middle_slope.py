"""skilift_tower_middle_slope: a ski lift tower: a steel pole with cross arms and sheave assemblies.

(Opus, 6 Oct, c37) the 10-15 cm cross arms carried fat round blobs at v4-v7. Tops narrower than 16 cm get a ridge
or nothing, the lip short (20% of the depth + 1 cm, sinking 1 cm)."""
import snow_hand as H


def build(m, v):
    return H.consts(m, v, A7_OVL=0.2, A7_LIPDROP=0.03, A7_THIN=0.16)

