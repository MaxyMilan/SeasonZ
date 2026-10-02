//! Season climate and weather of the seasonal worlds: the climate of Kyiv (see DS_Climate)
modded class WorldData
{
	protected bool m_DS_Active;
	//! overcast above which lightning strikes (above 1 = no thunderstorms)
	protected float m_DS_StormThreshold = 2.0;

	void DS_ApplyClimate()
	{
		m_DS_Active = DS_Util.IsSeasonalWorld();
		if (!m_DS_Active)
			return;

		for (int i = 0; i < 12; i++)
		{
			m_MinTemps[i] = DS_Climate.MIN_TEMPS[i];
			m_MaxTemps[i] = DS_Climate.MAX_TEMPS[i];
		}
		// standard atmosphere instead of the steeper game value
		m_TemperaturePerHeightReductionModifier = DS_Climate.LAPSE;
		m_EnTempUpdated = false;
	}

	bool DS_IsActive()
	{
		return m_DS_Active;
	}

	//! the climate curve of the day plus the current warm spell or cold snap
	override protected float CalcBaseEnvironmentTemperature(float monthday, float daytime)
	{
		float t = super.CalcBaseEnvironmentTemperature(monthday, daytime);
		if (m_DS_Active)
			t += DS_State.s_TempAnomaly;
		return t;
	}

	//! recompute the base temperature right away (after the season date or the anomaly changed)
	void DS_RefreshTemperature()
	{
		m_EnTempUpdated = false;
		UpdateBaseEnvTemperature(0);
	}

	//! temperature deciding between rain and snow (typical terrain height)
	float DS_PrecipTemperature()
	{
		return GetBaseEnvTemperatureAtPosition(Vector(0, 150, 0));
	}

	//! lowest and highest temperature of a season day at a height, including the current anomaly
	void DS_DailyRange(float doy, float altitude, out float tmin, out float tmax)
	{
		int month;
		int day;
		DS_Calendar.ToMonthDay(doy, month, day);
		float monthday = month + day / 32.0;
		int a = Math.Floor(monthday) - 1;
		int b = a + 1;
		if (b >= 12)
			b = 0;
		float f = monthday - Math.Floor(monthday);
		float drop = Math.Max(0, altitude * m_TemperaturePerHeightReductionModifier);
		tmin = Math.Lerp(m_MinTemps[a], m_MinTemps[b], f) + DS_State.s_TempAnomaly - drop;
		tmax = Math.Lerp(m_MaxTemps[a], m_MaxTemps[b], f) + DS_State.s_TempAnomaly - drop;
	}

	//! weather odds of the season date: clear periods as often as Kyiv has sunshine, bad weather (rain or snow) as
	//! often as Kyiv has days with precipitation
	void DS_BeforeWeatherChange(EWeatherPhenomenon type)
	{
		float doy = DS_State.s_DayOfYear;
		int clearChance = Math.Round(100.0 * DS_Climate.Monthly(DS_Climate.SUNSHINE, doy));
		int badChance = Math.Round(100.0 - 100.0 * DS_Climate.Monthly(DS_Climate.PRECIP_SHARE, doy));
		m_WeatherDefaultSettings.m_ClearWeatherChance = clearChance;
		m_WeatherDefaultSettings.m_BadWeatherChance = badChance;
		if (type == EWeatherPhenomenon.OVERCAST)
		{
			// vanilla resets these to the defaults only after its decision; the season's odds apply right away
			m_ClearWeatherChance = clearChance;
			m_BadWeatherChance = badChance;
		}
	}

	void DS_ChooseSnowfall(out float value, out float changeTime, out float duration)
	{
		float overcast = m_Weather.GetOvercast().GetActual();
		int chance = Math.RandomIntInclusive(0, 100);
		changeTime = Math.RandomIntInclusive(60, 120);
		duration = Math.RandomIntInclusive(150, 300);
		value = 0;

		if (overcast <= 0.45)
			return;

		if (overcast > 0.92)
		{
			value = Math.RandomFloatInclusive(0.75, 1.0);
			return;
		}

		if (overcast < 0.7)
		{
			if (chance < 45)
				value = Math.RandomFloatInclusive(0.05, 0.35);
			else if (chance < 70)
				value = Math.RandomFloatInclusive(0.3, 0.55);
			return;
		}

		if (chance < 35)
			value = Math.RandomFloatInclusive(0.6, 0.95);
		else if (chance < 75)
			value = Math.RandomFloatInclusive(0.35, 0.65);
		else if (chance < 90)
			value = Math.RandomFloatInclusive(0.1, 0.35);
	}

	//! lightning: thunderstorms in the heaviest bad weather, as often as Kyiv has them (half the thunderstorm-day
	//! share, as a storm lasts a few hours); none in winter
	protected void DS_UpdateStorm(float doy)
	{
		float storm = 0.5 * DS_Climate.Monthly(DS_Climate.THUNDER_SHARE, doy);
		float bad = DS_Climate.Monthly(DS_Climate.PRECIP_SHARE, doy);
		if (storm < 0.002 || bad < 0.01)
		{
			m_Weather.SetStorm(0, 1.0, 45);
			m_DS_StormThreshold = 2.0;
			return;
		}
		// bad weather overcast spreads evenly from 0.6 to 1.0
		float threshold = 1.0 - 0.4 * Math.Min(1.0, storm / bad);
		m_Weather.SetStorm(1.0, threshold, 45);
		m_DS_StormThreshold = threshold;
	}

	//! fog as often as in Kyiv, most in the morning and in the cold half of the year
	protected void DS_ChooseFog(float doy)
	{
		float share = DS_Climate.Monthly(DS_Climate.FOG_SHARE, doy);
		float hour = g_Game.GetDayTime();
		float chance = share * 0.35;
		if (hour >= 4.0 && hour <= 10.0)
			chance = Math.Min(0.9, share * 2.0);
		float haze = DS_HazeFloor();
		if (Math.RandomFloat01() < chance)
		{
			float fogValue = Math.RandomFloatInclusive(0.15, 0.4) + haze * 0.5;
			m_Weather.GetFog().Set(Math.Max(fogValue, haze), Math.RandomIntInclusive(300, 900), 0);
			if (DS_State.s_DebugWeatherLog)
				Print(string.Format("[DynamicSeasons] fog: chance %1 at %2 h -> fog", chance, hour));
			return;
		}
		// otherwise only a light haze (in winter the haze of the snow season)
		m_Weather.GetFog().Set(Math.Max(Math.Min(m_Weather.GetFog().GetForecast(), 0.1), haze), 900, 0);
		if (DS_State.s_DebugWeatherLog)
			Print(string.Format("[DynamicSeasons] fog: chance %1 at %2 h -> haze", chance, hour));
	}

	//! the haze of the snow season: while snow lies the air is rarely clear to the horizon. It grows with the snow
	//! cover (none below 1 cm at 250 m, full from 6 cm) and fades as the snow melts
	float DS_HazeFloor()
	{
		if (!m_DS_Active || !DS_State.s_Valid)
			return 0;
		float cover = Math.Clamp((DS_State.s_Snow1 - 1.0) / 5.0, 0, 1);
		return Math.Clamp(DS_State.s_WinterHaze * DS_Climate.WINTER_HAZE * cover, 0, 0.9);
	}

	//! server, every few seconds: the fog never stays below the winter haze (it thickens over five minutes)
	void DS_EnforceHaze()
	{
		float haze = DS_HazeFloor();
		if (haze <= 0)
			return;
		Fog fog = m_Weather.GetFog();
		if (fog.GetForecast() < haze - 0.01)
			fog.Set(haze, 300, 0);
	}

	bool DS_AfterWeatherChange(EWeatherPhenomenon type, bool handled)
	{
		float doy = DS_State.s_DayOfYear;

		m_Weather.GetSnowfall().SetLimits(0, 1);
		m_Weather.GetSnowfall().SetForecastChangeLimits(0, 1);
		m_Weather.SetSnowfallThresholds(0.45, 1.0, 60);
		DS_UpdateStorm(doy);

		if (type == EWeatherPhenomenon.OVERCAST && DS_State.s_DebugWeatherLog)
		{
			string chosen = "cloudy";
			if (m_ChoosenWeather == WorldDataWeatherConstants.CLEAR_WEATHER)
				chosen = "clear";
			else if (m_ChoosenWeather == WorldDataWeatherConstants.BAD_WEATHER)
				chosen = "bad";
			Print(string.Format("[DynamicSeasons] weather: roll %1 against clear below %2 and bad above %3 -> %4, overcast to %5, lightning above %6", m_Chance, m_WeatherDefaultSettings.m_ClearWeatherChance, m_WeatherDefaultSettings.m_BadWeatherChance, chosen, m_Weather.GetOvercast().GetForecast(), m_DS_StormThreshold));
		}

		bool cold = DS_PrecipTemperature() < 0.8;

		if (type == EWeatherPhenomenon.RAIN)
		{
			if (cold)
			{
				float amount = m_Weather.GetRain().GetForecast();
				m_Weather.GetRain().Set(0, 60, 600);
				if (m_Weather.GetOvercast().GetActual() > 0.45)
					m_Weather.GetSnowfall().Set(Math.Clamp(amount * 1.15, 0, 1), Math.RandomIntInclusive(60, 120), Math.RandomIntInclusive(150, 300));
				return true;
			}

			if (m_Weather.GetSnowfall().GetForecast() > 0)
				m_Weather.GetSnowfall().Set(0, 60, 600);
			return handled;
		}

		if (type == EWeatherPhenomenon.SNOWFALL)
		{
			if (!cold)
			{
				m_Weather.GetSnowfall().Set(0, 60, 600);
				return true;
			}

			float snowValue;
			float snowTime;
			float snowDuration;
			DS_ChooseSnowfall(snowValue, snowTime, snowDuration);
			m_Weather.GetSnowfall().Set(snowValue, snowTime, snowDuration);
			m_Weather.GetRain().Set(0, 60, 600);
			return true;
		}

		if (type == EWeatherPhenomenon.FOG)
		{
			DS_ChooseFog(doy);
			return true;
		}

		return handled;
	}

	//! water temperatures of the season date: rivers, ponds and wells like the Dnipro at Kyiv, the sea like the
	//! Black Sea at Odesa
	void DS_UpdateLiquids(float doy)
	{
		if (!m_DS_Active || !m_LiquidSettings)
			return;

		float fresh = DS_Climate.Monthly(DS_Climate.RIVER, doy);
		float sea = DS_Climate.Monthly(DS_Climate.SEA, doy);
		m_LiquidSettings.m_Temperatures.Set(LIQUID_WATER, fresh);
		m_LiquidSettings.m_Temperatures.Set(LIQUID_STILLWATER, fresh);
		m_LiquidSettings.m_Temperatures.Set(LIQUID_RIVERWATER, fresh);
		m_LiquidSettings.m_Temperatures.Set(LIQUID_FRESHWATER, fresh);
		m_LiquidSettings.m_Temperatures.Set(LIQUID_SALTWATER, sea);
	}
}
