"""mil_tent_big4: a big military tent: a sagging, wavy canvas roof (part 0, 126 m2 of top) on poles over a boxy
inner structure (73), guy ropes.

(Opus, 6 Oct, b1) v1 left bare patches in the canvas' folds and by v4-v7 the cap rolled over the wavy edge as hanging
curtains and folds. As medical_tent_shower: only the canvas holds snow (the inner structure is under it), a short lip
(OVL .1, sinking 3 cm), a minimum layer against tears in the folds, small low ledges bare."""
# (b1b) the canvas' drooping valance along the edges still carried pointed flaps: snow holds to 40 degrees (full
# depth to 25) and the lip is shorter still, so the steep valance stays bare
import snow_hand as H


def build(m, v):
    m._sz_parts = (0,)
    m._sz_rails = ([], [])
    H.ledges(m, drop=.08, reach=.6, amin=.5, wmin=.16, jump=.08, ny=.5)
    return H.consts(m, v, A7_OVL=.05, A7_LIPDROP=.02, A7_BANDH=0.,
                    A5_STEEP_SMOOTH=40., A5_FULL_SMOOTH=25., A7_THIN=0., A7_MINLAYER=.5)
