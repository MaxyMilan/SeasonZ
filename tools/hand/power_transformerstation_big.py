"""power_transformerstation_big: an open-air substation, gantries of timber posts and cross beams over rows of
transformers, switches and insulator stacks.

(Opus, 6 Oct, m1, c39) dozens of white beads sat on the insulator caps and small fittings at every depth. Tops
narrower than 16 cm (insulators, switch arms, brackets) get no volumetric snow (a straight strip a ridge, a disc
nothing); the gantry beams, transformer tops and cabinets keep their caps.
(c43) with 16 cm the insulator caps (discs about 20 cm across) still carried white knobs: 25 cm.
(c50) at 25 cm the insulator caps still carried knobs: only parts with at least 8 dm2 of top hold snow (gantry
beams, transformers, cabinets), thin strips 16 cm."""
import snow_hand as H


def build(m, v):
    return H.consts(m, v, fn=lambda m_, v_: H.big_tops(m_, v_, 0.08), A7_THIN=0.16)
