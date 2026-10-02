modded class ChernarusPlusData
{
	override void Init()
	{
		super.Init();
		DS_ApplyClimate();
		if (m_DS_Active && (g_Game.IsServer() || !g_Game.IsMultiplayer()))
			m_Weather.GetSnowfall().SetLimits(0, 1);
	}

	override bool WeatherOnBeforeChange(EWeatherPhenomenon type, float actual, float change, float time)
	{
		if (!m_DS_Active)
			return super.WeatherOnBeforeChange(type, actual, change, time);

		DS_BeforeWeatherChange(type);
		bool handled = super.WeatherOnBeforeChange(type, actual, change, time);
		return DS_AfterWeatherChange(type, handled);
	}
}

modded class EnochData
{
	override void Init()
	{
		super.Init();
		DS_ApplyClimate();
		if (m_DS_Active && (g_Game.IsServer() || !g_Game.IsMultiplayer()))
			m_Weather.GetSnowfall().SetLimits(0, 1);
	}

	override bool WeatherOnBeforeChange(EWeatherPhenomenon type, float actual, float change, float time)
	{
		if (!m_DS_Active)
			return super.WeatherOnBeforeChange(type, actual, change, time);

		DS_BeforeWeatherChange(type);
		bool handled = super.WeatherOnBeforeChange(type, actual, change, time);
		return DS_AfterWeatherChange(type, handled);
	}
}

