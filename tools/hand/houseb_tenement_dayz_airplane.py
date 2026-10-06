"""houseb_tenement_dayz_airplane: a crashed small aircraft broken into fuselage, wings and tail (Expansion mapping).

(Opus, 6 Oct, e2; Astra Feynman) a tall pointed sheet climbed the near-vertical tail fin and the caps beside it hung
triangular folds. The wreck route (parts with 1 dm2 of top, a short lip, ledges bare, thinning on curved panels) with
snow holding to 40 degrees (full depth to 22), so the fin stays bare."""
import snow_hand as H


def build(m, v):
    return H.wreck(m, v, A5_STEEP_SMOOTH=40.0, A5_FULL_SMOOTH=22.0)
