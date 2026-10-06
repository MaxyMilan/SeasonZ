"""misc_pallets2: stacked or leaning euro pallets. The top boards lie 6-10 cm apart: as separate beams each got a sausage of
its own. One deck instead: every board goes to the addonfine cap (snow_addon via hybrid), whose pillow bridges the gaps as
the snow deepens; boards seen only through the slots get none (sky test in snow_addon._drop_tips)."""
import snow_hand as H


def build(m, v):
    m._sz_rails = ([], [])
    return H.hybrid(m, v)

