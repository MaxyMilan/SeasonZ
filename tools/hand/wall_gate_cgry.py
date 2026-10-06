"""Grey cemetery gate arch with a small pitched roof.
(Opus, 6 Oct, c37) the cap broke open along the ridge; tried parts with
at least 1 cm2 of top, including the ridge strip, and a short lip.
c62 has a dark notch at the small roof ridge near the upper roof.
ast3b attempt 1 selects both exposed roof parts (3, 4) in one shared field.
Disabling height bands avoids an abrupt cut where the lower roof meets the
upper roof; the short lip still limits snow past the eaves.
ast3b attempt 2: attempt 1 retained the crease beside the upper roof.
Separate roof fields prevent spill across levels; SKYMIN .1 admits the
open lower ridge beside the taller roof while retaining the vertical sky test.
"""
import snow_hand as H


def build(m, v):
    groups = [((3,), (0, 1, 2, 4, 5)), ((4,), (0, 1, 2, 3, 5))]
    return H.consts(m, v, fn=lambda m_, v_: H.separate(m_, v_, groups),
                    A7_SKYMIN=.1, A7_BANDH=0., A7_OVL=.3, A7_LIPDROP=.05)

