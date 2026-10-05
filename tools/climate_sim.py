"""Offline model of the Kyiv climate in DayZ: weather process (vanilla Chernarus logic with the monthly Kyiv odds), the
game's temperature curve, a synoptic temperature anomaly and the snow pack. Used to calibrate and check the mod's
constants against Kyiv observations before they go into SZ_Climate / SZ_ServerController."""
import math
import random
import sys

import numpy as np

DAYS = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
START = np.cumsum([0] + DAYS[:-1])
# sea level tables at the start of each month (fitted to Kyiv 1991-2020 at 170 m, lapse 6.5 K/km)
TMIN = [-4.2, -4.9, -2.7, 3.5, 9.8, 14.3, 17.4, 18.3, 14.9, 8.8, 3.7, -1.0]
TMAX = [0.2, 0.2, 3.7, 11.9, 19.9, 24.5, 27.1, 28.4, 24.9, 17.7, 9.9, 3.1]
LAPSE = 0.0065
PRECIP_MM = [38, 40, 40, 42, 65, 73, 68, 56, 57, 46, 46, 47]
PRECIP_DAYS = [8, 8, 9, 7, 9, 10, 9, 7, 7, 7, 8, 9]
SUN = [0.17, 0.24, 0.34, 0.44, 0.55, 0.57, 0.60, 0.60, 0.50, 0.36, 0.17, 0.12]
ANOM_SIGMA = [5.0, 4.5, 3.5, 3.0, 3.0, 2.5, 2.5, 2.5, 3.0, 3.0, 3.5, 4.5]
ANOM_TAU_DAYS = 3.0
SUNRISE_JAN, SUNSET_JAN, SUNRISE_JUL, SUNSET_JUL = 8.54, 15.52, 3.26, 20.73


def month_day(doy):
    d = int(doy) % 365
    m = 0
    while m < 11 and d >= START[m + 1]:
        m += 1
    return m + 1, d - START[m] + 1


def monthly(table, doy):
    """value of a monthly table at a day of year, linear between the middles of the months"""
    mids = [START[m] + DAYS[m] / 2.0 for m in range(12)]
    d = doy % 365
    for m in range(12):
        a = mids[m]
        b = mids[(m + 1) % 12] + (365 if m == 11 else 0)
        dd = d if d >= mids[0] or m != 11 else d + 365
        if m == 11 and d < mids[0]:
            dd = d + 365
        else:
            dd = d
        if a <= dd < b:
            f = (dd - a) / (b - a)
            return table[m] + (table[(m + 1) % 12] - table[m]) * f
    return table[0]


def sunrise(monthday):
    if monthday <= 8.0:
        return ((SUNRISE_JAN - SUNRISE_JUL) / 7.0) * (1 - monthday) + SUNRISE_JAN
    return ((monthday - 8) * (SUNRISE_JAN - SUNRISE_JUL)) / 5.0 + SUNRISE_JUL


def sunset(monthday):
    if monthday <= 8.0:
        return ((SUNSET_JAN - SUNSET_JUL) / 7.0) * (1 - monthday) + SUNSET_JAN
    return ((monthday - 8) * (SUNSET_JAN - SUNSET_JUL)) / 5.0 + SUNSET_JUL


def lerp(a, b, t):
    return a + (b - a) * t


def game_temp(doy, hour):
    """vanilla CalcBaseEnvironmentTemperature with the mod's tables (sea level)"""
    month, day = month_day(doy)
    monthday = month + day / 32.0
    sr, ss = sunrise(monthday), sunset(monthday)
    light = ss - sr
    night = 24.0 - light
    i = int(math.floor(monthday)) - 1
    j = (i + 1) % 12
    f = monthday - math.floor(monthday)
    mn = lerp(TMIN[i], TMIN[j], f)
    mx = lerp(TMAX[i], TMAX[j], f)
    ev = mn + 0.5 * abs(mn - mx)
    if sr <= hour <= ss:
        if hour <= sr + light * 0.75:
            return lerp(mn, mx, (hour - sr) / (light * 0.75))
        return lerp(mx, ev, ((hour - sr) - light * 0.75) / (light * 0.25))
    if ss < hour < 24:
        return lerp(ev, mn, ((hour - ss) / (24 - ss)) / 2.0)
    return lerp(ev, mn, ((hour + (24 - ss)) / night) / 2.0 + 0.5)


