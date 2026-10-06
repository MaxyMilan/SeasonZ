"""slum_roof6: a tarp stretched over four poles as a roof, its front hanging down steeply (Expansion mapping).

(Opus, 6 Oct, e1; Astra McClintock/Feynman) the snow ran on down the hanging front of the tarp as long torn flaps
around its opening, also with snow held only to 40 degrees and a short lip. The blanket recipe instead (H.auto: each
top region its own blanket that follows the tarp's surface and stops where it turns steep)."""
import snow_hand as H


def build(m, v):
    return H.auto(m, v)
