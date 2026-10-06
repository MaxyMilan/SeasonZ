"""wall_barricade1_4: a junk barricade of pipes, planks, a shelf and chairs (Expansion mapping).

(Opus, 6 Oct, e1; Astra Boyle) as a fence (kind 1, its walls folder) every pipe got a log crescent that wrapped it
white and the shelf under a leaning panel a cushion, with teeth under the lips; (e1b, McClintock) as kind 0 with the
volumetric cap: pointed hanging folds and steep sheets with teeth on the leaning panels and chairs. Treated as the
rubbish heaps are (garbage_pile*, the slum ruins): rough, a short lip, crevices filled; small or narrow tops just
below a bigger one bare."""
import snow_hand as H


def build(m, v):
    m.kind = 0
    m.rough = True
    m.skind = 'rough'
    m.scls = 'any'
    H.ledges(m, 0.08, 0.4)
    return H.consts(m, v, A7_OVL=0.3, A7_LIPDROP=0.05, A7_CREVICE=0.15)