def daily_range(doy):
    month, day = month_day(doy)
    monthday = month + day / 32.0
    i = int(math.floor(monthday)) - 1
    j = (i + 1) % 12
    f = monthday - math.floor(monthday)
    return lerp(TMIN[i], TMIN[j], f), lerp(TMAX[i], TMAX[j], f)


def positive_mean(tmin, tmax):
    """mean of max(0, T) over a day with a sinusoidal course between tmin and tmax"""
    m = 0.5 * (tmin + tmax)
    a = 0.5 * (tmax - tmin)
    if a < 1e-6:
        return max(0.0, m)
    if m >= a:
        return m
    if m <= -a:
        return 0.0
    return (m * math.acos(-m / a) + math.sqrt(a * a - m * m)) / math.pi


def negative_mean(tmin, tmax):
    """mean of max(0, -T) over a day with a sinusoidal course between tmin and tmax (freezing degrees)"""
    return positive_mean(-tmax, -tmin)


# ice on ponds and lakes (see SZ_Climate): the open water follows the daily mean air temperature within POND_TAU
# days and cannot cool below freezing; at freezing the cold grows ice by Stefan's law, h^2 grows by alpha^2 per
# freezing degree-day (alpha lower under snow), and positive degree-days and the spring sun melt it.
ICE = dict(tau=5.0, alpha=2.2, snow_half=12.0, melt=0.45,
           sun=[0.0, 0.1, 0.4, 1.0, 1.5, 1.5, 1.5, 1.5, 1.0, 0.3, 0.0, 0.0], snow_shield=0.3)


class Pond:
    def __init__(self):
        self.temp = 12.0
        self.ice = 0.0

    def step(self, sd, lo, hi, snow_cm, doy, p=ICE):
        mean = 0.5 * (lo + hi)
        if self.ice <= 0.0:
            self.temp += (mean - self.temp) * min(1.0, sd / p['tau'])
            if self.temp >= 0.0:
                return
            # the surface reached freezing: the cold beyond it starts the ice
            fdd = -self.temp * p['tau']
            self.temp = 0.0
        else:
            fdd = negative_mean(lo, hi) * sd
        a = p['alpha'] / (1.0 + snow_cm / p['snow_half'])
        self.ice = math.sqrt(self.ice * self.ice + a * a * fdd)
        pdd_day = positive_mean(lo, hi)
        melt = (p['melt'] * pdd_day + monthly(p['sun'], doy) * min(1.0, pdd_day)) * sd
        if snow_cm >= 1.0:
            melt *= p['snow_shield']
        self.ice -= melt
        if self.ice < 0.2:
            self.ice = 0.0
            self.temp = max(self.temp, 0.0)


