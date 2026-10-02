//! The climate of Kyiv (1991-2020) adapted to Chernarus. The game places Chernarus at 30 E like Kyiv (Chernarus+ world
//! config); the Kyiv observatory at about 170 m stands for a typical Chernarus field. Monthly tables start in January.
class DS_Climate
{
	//! standard atmosphere: 6.5 degrees per kilometre (the game's own Chernarus value is 12 per kilometre)
	static const float LAPSE = 0.0065;
	//! height of the Kyiv weather station the tables refer to
	static const float REF_ALTITUDE = 170.0;

	//! sea level daily minimum and maximum at the start of each month (the game interpolates through the month).
	//! With the lapse rate they reproduce the Kyiv monthly means at 170 m within 0.3 degrees:
	//! min -5.5 -5.0 -0.8 5.7 10.9 14.8 16.7 15.7 10.6 5.1 0.4 -3.9, max -0.8 0.7 6.5 15.0 21.1 24.6 26.5 25.9 20.0 12.9 5.3 0.5
	static const ref array<float> MIN_TEMPS = {-4.2, -4.9, -2.7, 3.5, 9.8, 14.3, 17.4, 18.3, 14.9, 8.8, 3.7, -1.0};
	static const ref array<float> MAX_TEMPS = {0.2, 0.2, 3.7, 11.9, 19.9, 24.5, 27.1, 28.4, 24.9, 17.7, 9.9, 3.1};

	//! share of days with at least 1 mm of rain or snow (Kyiv: 8 8 9 7 9 10 9 7 7 7 8 9 days)
	static const ref array<float> PRECIP_SHARE = {0.258, 0.286, 0.290, 0.233, 0.290, 0.333, 0.290, 0.226, 0.233, 0.226, 0.267, 0.290};
	//! share of possible sunshine (Kyiv sunshine hours)
	static const ref array<float> SUNSHINE = {0.17, 0.24, 0.34, 0.44, 0.55, 0.57, 0.60, 0.60, 0.50, 0.36, 0.17, 0.12};
	//! share of days with a thunderstorm (about 25 a year, 6-7 in June and July, almost none in winter)
	static const ref array<float> THUNDER_SHARE = {0.0, 0.0, 0.006, 0.050, 0.161, 0.233, 0.210, 0.129, 0.050, 0.010, 0.003, 0.0};
	//! share of days with fog (about 39 a year, most from October to February)
	static const ref array<float> FOG_SHARE = {0.194, 0.179, 0.129, 0.067, 0.032, 0.033, 0.032, 0.032, 0.067, 0.129, 0.200, 0.194};
	//! fog value of the winter haze at full snow cover (config WinterHaze scales it): a soft haze over the distant
	//! hills that also ends the game's drawing of the snowy forests at about a kilometre and a half
	static const float WINTER_HAZE = 0.45;

	//! water (mm) per hour of precipitation at full intensity: calibrated with the weather odds above so the monthly
	//! totals match Kyiv (38 40 40 42 65 73 68 56 57 46 46 47 mm; tools/climate_sim.py)
	static const ref array<float> PRECIP_RATE = {0.309, 0.409, 0.497, 0.733, 1.263, 1.376, 1.089, 1.424, 1.214, 0.975, 0.510, 0.378};
	//! snow melt per degree-day above freezing (mm of water), higher in spring when the sun is stronger
	static const ref array<float> MELT_FACTOR = {1.875, 2.25, 3.0, 3.75, 3.75, 3.75, 3.75, 3.75, 3.75, 3.0, 2.25, 1.875};
	//! snow melted from below by the warmth of the ground (mm of water per day), most in early winter while the soil
	//! is still warm; frozen soil in late winter melts nothing
	static const ref array<float> GROUND_MELT = {0.1, 0.0, 0.0, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 1.2, 1.0, 0.5};
	//! With these rates a 20 year run of tools/climate_sim.py gives at 170 m an average monthly maximum of 9.5, 13.5,
	//! 7.0, 3.6 and 6.4 cm in January, February, March, November and December and about 78 days with snow cover
	//! (Kyiv: 9, 11, 7, 2 and 5 cm, about 80 days), and 617 mm of precipitation a year (Kyiv: 618 mm).
	//! Its average depth per month (cm) at sea level, 250 m and 500 m starts a new snow pack:
	static const ref array<float> SEED_0 = {2.6, 3.3, 0.3, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.2, 1.1};
	static const ref array<float> SEED_250 = {5.3, 8.2, 2.4, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.5, 2.3};
	static const ref array<float> SEED_500 = {9.7, 16.4, 8.7, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0, 4.4};
	//! day to day spread of the temperature (standard deviation of the daily mean, degrees)
	static const ref array<float> ANOMALY_SIGMA = {5.0, 4.5, 3.5, 3.0, 3.0, 2.5, 2.5, 2.5, 3.0, 3.0, 3.5, 4.5};
	//! how long a warm spell or cold snap lasts (days)
	static const float ANOMALY_DAYS = 3.0;

	//! water temperatures: the Dnipro at Kyiv for fresh water, the Black Sea at Odesa for salt water
	static const ref array<float> RIVER = {1.0, 1.0, 3.5, 9.5, 14.0, 19.0, 23.5, 21.5, 18.0, 10.5, 6.5, 2.0};
	static const ref array<float> SEA = {4.2, 3.3, 3.9, 8.3, 15.8, 21.2, 24.0, 24.1, 21.4, 16.6, 11.6, 7.4};

