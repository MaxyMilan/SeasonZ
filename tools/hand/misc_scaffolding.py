"""misc_scaffolding: a scaffold of tubes with board platforms.

(Opus, 6 Oct, b1) the guard rails grew sausages far wider than the tubes and the crossings fins. Tops narrower
than 12 cm (tubes, rails) get a ridge or nothing, the platforms their caps, with a short lip."""
import snow_hand as H


def build(m, v):
    return H.consts(m, v, fn=lambda m_, v_: H.big_tops(m_, v_, 0.01), A7_OVL=0.3, A7_LIPDROP=0.05, A7_THIN=0.12)
