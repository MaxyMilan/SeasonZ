"""wall_forfieldfen_end: rustic field fence with three uneven round rails.

Round rails 0 (middle), 2 (lower), 3 (upper): shelter-aware log crescents.
Use 5 cm stations for 0 and 2 to follow their supported broken ends more
closely. Whole-station support and shelter trimming remain active.
The upper rail needs 15 profile samples to round its post junction without
a ridge. Posts 1 and 4: small blankets over their exposed sawn tops only.
Resolve those irregular 15 cm tops on a 5 mm grid and smooth their blankets
over 4 cm; the default 1 cm grid makes folds along their uneven edges.
This is a model-local sampling choice, using the same actual source mesh.
The lower rail uses an 8 mm crown lift to bury its local wood point in v1;
its long edges and end feet retain log()'s original contact inset.
Vertical post faces and rail undersides stay bare. No crumb caps.
"""
import snow_hand as H


def build(m, v):
    if m.g > 0.005:
        m.__init__(m.name, path=m.path, g=0.005)
    out = [m.log(p, v, step=0.07 if p == 3 else 0.05,
                 k=15 if p == 3 else 11, lift=0.008 if p == 2 else 0.002)
           for p in (0, 2, 3)]
    for R, Zc in m.regions(m.tops(v, parts=[1, 4]), v, min_area=0.0012):
        out.append(m.blanket(R, Zc, v, smooth=0.04))
    return H.join(out)
