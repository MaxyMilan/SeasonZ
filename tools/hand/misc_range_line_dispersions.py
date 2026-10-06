"""misc_range_line_dispersions: a shooting range dispersion line: two posts, a top and a bottom rail with three target boards (Expansion mapping).

(Opus, 6 Oct, e1; Astra McClintock) as a fence the upright target boards counted as tops and grew flat vertical sheets,
the rails stopped short of the posts. As vanilla misc_range_pistol: caps on the posts and ridges on the rails, the
targets bare: fence_auto over the posts and rails only (parts 8, 10, 11, 12), the target boards and their stuck-on
decals let the snow through."""
import snow_hand as H


def build(m, v):
    return H.fence_only(m, v, (8,10,11,12))
