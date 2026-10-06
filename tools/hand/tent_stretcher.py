"""tent_stretcher: a canvas stretcher on the ground, 17 cm high (Expansion mapping).

(Opus, 6 Oct, e1; Astra Boyle flagged it bare) snow_addon leaves every surface under 25 cm over the ground to the
ground snow, but the ground snow only buries a prop this low once it is deeper than the prop (v5-v7): until then
its top stood bare beside a white ground. The ground lowered, so its top holds its own cushion from v1."""
import snow_hand as H


def build(m, v):
    m.ground = float(m.V[:, 1].min()) - 0.25
    return H.big_tops(m, v, 0.01)