class Weather:
    """vanilla Chernarus weather decisions with the mod's monthly odds (real seconds)"""

    def __init__(self, rng):
        self.rng = rng
        self.overcast = 0.4
        self.oc_from = 0.4
        self.oc_to = 0.4
        self.oc_t = 0.0
        self.oc_time = 1.0
        self.oc_next = 0.0
        self.last = 0
        self.same = 0
        self.rain = 0.0
        self.rain_next = 0.0
        self.snow = 0.0
        self.snow_next = 0.0

    def odds(self, doy):
        clear = int(round(100 * monthly(SUN, doy)))
        bad = int(round(100 - 100 * monthly([PRECIP_DAYS[m] / DAYS[m] for m in range(12)], doy)))
        return clear, bad

    def step(self, t, dt, doy, t150):
        r = self.rng
        if t >= self.oc_next:
            clear0, bad0 = self.odds(doy)
            clear, bad = clear0, bad0
            chance = r.randint(0, 100)
            if self.last == 1:
                clear -= 5 * self.same
            if self.last == 2:
                clear += 5 * self.same
            if self.last == 3:
                clear += 5
                bad += 5 * self.same + 5
            if chance < clear:
                w = 1
            elif chance > bad:
                w = 3
            else:
                w = 2
            if w == self.last:
                self.same += 1
            else:
                self.same = 0
            self.last = w
            val = {1: r.uniform(0, 0.3), 2: r.uniform(0.3, 0.6), 3: r.uniform(0.6, 1.0)}[w]
            ptime = r.randint(600, 900)
            plen = r.randint(600, 900)
            self.oc_from, self.oc_to, self.oc_t, self.oc_time = self.overcast, val, 0.0, ptime
            self.oc_next = t + ptime + plen
        self.oc_t += dt
        self.overcast = lerp(self.oc_from, self.oc_to, min(1.0, self.oc_t / self.oc_time))
        oc = self.overcast
        cold = t150 < 0.8
        if t >= self.rain_next:
            chance = r.randint(0, 100)
            val = 0.0
            nxt = r.randint(60, 120)
            if oc <= 0.6:
                val = 0.0
            elif oc > 0.9:
                val = r.uniform(0.8, 1.0)
            elif oc < 0.75:
                val = r.uniform(0.1, 0.3) if chance < 30 else r.uniform(0.2, 0.5) if chance < 60 else r.uniform(0.0, 0.2) if chance < 80 else 0.0
                if chance >= 80:
                    nxt += 120
            else:
                val = r.uniform(0.5, 0.7) if chance < 25 else r.uniform(0.2, 0.4) if chance < 50 else r.uniform(0.4, 0.6) if chance < 75 else 0.0
                if chance >= 75:
                    nxt += 120
            if cold:
                if oc > 0.45 and val > 0:
                    self.snow = min(1.0, val * 1.15)
                    self.snow_next = t + r.randint(60, 120) + r.randint(150, 300)
                val = 0.0
            self.rain = val
            self.rain_next = t + nxt
        if t >= self.snow_next:
            if not cold:
                self.snow = 0.0
                self.snow_next = t + 660
            else:
                chance = r.randint(0, 100)
                val = 0.0
                if oc > 0.92:
                    val = r.uniform(0.75, 1.0)
                elif oc > 0.45:
                    if oc < 0.7:
                        val = r.uniform(0.05, 0.35) if chance < 45 else r.uniform(0.3, 0.55) if chance < 70 else 0.0
                    else:
                        val = r.uniform(0.6, 0.95) if chance < 35 else r.uniform(0.35, 0.65) if chance < 75 else r.uniform(0.1, 0.35) if chance < 90 else 0.0
                self.snow = val
                self.snow_next = t + r.randint(60, 120) + r.randint(150, 300)
        # conversions as UpdatePrecipitationType
        if self.snow > 0.02 and t150 > 1.5:
            self.rain = max(self.rain, self.snow)
            self.snow = 0.0
        elif self.rain > 0.02 and t150 < 0.3:
            self.snow = min(1.0, self.rain * 1.15)
            self.rain = 0.0
        rain = self.rain if oc >= 0.6 else 0.0
        snow = self.snow if oc >= 0.45 else 0.0
        return oc, rain, snow


class Pack:
    def __init__(self, cap):
        self.swe = 0.0
        self.depth = 0.0
        self.cap = cap
        self.wet = 0.0

    def density(self):
        return self.swe / (10.0 * self.depth) if self.depth > 0.01 else 0.1


