"""misc_polytunnel: a plastic-sheet tunnel greenhouse on hoops; the sheet hangs in folds down its sides.

(Opus, 6 Oct) the folds' up-facing facets on the sides (within the smooth models' 60 degrees) caught loose white lumps
at every depth (m1). Snow slides off taut plastic: only the arch's crown (up to 45 degrees, full depth to 25) holds it."""
import snow_hand as H


def build(m, v):
    return H.consts(m, v, A5_STEEP_SMOOTH=45., A5_FULL_SMOOTH=25.)
