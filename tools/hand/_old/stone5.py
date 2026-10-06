"""stone5: one small, low boulder. A continuous drape follows the rounded crown,
fills small surface hollows as depth grows and disappears into the steep flanks.
The ground contact and all free boundaries taper inside the stone."""
import snow_rock as R


def build(m,v):
    return R.drape(m,v,budget=3400,angle7=58)