def simulate(params, years=6, speed=12.0, accel=4.0, night_accel=2.0, seed=1, start_doy=243.0, log=False):
    rng = random.Random(seed)
    w = Weather(rng)
    levels = [0.0, 250.0, 500.0]
    caps = params['caps']
    packs = [Pack(c) for c in caps]
    ponds = [Pond() for _ in levels]
    K = params['K']
    oro = params['oro']
    t = 0.0
    dt = 10.0
    doy = start_doy
    hour = 12.0
    anom = 0.0
    total_days = 365.0 * years
    stats = {lv: {m: [] for m in range(12)} for lv in range(3)}
    ice_stats = {lv: {m: [] for m in range(12)} for lv in range(3)}
    temp_stats = {lv: {m: [] for m in range(12)} for lv in range(3)}
    ice_series = []
    precip = [0.0] * 12
    months_seen = [0.0] * 12
    snow_hours = [0.0] * 12
    intensity_hours = [0.0] * 12
    day_acc = 0.0
    while (doy - start_doy) < total_days:
        sd = dt * speed / 86400.0  # season days in this step
        doy += sd
        # game clock (in-game hours), night runs faster
        mo, dd = month_day(doy)
        sr, ss = sunrise(mo + dd / 32.0), sunset(mo + dd / 32.0)
        rate = accel * (night_accel if (hour < sr or hour > ss) else 1.0)
        hour = (hour + dt * rate / 3600.0) % 24.0
        # synoptic anomaly (season time)
        sig = monthly(ANOM_SIGMA, doy)
        a = math.exp(-sd / ANOM_TAU_DAYS)
        anom = anom * a + sig * math.sqrt(max(0.0, 1 - a * a)) * rng.gauss(0, 1)
        t0 = game_temp(doy, hour) + anom
        t150 = t0 - 150 * LAPSE
        oc, rain, snow = w.step(t, dt, doy, t150)
        m = mo - 1
        hours = sd * 24.0
        months_seen[m] += sd
        intensity_hours[m] += (rain + snow) * hours
        if snow > 0.0:
            snow_hours[m] += hours
        kk = K[m]
        precip[m] += (rain + snow) * kk * hours
        tmin, tmax = daily_range(doy)
        for li, alt in enumerate(levels):
            p = packs[li]
            tl_now = t0 - alt * LAPSE
            water = (rain + snow) * kk * hours * (1 + oro * (alt - 170.0) / 100.0)
            falls_as_snow = (snow > 0 and tl_now <= 1.5) or (rain > 0 and tl_now <= 0.0)
            if water > 0 and falls_as_snow:
                p.swe += water
                p.depth += water * params['fresh_cm_per_mm']
            elif water > 0 and p.swe > 0:
                p.wet = 1.0
            # melt with the daily course shifted by the anomaly
            lo = tmin + anom - alt * LAPSE
            hi = tmax + anom - alt * LAPSE
            pdd = positive_mean(lo, hi)
            ddf = monthly(params['ddf'], doy)
            ddf *= params.get('ddf_scale', 1.0)
            if p.swe > 0:
                melt = ddf * pdd * sd + (rain * kk * hours * max(0.0, tl_now) / 80.0)
                # heat from the ground melts the snow from below, most in early winter while the soil is warm
                melt += monthly(params['ground'], doy) * params.get('ground_scale', 1.0) * sd
                if melt > 0:
                    rho = p.density()
                    p.swe = max(0.0, p.swe - melt)
                    p.depth = p.swe / (10.0 * rho) if p.swe > 0 else 0.0
                    # thaw makes the pack wet; melt from below by the ground does not
                    if pdd > 0.2:
                        p.wet = 1.0
                # settling
                rho = p.density()
                if pdd > 0.2 or p.wet > 0:
                    target, tau = params['rho_wet'], params['tau_wet']
                else:
                    target, tau = params['rho_dry'], params['tau_dry']
                rho = rho + (target - rho) * min(1.0, sd / tau)
                p.depth = p.swe / (10.0 * rho)
                p.wet = max(0.0, p.wet - sd)
                if p.depth > p.cap:
                    p.depth = p.cap
                    p.swe = min(p.swe, p.cap * 10.0 * rho)
            else:
                p.depth = 0.0
                p.swe = 0.0
            ponds[li].step(sd, lo, hi, p.depth, doy)
        day_acc += sd
        if day_acc >= 0.25:
            day_acc = 0.0
            for li in range(3):
                stats[li][m].append(packs[li].depth)
                ice_stats[li][m].append(ponds[li].ice)
                temp_stats[li][m].append(ponds[li].temp)
            ice_series.append((doy, [ponds[li].ice for li in range(3)], [packs[li].depth for li in range(3)]))
        t += dt
    params['_ice'] = (ice_stats, temp_stats, ice_series)
    return stats, precip, months_seen, snow_hours, intensity_hours


def summarize(stats, precip, months_seen, snow_hours, intensity_hours, label=''):
    years = [ms / DAYS[m] for m, ms in enumerate(months_seen)]
    print(label)
    print('month  precip(mm/month)  snowHours/day  E[intensity]  depth0 mean/max  depth170 mean/max  depth250 mean  depth500 mean  cover170(%)')
    for m in range(12):
        n = years[m] if years[m] > 0 else 1
        d0 = np.array(stats[0][m]) if stats[0][m] else np.zeros(1)
        d2 = np.array(stats[1][m]) if stats[1][m] else np.zeros(1)
        d5 = np.array(stats[2][m]) if stats[2][m] else np.zeros(1)
        d170 = d0 + (d2 - d0) * 0.68
        # monthly maximum averaged over the years
        k = max(1, int(round(len(d170) / n)))
        maxes = [d170[i:i + k].max() for i in range(0, len(d170), k)] if len(d170) else [0]
        maxes0 = [d0[i:i + k].max() for i in range(0, len(d0), k)] if len(d0) else [0]
        hours = months_seen[m] * 24.0
        print('%3d  %8.1f  %8.2f  %8.3f  %6.1f/%6.1f  %6.1f/%6.1f  %6.1f  %6.1f  %5.0f' % (
            m + 1, precip[m] / n, snow_hours[m] / max(1e-6, months_seen[m]), intensity_hours[m] / max(1e-6, hours),
            d0.mean(), np.mean(maxes0), d170.mean(), np.mean(maxes), d2.mean(), d5.mean(), 100.0 * (d170 >= 1.0).mean()))


