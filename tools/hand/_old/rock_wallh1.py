"""rock_wallh1: a long, very large connected rock wall. Use only exposed
upward source facets and a fixed 11500-triangle sampling target. The vertical
wall and buried base are excluded; discontinuous shelves keep open boundaries.
The actual imported visual LOD and all remaining flaws are recorded in QA."""
import snow_rock as R


def build(m,v):
    return R.drape(m,v,budget=11500)
