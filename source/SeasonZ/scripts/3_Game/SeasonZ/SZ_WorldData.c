//! Season climate and weather of the seasonal worlds: the climate of Kyiv (see SZ_Climate)
modded class WorldData
{
	protected bool m_SZ_Active;
	//! overcast above which lightning strikes (above 1 = no thunderstorms)
	protected float m_SZ_StormThreshold = 2.0;

	void SZ_ApplyClimate()
	{
		m_SZ_Active = SZ_Util.IsSeasonalWorld();
		if (!m_SZ_Active)
			return;

		for (int i = 0; i < 12; i++)
		{
			m_MinTemps[i] = SZ_Climate.MIN_TEMPS[i];
			m_MaxTemps[i] = SZ_Climate.MAX_TEMPS[i];
		}
		// standard atmosphere instead of the steeper game value
		m_TemperaturePerHeightReductionModifier = SZ_Climate.LAPSE;
		m_EnTempUpdated = false;
	}

	bool SZ_IsActive()
	{
		return m_SZ_Active;
	}

	//! the climate curve of the day plus the current warm spell or cold snap
	override protected float CalcBaseEnvironmentTemperature(float monthday, float daytime)
	{
		float t = super.CalcBaseEnvironmentTemperature(monthday, daytime);
		if (m_SZ_Active)
			t += SZ_State.s_TempAnomaly;
		return t;
	}

	//! recompute the base temperature right away (after the season date or the anomaly changed)
	void SZ_RefreshTemperature()
	{
		m_EnTempUpdated = false;
		UpdateBaseEnvTemperature(0);
	}

	//! temperature deciding between rain and snow (typical terrain height)
	float SZ_PrecipTemperature()
	{
		return GetBaseEnvTemperatureAtPosition(Vector(0, 150, 0));
	}

	//! lowest and highest temperature of a season day at a height, including the current anomaly
	void SZ_DailyRange(float doy, float altitude, out float tmin, out float tmax)
	{
		int month;
		int day;
		SZ_Calendar.ToMonthDay(doy, month, day);
		float monthday = month + day / 32.0;
		int a = Math.Floor(monthday) - 1;
		int b = a + 1;
		if (b >= 12)
			b = 0;
		float f = monthday - Math.Floor(monthday);
		float drop = Math.Max(0, altitude * m_TemperaturePerHeightReductionModifier);
		tmin = Math.Lerp(m_MinTemps[a], m_MinTemps[b], f) + SZ_State.s_TempAnomaly - drop;
		tmax = Math.Lerp(m_MaxTemps[a], m_MaxTemps[b], f) + SZ_State.s_TempAnomaly - drop;
	}

	//! weather odds of the season date: clear periods as often as Kyiv has sunshine, bad weather (rain or snow) as
	//! often as Kyiv has days with precipitation
	void SZ_BeforeWeatherChange(EWeatherPhenomenon type)
	{
		float doy = SZ_State.s_DayOfYear;
		int clearChance = Math.Round(100.0 * SZ_Climate.Monthly(SZ_Climate.SUNSHINE, doy));
		int badChance = Math.Round(100.0 - 100.0 * SZ_Climate.Monthly(SZ_Climate.PRECIP_SHARE, doy));
		m_WeatherDefaultSettings.m_ClearWeatherChance = clearChance;
		m_WeatherDefaultSettings.m_BadWeatherChance = badChance;
		if (type == EWeatherPhenomenon.OVERCAST)
		{
			// vanilla resets these to the defaults only after its decision; the season's odds apply right away
			m_ClearWeatherChance = clearChance;
			m_BadWeatherChance = badChance;
		}
	}

	void SZ_ChooseSnowfall(out float value, out float changeTime, out float duration)
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
	protected void SZ_UpdateStorm(float doy)
	{
		float storm = 0.5 * SZ_Climate.Monthly(SZ_Climate.THUNDER_SHARE, doy);
		float bad = SZ_Climate.Monthly(SZ_Climate.PRECIP_SHARE, doy);
		if (storm < 0.002 || bad < 0.01)
		{
			m_Weather.SetStorm(0, 1.0, 45);
			m_SZ_StormThreshold = 2.0;
			return;
		}
		// bad weather overcast spreads evenly from 0.6 to 1.0
		float threshold = 1.0 - 0.4 * Math.Min(1.0, storm / bad);
		m_Weather.SetStorm(1.0, threshold, 45);
		m_SZ_StormThreshold = threshold;
	}

	//! fog as often as in Kyiv, most in the morning and in the cold half of the year
	protected void SZ_ChooseFog(float doy)
	{
		float share = SZ_Climate.Monthly(SZ_Climate.FOG_SHARE, doy);
		float hour = g_Game.GetDayTime();
		float chance = share * 0.35;
		if (hour >= 4.0 && hour <= 10.0)
			chance = Math.Min(0.9, share * 2.0);
		float haze = SZ_HazeFloor();
		if (Math.RandomFloat01() < chance)
		{
			float fogValue = Math.RandomFloatInclusive(0.15, 0.4) + haze * 0.5;
			m_Weather.GetFog().Set(Math.Max(fogValue, haze), Math.RandomIntInclusive(300, 900), 0);
			if (SZ_State.s_DebugWeatherLog)
				Print(string.Format("[SeasonZ] fog: chance %1 at %2 h -> fog", chance, hour));
			return;
		}
		// otherwise only a light haze (in winter the haze of the snow season)
		m_Weather.GetFog().Set(Math.Max(Math.Min(m_Weather.GetFog().GetForecast(), 0.1), haze), 900, 0);
		if (SZ_State.s_DebugWeatherLog)
			Print(string.Format("[SeasonZ] fog: chance %1 at %2 h -> haze", chance, hour));
	}

	//! the haze of the snow season: while snow lies the air is rarely clear to the horizon. It grows with the snow
	//! cover (none below 1 cm at 250 m, full from 6 cm) and fades as the snow melts
	float SZ_HazeFloor()
	{
		if (!m_SZ_Active || !SZ_State.s_Valid)
			return 0;
		float cover = Math.Clamp((SZ_State.s_Snow1 - 1.0) / 5.0, 0, 1);
		return Math.Clamp(SZ_State.s_WinterHaze * SZ_Climate.WINTER_HAZE * cover, 0, 0.9);
	}

	//! server, every few seconds: the fog never stays below the winter haze (it thickens over five minutes)
	void SZ_EnforceHaze()
	{
		float haze = SZ_HazeFloor();
		if (haze <= 0)
			return;
		Fog fog = m_Weather.GetFog();
		if (fog.GetForecast() < haze - 0.01)
			fog.Set(haze, 300, 0);
	}

	bool SZ_AfterWeatherChange(EWeatherPhenomenon type, bool handled)
	{
		float doy = SZ_State.s_DayOfYear;

		m_Weather.GetSnowfall().SetLimits(0, 1);
		m_Weather.GetSnowfall().SetForecastChangeLimits(0, 1);
		m_Weather.SetSnowfallThresholds(0.45, 1.0, 60);
		SZ_UpdateStorm(doy);

		if (type == EWeatherPhenomenon.OVERCAST && SZ_State.s_DebugWeatherLog)
		{
			string chosen = "cloudy";
			if (m_ChoosenWeather == WorldDataWeatherConstants.CLEAR_WEATHER)
				chosen = "clear";
			else if (m_ChoosenWeather == WorldDataWeatherConstants.BAD_WEATHER)
				chosen = "bad";
			Print(string.Format("[SeasonZ] weather: roll %1 against clear below %2 and bad above %3 -> %4, overcast to %5, lightning above %6", m_Chance, m_WeatherDefaultSettings.m_ClearWeatherChance, m_WeatherDefaultSettings.m_BadWeatherChance, chosen, m_Weather.GetOvercast().GetForecast(), m_SZ_StormThreshold));
		}

		bool cold = SZ_PrecipTemperature() < 0.8;

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
			SZ_ChooseSnowfall(snowValue, snowTime, snowDuration);
			m_Weather.GetSnowfall().Set(snowValue, snowTime, snowDuration);
			m_Weather.GetRain().Set(0, 60, 600);
			return true;
		}

		if (type == EWeatherPhenomenon.FOG)
		{
			SZ_ChooseFog(doy);
			return true;
		}

		return handled;
	}

	//! water temperatures of the season date: rivers, ponds and wells like the Dnipro at Kyiv, the sea like the
	//! Black Sea at Odesa
	void SZ_UpdateLiquids(float doy)
	{
		if (!m_SZ_Active || !m_LiquidSettings)
			return;

		float fresh = SZ_Climate.Monthly(SZ_Climate.RIVER, doy);
		float sea = SZ_Climate.Monthly(SZ_Climate.SEA, doy);
		m_LiquidSettings.m_Temperatures.Set(LIQUID_WATER, fresh);
		m_LiquidSettings.m_Temperatures.Set(LIQUID_STILLWATER, fresh);
		m_LiquidSettings.m_Temperatures.Set(LIQUID_RIVERWATER, fresh);
		m_LiquidSettings.m_Temperatures.Set(LIQUID_FRESHWATER, fresh);
		m_LiquidSettings.m_Temperatures.Set(LIQUID_SALTWATER, sea);
	}
}
