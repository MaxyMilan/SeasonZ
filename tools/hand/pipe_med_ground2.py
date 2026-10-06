"""pipe_med_ground2: a run of small or medium pipe (bends, flanges) on supports, in the pipe family.

(Opus, 6 Oct) c37/c45: at v7 a thick tongue hung from the pipe's end down onto the support under it, also with
a short lip: the pipe's snow and the support top's merged in one field. The pipe run (parts reaching within 25 cm
of the top) and the lower parts (supports, clamps, bases) are separate fields that do not spill onto each other,
with a short lip (10% of the depth + 1 cm, sinking 1 cm at most); tops narrower than 16 cm (the thin crossing pipes and braces
above the main run, which grew fat rolls in c47) a ridge or nothing."""
import snow_hand as H


def _groups(m):
    """the pipe run (parts reaching within 25 cm of the model's top) and the lower parts (supports, clamps, bases)"""
    if not hasattr(m, '_sz_pipe_groups'):
        top = float(m.V[:, 1].max())
        hi = {}
        for p in range(int(m.part_t.max()) + 1):
            sel = m.part_t == p
            if sel.any():
                hi[p] = float(m.V[m.T[sel]][..., 1].max())
        upper = tuple(p for p, h in hi.items() if h >= top - 0.25)
        lower = tuple(p for p in hi if p not in upper)
        m._sz_pipe_groups = [(upper, lower), (lower, upper)] if lower else [(upper, ())]
    return m._sz_pipe_groups


def build(m, v):
    g = _groups(m)
    return H.consts(m, v, fn=lambda m_, v_: H.separate(m_, v_, g), A7_OVL=0.1, A7_LIPDROP=0.03, A7_THIN=0.16)
