//! Server configuration, $profile:SeasonZ/config.json
class SZ_Config
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

//! Persistent runtime state, $profile:SeasonZ/state.json
class SZ_PersistentState
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
	//! Version 4 persists carrying history; layout 1 pins the ordered Chernarus pond dataset.
	int PondLayout = 0;
	string PondWorld;
	ref array<int> PondCarry;
	//! Version 5: simulation cursor and unconsumed weighted time, including catch-up across restarts.
	float ClimateCycle;
	float ClimatePendingCycle;
	float ClimateCycleTotal;
	float ClockRemainder;
	ref array<float> SnowWetDays;

	//! Positive comparisons reject NaN as well as infinities and unreasonable edited save data.
	static bool InRange(float value, float low, float high)
	{
		return value >= low && value <= high;
	}

	bool ValidForLoad()
	{
		if (Version < 1 || Version > 5 || SnowModel < 0 || SnowModel > 2 || IceModel < 0 || IceModel > 1)
			return false;
		if (!InRange(CycleDays, -1000000, 1000000) || !InRange(TempAnomaly, -100, 100))
			return false;
		if (!InRange(SnowSeaLevelCm, 0, 1000) || !InRange(Snow250mCm, 0, 1000) || !InRange(Snow500mCm, 0, 1000))
			return false;
		if (!InRange(SnowWaterSeaLevelMm, 0, 10000) || !InRange(SnowWater250mMm, 0, 10000) || !InRange(SnowWater500mMm, 0, 10000))
			return false;
		if (!InRange(IceSeaLevelCm, 0, 10000) || !InRange(Ice250mCm, 0, 10000) || !InRange(Ice500mCm, 0, 10000))
			return false;
		if (!InRange(PondTempSeaLevel, 0, 100) || !InRange(PondTemp250m, 0, 100) || !InRange(PondTemp500m, 0, 100))
			return false;
		if (Version >= 4)
		{
			if (!SZ_PondProtocol.Valid(PondLayout, PondWorld, PondCarry))
				return false;
		}
		else if (PondLayout != 0 || PondWorld != "" || (PondCarry && PondCarry.Count() > 0))
			return false;
		if (Version >= 5)
		{
			if (!InRange(ClimateCycleTotal, 18.25, 7300) || !InRange(ClimateCycle, 0, ClimateCycleTotal) || !InRange(ClimatePendingCycle, 0, 1000000) || !InRange(ClockRemainder, -0.001, 0.001))
				return false;
			if (!SnowWetDays || SnowWetDays.Count() != 3)
				return false;
			foreach (float wet : SnowWetDays)
			{
				if (!InRange(wet, 0, 1))
					return false;
			}
		}
		if (SnowModel == 2)
		{
			if ((SnowSeaLevelCm > 0) != (SnowWaterSeaLevelMm > 0) || (Snow250mCm > 0) != (SnowWater250mMm > 0) || (Snow500mCm > 0) != (SnowWater500mMm > 0))
				return false;
		}
		return true;
	}
}

