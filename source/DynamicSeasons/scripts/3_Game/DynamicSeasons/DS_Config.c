//! Server configuration, $profile:DynamicSeasons/config.json
class DS_Config
{
	//! settings added since the first version: a config.json from before them reads them as 0, so they are set to
	//! their defaults once (2 = WinterHaze)
	int ConfigVersion = 2;
	//! "RealTime" follows the real calendar date of the server machine, "Multiplier" runs its own season clock
	string Mode = "RealTime";
	//! Multiplier mode: 1 = one season year per real year, 12 = per real month, 52 = per real week, 365 = per real day
	float SeasonSpeedMultiplier = 12.0;
	//! Multiplier mode: relative length of each season
	float SpringLengthMultiplier = 1.0;
	float SummerLengthMultiplier = 1.0;
	float AutumnLengthMultiplier = 1.0;
	float WinterLengthMultiplier = 1.0;
	//! Multiplier mode: day of year (1-365) the season clock starts at on the first run
	int StartDayOfYear = 335;
	//! how fast snow builds up during snowfall and how fast it melts above freezing
	float SnowBuildupMultiplier = 1.0;
	float SnowMeltMultiplier = 1.0;
	//! winter haze while snow lies: 1 = the default, 0 = off, up to 2 = thicker. The haze also limits how far the
	//! game draws the snowy world, which keeps the frame rate up
	float WinterHaze = 1.0;

	bool IsRealTime()
	{
		string mode = Mode;
		mode.ToLower();
		return mode != "multiplier";
	}

	void Validate()
	{
		if (ConfigVersion < 2)
		{
			WinterHaze = 1.0;
			ConfigVersion = 2;
		}
		SeasonSpeedMultiplier = Math.Clamp(SeasonSpeedMultiplier, 0.0, 100000.0);
		SpringLengthMultiplier = Math.Clamp(SpringLengthMultiplier, 0.05, 20.0);
		SummerLengthMultiplier = Math.Clamp(SummerLengthMultiplier, 0.05, 20.0);
		AutumnLengthMultiplier = Math.Clamp(AutumnLengthMultiplier, 0.05, 20.0);
		WinterLengthMultiplier = Math.Clamp(WinterLengthMultiplier, 0.05, 20.0);
		if (StartDayOfYear < 1)
			StartDayOfYear = 1;
		if (StartDayOfYear > 365)
			StartDayOfYear = 365;
		SnowBuildupMultiplier = Math.Clamp(SnowBuildupMultiplier, 0.0, 100.0);
		SnowMeltMultiplier = Math.Clamp(SnowMeltMultiplier, 0.0, 100.0);
		WinterHaze = Math.Clamp(WinterHaze, 0.0, 2.0);
	}
}

//! Persistent runtime state, $profile:DynamicSeasons/state.json
class DS_PersistentState
{
	int Version = 1;
	bool Initialized = false;
	float CycleDays = 0;
	float SnowSeaLevelCm = 0;
	float Snow250mCm = 0;
	float Snow500mCm = 0;
	//! water held by the snow of each level (mm)
	float SnowWaterSeaLevelMm = 0;
	float SnowWater250mMm = 0;
	float SnowWater500mMm = 0;
	//! current warm spell or cold snap (degrees)
	float TempAnomaly = 0;
	//! snow model the depths come from: 2 = the Kyiv snow pack of v0.3 (earlier depths are replaced on start)
	int SnowModel = 0;
	//! ice on ponds and lakes at each level (cm) and the water temperature of the open ponds (degrees)
	float IceSeaLevelCm = 0;
	float Ice250mCm = 0;
	float Ice500mCm = 0;
	float PondTempSeaLevel = 0;
	float PondTemp250m = 0;
	float PondTemp500m = 0;
	//! 1 once the pond values above exist (a state of an earlier version starts them from the Kyiv climate)
	int IceModel = 0;
}

