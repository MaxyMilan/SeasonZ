"""mil_camonet_roof_east: a camouflage net stretched flat on poles as a roof.

(Opus, 6 Oct, b1) the net's ragged edge tore the cap into open bites with small flaps hanging under it at v1-v4.
A short lip (30% of the depth + 1 cm, sinking 1.6 cm at most), thin strips a ridge."""
import snow_hand as H


def build(m, v):
    return H.consts(m, v, fn=lambda m_, v_: H.big_tops(m_, v_, 0.01), A7_OVL=0.3, A7_LIPDROP=0.05, A7_THIN=0.07)
