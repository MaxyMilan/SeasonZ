"""slum_roof6: a tarp stretched over four poles as a roof, its front hanging down steeply (Expansion mapping).

(Opus, 6 Oct, e1; Astra McClintock) the snow ran on down the hanging front of the tarp as long torn flaps around its
opening. Snow holds to 40 degrees, full depth to 25, a short lip: the hanging front stays bare."""
import snow_hand as H


def build(m, v):
    return H.consts(m, v, fn=lambda m_, v_: H.big_tops(m_, v_, 0.01), A5_STEEP_SMOOTH=40.0, A5_FULL_SMOOTH=25.0,
                    A7_OVL=0.15, A7_LIPDROP=0.03)
