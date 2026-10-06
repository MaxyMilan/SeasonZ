"""boathouse_piert: a boathouse pier walkway on posts.

(Opus, 6 Oct, b1) the deck's v7 lip curled down around the posts towards the braces. A short lip (30% of the
depth + 1 cm, sinking 1.6 cm at most), thin rails ridges."""
import snow_hand as H


def build(m, v):
    return H.consts(m, v, fn=lambda m_, v_: H.big_tops(m_, v_, 0.01), A7_OVL=0.3, A7_LIPDROP=0.05, A7_THIN=0.07)
