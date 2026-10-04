modded class ChernarusPlusData
{
	override void Init()
	{
		super.Init();
		SZ_ApplyClimate();
		if (m_SZ_Active && (g_Game.IsServer() || !g_Game.IsMultiplayer()))
			m_Weather.GetSnowfall().SetLimits(0, 1);
	}

	override bool WeatherOnBeforeChange(EWeatherPhenomenon type, float actual, float change, float time)
	{
		if (!m_SZ_Active)
			return super.WeatherOnBeforeChange(type, actual, change, time);

		SZ_BeforeWeatherChange(type);
		bool handled = super.WeatherOnBeforeChange(type, actual, change, time);
		return SZ_AfterWeatherChange(type, handled);
	}
}

modded class EnochData
{
	override void Init()
	{
		super.Init();
		SZ_ApplyClimate();
		if (m_SZ_Active && (g_Game.IsServer() || !g_Game.IsMultiplayer()))
			m_Weather.GetSnowfall().SetLimits(0, 1);
	}

	override bool WeatherOnBeforeChange(EWeatherPhenomenon type, float actual, float change, float time)
	{
		if (!m_SZ_Active)
			return super.WeatherOnBeforeChange(type, actual, change, time);

		SZ_BeforeWeatherChange(type);
		bool handled = super.WeatherOnBeforeChange(type, actual, change, time);
		return SZ_AfterWeatherChange(type, handled);
	}
}