	//! Ice on ponds and lakes. Open water follows the daily mean air temperature within POND_DAYS days and cannot cool
	//! below freezing; at freezing the cold grows ice by Stefan's law (the square of the thickness grows by
	//! ICE_ALPHA squared per freezing degree-day, less under insulating snow), while positive degree-days and the
	//! spring sun melt it, slowly while snow still covers it. An 8 year run of tools/climate_sim.py (mode ice) gives at
	//! 250 m 4 cm of ice between December 5 and 25, the last ice between March 10 and 31 and a winter maximum of 19 to
	//! 27 cm, like the ponds around Kyiv.
	static const float POND_DAYS = 5.0;
	static const float ICE_ALPHA = 2.2;
	//! snow depth (cm) that halves the growth rate
	static const float ICE_SNOW_HALF = 12.0;
	//! melt per positive degree-day (cm)
	static const float ICE_MELT = 0.45;
	//! melt by the sun on thawing days (cm per day)
	static const ref array<float> ICE_SUN = {0.0, 0.1, 0.4, 1.0, 1.5, 1.5, 1.5, 1.5, 1.0, 0.3, 0.0, 0.0};
	//! share of the melt that still reaches ice under snow
	static const float ICE_SNOW_SHIELD = 0.3;
	//! average ice (cm) and pond water temperature per month of that run, to start a new pond state
	static const ref array<float> ICE_SEED_0 = {12.2, 14.0, 2.7, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 3.5};
	static const ref array<float> ICE_SEED_250 = {16.4, 20.4, 8.6, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 6.1};
	static const ref array<float> ICE_SEED_500 = {19.5, 23.0, 15.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 8.9};
	static const ref array<float> POND_TEMP_0 = {0.1, 0.1, 3.0, 10.9, 16.0, 20.8, 22.7, 21.7, 17.2, 12.0, 5.3, 1.1};
	static const ref array<float> POND_TEMP_250 = {0.0, 0.0, 1.3, 9.2, 14.4, 19.2, 21.0, 20.0, 15.6, 10.4, 3.8, 0.4};
	static const ref array<float> POND_TEMP_500 = {0.0, 0.0, 0.3, 7.4, 12.7, 17.5, 19.4, 18.4, 14.0, 8.7, 2.5, 0.1};

	static array<float> IceSeed(int level)
	{
		if (level == 0)
			return ICE_SEED_0;
		if (level == 1)
			return ICE_SEED_250;
		return ICE_SEED_500;
	}

	static array<float> PondTempSeed(int level)
	{
		if (level == 0)
			return POND_TEMP_0;
		if (level == 1)
			return POND_TEMP_250;
		return POND_TEMP_500;
	}

	//! typical snow depth table of a tracked level (0 = sea level, 1 = 250 m, 2 = 500 m)
	static array<float> SeedDepths(int level)
	{
		if (level == 0)
			return SEED_0;
		if (level == 1)
			return SEED_250;
		return SEED_500;
	}

	//! middle of each month as a day of year (0 = January 1st)
	static const ref array<float> MONTH_MIDDLE = {15.5, 45.0, 74.5, 105.0, 135.5, 166.0, 196.5, 227.5, 258.0, 288.5, 319.0, 349.5};

	//! value of a monthly table at a day of year, linear between the middles of the months.
	//! (Enforce note: a function result used in an expression can be overwritten when another part of the same
	//! expression calls that function again internally, so intermediate results go into locals.)
	static float Monthly(array<float> table, float doy)
	{
		float d = DS_Calendar.Wrap(doy);
		int a = 11;
		for (int m = 0; m < 12; m++)
		{
			if (d >= MONTH_MIDDLE[m])
				a = m;
		}
		int b = a + 1;
		float midA = MONTH_MIDDLE[a];
		float midB;
		if (a == 11)
		{
			b = 0;
			midB = MONTH_MIDDLE[0] + 365.0;
			if (d < midA)
				d += 365.0;
		}
		else
		{
			midB = MONTH_MIDDLE[b];
		}
		float f = Math.Clamp((d - midA) / (midB - midA), 0, 1);
		float va = table[a];
		float vb = table[b];
		return va + (vb - va) * f;
	}

	//! mean of max(0, T) over a day whose temperature runs as a sine between tmin and tmax
	static float PositiveMean(float tmin, float tmax)
	{
		float m = 0.5 * (tmin + tmax);
		float a = 0.5 * (tmax - tmin);
		if (a < 0.001)
			return Math.Max(0, m);
		if (m >= a)
			return m;
		if (m <= -a)
			return 0;
		float arc = Math.Acos(-m / a);
		float root = Math.Sqrt(a * a - m * m);
		return (m * arc + root) / Math.PI;
	}

	//! mean of max(0, -T) over such a day (freezing degrees)
	static float NegativeMean(float tmin, float tmax)
	{
		return PositiveMean(-tmax, -tmin);
	}

	static float Exp(float x)
	{
		return Math.Pow(2.718281828, x);
	}

	//! normally distributed random number (mean 0, deviation 1): the sum of twelve uniform numbers minus six
	//! (Math.Log2 returns 0 in the game, so the usual Box-Muller formula does not work)
	static float Gauss()
	{
		float sum = -6.0;
		for (int i = 0; i < 12; i++)
		{
			float u = Math.RandomFloat01();
			sum += u;
		}
		return sum;
	}

	//! more rain and snow on higher ground: 5 percent per 100 m above the reference height
	static float Orographic(float altitude)
	{
		return Math.Clamp(1.0 + 0.05 * (altitude - REF_ALTITUDE) / 100.0, 0.85, 1.4);
	}

	//! the most snow a level holds (cm): 40 at the coast, 55 at 250 m, 75 at 500 m
	static float DepthCap(float altitude)
	{
		if (altitude <= 250.0)
			return Math.Lerp(40.0, 55.0, Math.Clamp(altitude / 250.0, 0, 1));
		return Math.Lerp(55.0, 75.0, Math.Clamp((altitude - 250.0) / 250.0, 0, 1));
	}
}