if __name__ == '__main__':
    params = dict(
        K=[1.0] * 12, oro=0.05, caps=[40.0, 55.0, 75.0], fresh_cm_per_mm=1.0,
        ddf=[2.5, 3.0, 4.0, 5.0, 5.0, 5.0, 5.0, 5.0, 5.0, 4.0, 3.0, 2.5],
        ground=[0.1, 0.0, 0.0, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 1.2, 1.0, 0.5],
        rho_dry=0.30, tau_dry=6.0, rho_wet=0.42, tau_wet=2.0)
    mode = sys.argv[1] if len(sys.argv) > 1 else 'calib'
    if mode == 'calib':
        stats, precip, ms, sh, ih = simulate(params, years=int(sys.argv[2]) if len(sys.argv) > 2 else 4)
        E = []
        for m in range(12):
            hours = ms[m] * 24.0
            E.append(ih[m] / hours)
        print('E per month', [round(e, 4) for e in E])
        print('K per month', [round(PRECIP_MM[m] / (DAYS[m] * 24.0 * E[m]), 3) for m in range(12)])
    elif mode == 'run':
        params['K'] = [0.309, 0.409, 0.497, 0.733, 1.263, 1.376, 1.089, 1.424, 1.214, 0.975, 0.51, 0.378]
        params['ddf'] = [1.875, 2.25, 3.0, 3.75, 3.75, 3.75, 3.75, 3.75, 3.75, 3.0, 2.25, 1.875]
        for kv in sys.argv[3:]:
            k, v = kv.split('=')
            params[k] = float(v)
        stats, precip, ms, sh, ih = simulate(params, years=int(sys.argv[2]), seed=7)
        summarize(stats, precip, ms, sh, ih, 'run %s' % sys.argv[3:])
    elif mode == 'ice':
        params['K'] = [0.309, 0.409, 0.497, 0.733, 1.263, 1.376, 1.089, 1.424, 1.214, 0.975, 0.51, 0.378]
        params['ddf'] = [1.875, 2.25, 3.0, 3.75, 3.75, 3.75, 3.75, 3.75, 3.75, 3.0, 2.25, 1.875]
        for kv in sys.argv[3:]:
            k, v = kv.split('=')
            ICE[k] = float(v)
        years = int(sys.argv[2])
        stats, precip, ms, sh, ih = simulate(params, years=years, seed=7)
        ice_stats, temp_stats, series = params['_ice']
        print('ice model', {k: v for k, v in ICE.items() if k != 'sun'})
        print('month   ice cm mean (0/250/500)    ice cm max-of-month mean (250)   pond temp mean (0/250/500)')
        for m in range(12):
            n = max(1, len(ice_stats[1][m]))
            k = max(1, int(round(n / years)))
            mx = [max(ice_stats[1][m][i:i + k]) for i in range(0, n, k)] if ice_stats[1][m] else [0]
            print('%3d   %5.1f %5.1f %5.1f   %5.1f   %5.1f %5.1f %5.1f' % (
                m + 1, np.mean(ice_stats[0][m] or [0]), np.mean(ice_stats[1][m] or [0]), np.mean(ice_stats[2][m] or [0]),
                np.mean(mx), np.mean(temp_stats[0][m] or [0]), np.mean(temp_stats[1][m] or [0]), np.mean(temp_stats[2][m] or [0])))
        # freeze-up (first day of the winter with 4 cm at 250 m) and break-up (last day with ice in spring)
        winters = {}
        for doy, ice, snow in series:
            year = int((doy - 182.0) // 365.0)
            d = doy % 365.0
            w = winters.setdefault(year, {'first4': None, 'last': None, 'max': 0.0, 'days': 0})
            if ice[1] >= 4.0 and w['first4'] is None:
                w['first4'] = d
            if ice[1] > 0.0:
                w['last'] = d
                w['days'] += 0.25
            w['max'] = max(w['max'], ice[1])
        for y, w in sorted(winters.items()):
            print('winter %d: 4 cm on day %s, last ice day %s, max %.1f cm, ice days %.0f' % (
                y, None if w['first4'] is None else round(w['first4']), None if w['last'] is None else round(w['last']), w['max'], w['days']))

