"""misc_hedgehog_iron: a Czech hedgehog: three steel angle beams crossed in a star.

(Opus, 6 Oct, c37) the upper beams' pillows merged into one big ball with flaps hanging down the beams at v4-v7.
Tops narrower than 16 cm (the beams' flanges) get a ridge or nothing, the lip is short."""
import snow_hand as H


def build(m, v):
    return H.consts(m, v, A7_OVL=0.3, A7_LIPDROP=0.05, A7_THIN=0.16)

