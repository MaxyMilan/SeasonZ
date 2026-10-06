"""rock_apart2: four disconnected rocks, parts 0..3, including the narrow
part 2. A common source-surface drape gives each its own embedded boundary;
sky tests prevent snow on hidden faces where their silhouettes overlap."""
import snow_rock as R


def build(m,v):
    return R.drape(m,v,budget=11000,parts=[0,1,2,3])
