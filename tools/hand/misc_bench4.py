"""misc_bench4: a park bench of curved slats (seat 10, 16-19; the curve 15, 14; back 13-11, 11 the top) on two cast
iron frames (0-9).

addonfine pillows (snow_addon via hybrid) on the seat (10, 16-19) and the top back board (11). The curve into the back
and the lower back boards (12-15) are blocked: no cap of their own and no spill from the seat's kernel, so the seat's
pillow never bridges into the backrest (no marshmallow). The frames hold none."""
import snow_hand as H


def build(m, v):
    m._sz_parts = (10, 11, 16, 17, 18, 19)
    m._sz_block = (12, 13, 14, 15)
    return H.hybrid(m, v)
