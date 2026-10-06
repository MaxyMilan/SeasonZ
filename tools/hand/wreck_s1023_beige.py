"""wreck_s1023_beige: a wrecked Skoda 1203 van (Expansion mapping).

(Opus, 6 Oct, e1; Astra Boyle) the roof clean, but the cowl ledge under the windscreen and the bumper top grew torn,
pointed patches and loose blobs with bare gaps (c3_v7). Ledges reaching up to 80 cm from a bigger top stay bare
(the default reach 40 cm missed the cowl under the long roof)."""
import snow_hand as H


def build(m, v):
    return H.wreck(m, v, LEDGES=[0.08, 0.8])
