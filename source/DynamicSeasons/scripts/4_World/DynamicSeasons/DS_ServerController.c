//! Server: season clock, world date, snow cover simulation, persistence and sync
class DS_ServerController
{
	protected ref DS_Config m_Config;
	protected ref DS_PersistentState m_State;
	//! walkable ice on frozen ponds around the players
	protected ref DS_PondIce m_Ice;
	protected bool m_RealTime;
	protected float m_TickTimer;
	protected float m_SyncTimer;
	protected float m_SaveTimer;
	protected float m_LiquidTimer;
	protected float m_LogTimer;
	//! season time collected between commits; single frame steps are too small for float precision at ~300 days
	protected float m_CyclePending;
	//! snow pack of the three tracked heights: the clients see the depth, the water it holds melts
	protected float m_Water[3];
	//! days a pack stays wet after a thaw or rain
	protected float m_Wet[3];
	//! water temperature of the open ponds at the three tracked heights (degrees)
	protected float m_PondTemp[3];
	//! season date of the previous snow step
	protected float m_LastDoy = -1;

	void DS_ServerController()
	{
		m_Config = new DS_Config();
		m_State = new DS_PersistentState();
	}

	void Init()
	{
		if (!FileExist(DS_Const.PROFILE_DIR))
			MakeDirectory(DS_Const.PROFILE_DIR);

		LoadConfig();
		LoadState();
		m_RealTime = m_Config.IsRealTime();

		if (!m_RealTime && !m_State.Initialized)
		{
			m_State.CycleDays = DoyToCycle(m_Config.StartDayOfYear - 1);
			m_State.Initialized = true;
		}

		DS_State.s_Snow0 = m_State.SnowSeaLevelCm;
		DS_State.s_Snow1 = m_State.Snow250mCm;
		DS_State.s_Snow2 = m_State.Snow500mCm;
		m_Water[0] = m_State.SnowWaterSeaLevelMm;
		m_Water[1] = m_State.SnowWater250mMm;
		m_Water[2] = m_State.SnowWater500mMm;
		DS_State.s_TempAnomaly = m_State.TempAnomaly;
		DS_State.s_Ice0 = m_State.IceSeaLevelCm;
		DS_State.s_Ice1 = m_State.Ice250mCm;
		DS_State.s_Ice2 = m_State.Ice500mCm;
		m_PondTemp[0] = m_State.PondTempSeaLevel;
		m_PondTemp[1] = m_State.PondTemp250m;
		m_PondTemp[2] = m_State.PondTemp500m;

		ComputeDayOfYear();
		if (m_State.SnowModel < 2)
		{
			// first start, or depths from the earlier snow model: begin with the snow Kyiv typically has on this date
			SeedSnow();
			m_State.SnowModel = 2;
			m_State.Version = 2;
			Print(string.Format("[DynamicSeasons] snow pack started from the Kyiv climate for day %1", DS_State.s_DayOfYear));
		}
		if (m_State.IceModel < 1)
		{
			// first start, or a state from before the pond ice: begin with the ice the ponds typically have on this date
			SeedPonds();
			m_State.IceModel = 1;
			m_State.Version = 3;
			Print(string.Format("[DynamicSeasons] pond ice started from the Kyiv climate for day %1", DS_State.s_DayOfYear));
		}
		ApplyDate();
		DS_State.s_Valid = true;
		UpdateLiquids();
		SaveState();
		LogStatus("init");
		m_Ice = new DS_PondIce();
		m_Ice.InitServer();
		Print(string.Format("[DynamicSeasons] world position: latitude=%1 longitude=%2", g_Game.GetWorld().GetLatitude(), g_Game.GetWorld().GetLongitude()));
	}

	protected void LoadConfig()
	{
		string error;
		bool loaded = false;
		if (FileExist(DS_Const.CONFIG_FILE))
		{
			DS_Config cfg;
			if (JsonFileLoader<DS_Config>.LoadFile(DS_Const.CONFIG_FILE, cfg, error) && cfg)
			{
				m_Config = cfg;
				loaded = true;
			}
			else
			{
				Print("[DynamicSeasons] config.json could not be read, using defaults this session: " + error);
			}
		}
		else
		{
			loaded = true;
		}

		m_Config.Validate();
		DS_State.s_WinterHaze = m_Config.WinterHaze;
		if (loaded)
			JsonFileLoader<DS_Config>.SaveFile(DS_Const.CONFIG_FILE, m_Config, error);
	}

	protected void LoadState()
	{
		string error;
		if (!FileExist(DS_Const.STATE_FILE))
			return;

		DS_PersistentState st;
		if (JsonFileLoader<DS_PersistentState>.LoadFile(DS_Const.STATE_FILE, st, error) && st)
			m_State = st;
		else
			Print("[DynamicSeasons] state.json could not be read: " + error);
	}

	void SaveState()
	{
		m_State.SnowSeaLevelCm = DS_State.s_Snow0;
		m_State.Snow250mCm = DS_State.s_Snow1;
		m_State.Snow500mCm = DS_State.s_Snow2;
		m_State.SnowWaterSeaLevelMm = m_Water[0];
		m_State.SnowWater250mMm = m_Water[1];
		m_State.SnowWater500mMm = m_Water[2];
		m_State.TempAnomaly = DS_State.s_TempAnomaly;
		m_State.IceSeaLevelCm = DS_State.s_Ice0;
		m_State.Ice250mCm = DS_State.s_Ice1;
		m_State.Ice500mCm = DS_State.s_Ice2;
		m_State.PondTempSeaLevel = m_PondTemp[0];
		m_State.PondTemp250m = m_PondTemp[1];
		m_State.PondTemp500m = m_PondTemp[2];
		string error;
		if (!JsonFileLoader<DS_PersistentState>.SaveFile(DS_Const.STATE_FILE, m_State, error))
			Print("[DynamicSeasons] state.json could not be written: " + error);
	}

	// ---- season cycle (Multiplier mode) --------------------------------------------------
	// cycle order: spring (Mar 1), summer (Jun 1), autumn (Sep 1), winter (Dec 1)
	protected float SegStart(int i)
	{
		if (i == 0)
			return 59;
		if (i == 1)
			return 151;
		if (i == 2)
			return 243;
		return 334;
	}

	protected float SegDays(int i)
	{
		if (i == 0)
			return 92;
		if (i == 1)
			return 92;
		if (i == 2)
			return 91;
		return 90;
	}

	protected float SegWeight(int i)
	{
		if (i == 0)
			return m_Config.SpringLengthMultiplier;
		if (i == 1)
			return m_Config.SummerLengthMultiplier;
		if (i == 2)
			return m_Config.AutumnLengthMultiplier;
		return m_Config.WinterLengthMultiplier;
	}

	protected float CycleTotal()
	{
		float total = 0;
		for (int i = 0; i < 4; i++)
			total += SegDays(i) * SegWeight(i);
		return total;
	}

	protected float CycleToDoy(float pos)
	{
		float total = CycleTotal();
		while (pos < 0)
			pos += total;
		while (pos >= total)
			pos -= total;

		float acc = 0;
		for (int i = 0; i < 4; i++)
		{
			float len = SegDays(i) * SegWeight(i);
			if (pos < acc + len || i == 3)
			{
				float frac = 0;
				if (len > 0)
					frac = Math.Clamp((pos - acc) / len, 0, 0.99999);
				return DS_Calendar.Wrap(SegStart(i) + frac * SegDays(i));
			}
			acc += len;
		}
		return 0;
	}

	protected float DoyToCycle(float doy)
	{
		float acc = 0;
		for (int i = 0; i < 4; i++)
		{
			float rel = DS_Calendar.Wrap(doy - SegStart(i));
			if (rel < SegDays(i))
				return acc + rel * SegWeight(i);
			acc += SegDays(i) * SegWeight(i);
		}
		return 0;
	}

	protected void ComputeDayOfYear()
	{
		if (DS_State.s_DebugDoy >= 0)
		{
			DS_State.s_DayOfYear = DS_State.s_DebugDoy;
			return;
		}
		if (m_RealTime)
		{
			int year;
			int month;
			int day;
			int hour;
			int minute;
			int second;
			GetYearMonthDay(year, month, day);
			GetHourMinuteSecond(hour, minute, second);
			DS_State.s_DayOfYear = DS_Calendar.DayOfYear(month, day, (hour * 3600 + minute * 60 + second) / 86400.0);
		}
		else
		{
			DS_State.s_DayOfYear = CycleToDoy(m_State.CycleDays);
		}
	}

	//! keeps the in-game calendar date on the season date, time of day is untouched
	protected void ApplyDate()
	{
		int year;
		int month;
		int day;
		int hour;
		int minute;
		g_Game.GetWorld().GetDate(year, month, day, hour, minute);

		int wantMonth;
		int wantDay;
		DS_Calendar.ToMonthDay(DS_State.s_DayOfYear, wantMonth, wantDay);
		if (wantMonth != month || wantDay != day)
		{
			g_Game.GetWorld().SetDate(year, wantMonth, wantDay, hour, minute);
			if (g_Game.GetMission() && g_Game.GetMission().GetWorldData())
				g_Game.GetMission().GetWorldData().DS_RefreshTemperature();
		}
	}

	protected void UpdateLiquids()
	{
		if (!g_Game.GetMission())
			return;
		WorldData wd = g_Game.GetMission().GetWorldData();
		if (wd)
			wd.DS_UpdateLiquids(DS_State.s_DayOfYear);
	}

	// ---- snow cover -----------------------------------------------------------------------
	// Each tracked height keeps a snow pack: the water it holds and its depth. Snowfall adds fresh snow (1 cm per mm
	// of water), the pack settles from a tenth to a third of water within about a week, thaws melt it by degree-days
	// of the season day and the ground melts it from below in early winter. All rates run on the season clock, so a
	// faster clock gives the same snow per season day. Calibrated against Kyiv (tools/climate_sim.py).
	protected float LevelAltitude(int level)
	{
		if (level == 0)
			return DS_Const.LEVEL_ALT_0;
		if (level == 1)
			return DS_Const.LEVEL_ALT_1;
		return DS_Const.LEVEL_ALT_2;
	}

	protected float GetDepth(int level)
	{
		if (level == 0)
			return DS_State.s_Snow0;
		if (level == 1)
			return DS_State.s_Snow1;
		return DS_State.s_Snow2;
	}

	protected void SetDepth(int level, float depth)
	{
		if (level == 0)
			DS_State.s_Snow0 = depth;
		else if (level == 1)
			DS_State.s_Snow1 = depth;
		else
			DS_State.s_Snow2 = depth;
	}

	//! the snow Kyiv typically has on the season date, settled
	protected void SeedSnow()
	{
		float doy = DS_State.s_DayOfYear;
		for (int level = 0; level < 3; level++)
		{
			float depth = DS_Climate.Monthly(DS_Climate.SeedDepths(level), doy);
			SetDepth(level, depth);
			m_Water[level] = depth * 10.0 * 0.28;
			m_Wet[level] = 0;
		}
	}

	protected float Density(float water, float depth)
	{
		if (depth < 0.01)
			return 0.1;
		return Math.Clamp(water / (10.0 * depth), 0.1, 0.5);
	}

	// ---- pond ice --------------------------------------------------------------------------------
	protected float GetIce(int level)
	{
		if (level == 0)
			return DS_State.s_Ice0;
		if (level == 1)
			return DS_State.s_Ice1;
		return DS_State.s_Ice2;
	}

	protected void SetIce(int level, float ice)
	{
		if (level == 0)
			DS_State.s_Ice0 = ice;
		else if (level == 1)
			DS_State.s_Ice1 = ice;
		else
			DS_State.s_Ice2 = ice;
	}

	//! the ice and pond temperature Kyiv's ponds typically have on the season date
	protected void SeedPonds()
	{
		float doy = DS_State.s_DayOfYear;
		for (int level = 0; level < 3; level++)
		{
			float ice = DS_Climate.Monthly(DS_Climate.IceSeed(level), doy);
			if (ice < 0.5)
				ice = 0;
			SetIce(level, ice);
			float temp = DS_Climate.Monthly(DS_Climate.PondTempSeed(level), doy);
			if (ice > 0)
				temp = 0;
			m_PondTemp[level] = temp;
		}
	}

	//! open water follows the daily mean temperature and cannot cool below freezing; at freezing the cold grows ice
	//! (Stefan's law, slower under snow), thaws and the spring sun melt it (see DS_Climate)
	protected void StepPond(int level, float days, WorldData wd)
	{
		float doy = DS_State.s_DayOfYear;
		float tmin;
		float tmax;
		wd.DS_DailyRange(doy, LevelAltitude(level), tmin, tmax);
		float mean = 0.5 * (tmin + tmax);
		float ice = GetIce(level);
		float fdd;
		if (ice <= 0)
		{
			float temp = m_PondTemp[level];
			temp += (mean - temp) * Math.Min(1.0, days / DS_Climate.POND_DAYS);
			if (temp >= 0)
			{
				m_PondTemp[level] = temp;
				SetIce(level, 0);
				return;
			}
			// the surface reached freezing: the cold beyond it starts the ice
			fdd = -temp * DS_Climate.POND_DAYS;
			m_PondTemp[level] = 0;
		}
		else
		{
			fdd = DS_Climate.NegativeMean(tmin, tmax) * days;
		}
		float snow = GetDepth(level);
		float alpha = DS_Climate.ICE_ALPHA / (1.0 + snow / DS_Climate.ICE_SNOW_HALF);
		ice = Math.Sqrt(ice * ice + alpha * alpha * fdd);
		float pddDay = DS_Climate.PositiveMean(tmin, tmax);
		float sun = DS_Climate.Monthly(DS_Climate.ICE_SUN, doy);
		float melt = (DS_Climate.ICE_MELT * pddDay + sun * Math.Min(1.0, pddDay)) * days;
		if (snow >= 1.0)
			melt *= DS_Climate.ICE_SNOW_SHIELD;
		ice -= melt;
		if (ice < 0.2)
		{
			ice = 0;
			m_PondTemp[level] = Math.Max(m_PondTemp[level], 0);
		}
		SetIce(level, ice);
	}

	//! warm spells and cold snaps: the anomaly drifts back to the climate within a few days while the day to day
	//! weather pushes it around (a first order random process on the season clock)
	protected void UpdateAnomaly(float days)
	{
		if (DS_State.s_DebugAnomaly > -100)
		{
			DS_State.s_TempAnomaly = DS_State.s_DebugAnomaly;
			return;
		}
		float sigma = DS_Climate.Monthly(DS_Climate.ANOMALY_SIGMA, DS_State.s_DayOfYear);
		float keep = DS_Climate.Exp(-days / DS_Climate.ANOMALY_DAYS);
		float spread = Math.Sqrt(Math.Max(0, 1.0 - keep * keep));
		float kick = DS_Climate.Gauss();
		DS_State.s_TempAnomaly = DS_State.s_TempAnomaly * keep + sigma * spread * kick;
	}

	protected void StepLevel(int level, float days, float snowfall, float rain, float rate, WorldData wd)
	{
		float alt = LevelAltitude(level);
		float hours = days * 24.0;
		float doy = DS_State.s_DayOfYear;
		float now = wd.GetBaseEnvTemperatureAtPosition(Vector(0, alt, 0));
		float tmin;
		float tmax;
		wd.DS_DailyRange(doy, alt, tmin, tmax);
		float water = (snowfall + rain) * rate * hours * DS_Climate.Orographic(alt);
		bool asSnow = (snowfall > 0.001 && now <= 1.5) || (rain > 0.001 && now <= 0.0);
		float swe = m_Water[level];
		float depth = GetDepth(level);
		if (water > 0 && asSnow)
		{
			water *= m_Config.SnowBuildupMultiplier;
			swe += water;
			depth += water;
		}
		else if (water > 0 && swe > 0)
		{
			m_Wet[level] = 1.0;
		}

		if (swe <= 0)
		{
			m_Water[level] = 0;
			SetDepth(level, 0);
			return;
		}

		float rho = Density(swe, depth);
		float pdd = DS_Climate.PositiveMean(tmin, tmax);
		float melt = DS_Climate.Monthly(DS_Climate.MELT_FACTOR, doy) * pdd * days;
		if (!asSnow && rain > 0.001)
			melt += rain * rate * hours * Math.Max(0, now) / 80.0;
		melt += DS_Climate.Monthly(DS_Climate.GROUND_MELT, doy) * days;
		melt *= m_Config.SnowMeltMultiplier;
		if (melt > 0)
		{
			swe = Math.Max(0, swe - melt);
			if (pdd > 0.2)
				m_Wet[level] = 1.0;
		}

		// dry snow settles to 0.30 within about a week, wet snow to 0.42 within two days
		float target = 0.30;
		float tau = 6.0;
		if (pdd > 0.2 || m_Wet[level] > 0)
		{
			target = 0.42;
			tau = 2.0;
		}
		rho += (target - rho) * Math.Min(1.0, days / tau);
		m_Wet[level] = Math.Max(0, m_Wet[level] - days);
		depth = 0;
		if (swe > 0)
			depth = swe / (10.0 * rho);
		float cap = DS_Climate.DepthCap(alt);
		if (depth > cap)
		{
			depth = cap;
			swe = Math.Min(swe, cap * 10.0 * rho);
		}
		m_Water[level] = swe;
		SetDepth(level, depth);
	}

	protected void UpdateSnow()
	{
		if (!g_Game.GetMission())
			return;
		WorldData wd = g_Game.GetMission().GetWorldData();
		if (!wd)
			return;

		float doy = DS_State.s_DayOfYear;
		float days = 0;
		if (m_LastDoy >= 0)
		{
			days = DS_Calendar.Wrap(doy - m_LastDoy);
			// a jump of the date (an admin change of the clock) is not elapsed time
			if (days > 2.0)
				days = 0;
		}
		m_LastDoy = doy;
		if (days <= 0)
			return;

		UpdateAnomaly(days);
		wd.DS_RefreshTemperature();
		Weather weather = g_Game.GetWeather();
		float snowfall = weather.GetSnowfall().GetActual();
		float rain = weather.GetRain().GetActual();
		float rate = DS_Climate.Monthly(DS_Climate.PRECIP_RATE, doy);
		for (int level = 0; level < 3; level++)
			StepLevel(level, days, snowfall, rain, rate, wd);
		for (int pond = 0; pond < 3; pond++)
			StepPond(pond, days, wd);
	}

	//! converts ongoing precipitation when the temperature crosses freezing
	protected void UpdatePrecipitationType()
	{
		if (!g_Game.GetMission())
			return;
		WorldData wd = g_Game.GetMission().GetWorldData();
		if (!wd)
			return;

		Weather weather = g_Game.GetWeather();
		float temp = wd.DS_PrecipTemperature();
		float snow = weather.GetSnowfall().GetActual();
		float rain = weather.GetRain().GetActual();

		if (snow > 0.02 && temp > 1.5)
		{
			weather.GetRain().Set(Math.Max(weather.GetSnowfall().GetForecast(), snow), 90, 240);
			weather.GetSnowfall().Set(0, 90, 600);
		}
		else if (rain > 0.02 && temp < 0.3)
		{
			weather.GetSnowfall().Set(Math.Clamp(Math.Max(weather.GetRain().GetForecast(), rain) * 1.15, 0, 1), 90, 240);
			weather.GetRain().Set(0, 90, 600);
		}
	}

	// ---- sync --------------------------------------------------------------------------------
	void SendState(PlayerIdentity identity)
	{
		Param8<float, float, float, float, float, float, float, float> data = new Param8<float, float, float, float, float, float, float, float>(DS_State.s_DayOfYear, DS_State.s_Snow0, DS_State.s_Snow1, DS_State.s_Snow2, DS_State.s_TempAnomaly, DS_State.s_Ice0, DS_State.s_Ice1, DS_State.s_Ice2);
		g_Game.RPCSingleParam(null, DS_Const.RPC_STATE, data, true, identity);
	}

	void LogStatus(string reason)
	{
		float temp = 0;
		if (g_Game.GetMission() && g_Game.GetMission().GetWorldData())
			temp = g_Game.GetMission().GetWorldData().DS_PrecipTemperature();
		Weather weather = g_Game.GetWeather();
		int month;
		int day;
		DS_Calendar.ToMonthDay(DS_State.s_DayOfYear, month, day);
		string mode = "multiplier";
		if (m_RealTime)
			mode = "realtime";
		Print(string.Format("[DynamicSeasons] %1: mode=%2 date=%3-%4 season=%5 temp150m=%6 overcast=%7 rain=%8 snowfall=%9", reason, mode, month, day, DS_Calendar.SeasonName(DS_State.s_DayOfYear), temp, weather.GetOvercast().GetActual(), weather.GetRain().GetActual(), weather.GetSnowfall().GetActual()));
		Print(string.Format("[DynamicSeasons] snow cm: 0m=%1 250m=%2 500m=%3 water mm: %4 %5 %6 anomaly=%7", DS_State.s_Snow0, DS_State.s_Snow1, DS_State.s_Snow2, m_Water[0], m_Water[1], m_Water[2], DS_State.s_TempAnomaly));
		float hazeFloor = 0;
		if (g_Game.GetMission() && g_Game.GetMission().GetWorldData())
			hazeFloor = g_Game.GetMission().GetWorldData().DS_HazeFloor();
		float fogNow = weather.GetFog().GetActual();
		Print(string.Format("[DynamicSeasons] haze: winter haze %1, fog now %2", hazeFloor, fogNow));
		float doy = DS_State.s_DayOfYear;
		int clearChance = Math.Round(100.0 * DS_Climate.Monthly(DS_Climate.SUNSHINE, doy));
		int badChance = Math.Round(100.0 * DS_Climate.Monthly(DS_Climate.PRECIP_SHARE, doy));
		int thunder = Math.Round(100.0 * DS_Climate.Monthly(DS_Climate.THUNDER_SHARE, doy));
		int fog = Math.Round(100.0 * DS_Climate.Monthly(DS_Climate.FOG_SHARE, doy));
		float river = 0;
		float sea = 0;
		if (g_Game.GetMission() && g_Game.GetMission().GetWorldData())
		{
			river = g_Game.GetMission().GetWorldData().GetLiquidTypeEnviroTemperature(LIQUID_FRESHWATER);
			sea = g_Game.GetMission().GetWorldData().GetLiquidTypeEnviroTemperature(LIQUID_SALTWATER);
		}
		Print(string.Format("[DynamicSeasons] climate: clear %1 pct, bad %2 pct, thunder days %3 pct, fog days %4 pct, water river=%5 sea=%6", clearChance, badChance, thunder, fog, river, sea));
		Print(string.Format("[DynamicSeasons] ponds: ice cm 0m=%1 250m=%2 500m=%3 open water temp 0m=%4 250m=%5 500m=%6", DS_State.s_Ice0, DS_State.s_Ice1, DS_State.s_Ice2, m_PondTemp[0], m_PondTemp[1], m_PondTemp[2]));
	}

	//! sets the snow of the three levels as settled snow (admin and test use)
	void SetSnow(float depth0, float depth1, float depth2)
	{
		SetDepth(0, Math.Max(0, depth0));
		SetDepth(1, Math.Max(0, depth1));
		SetDepth(2, Math.Max(0, depth2));
		for (int level = 0; level < 3; level++)
		{
			m_Water[level] = GetDepth(level) * 10.0 * 0.30;
			m_Wet[level] = 0;
		}
		SendState(null);
		LogStatus("snow set");
	}

	//! sets the pond ice of the three levels (admin and test use)
	void SetPondIce(float ice0, float ice1, float ice2)
	{
		SetIce(0, Math.Max(0, ice0));
		SetIce(1, Math.Max(0, ice1));
		SetIce(2, Math.Max(0, ice2));
		for (int level = 0; level < 3; level++)
		{
			if (GetIce(level) > 0)
				m_PondTemp[level] = 0;
		}
		SendState(null);
		LogStatus("ice set");
	}

	void Update(float timeslice)
	{
		if (!m_RealTime)
		{
			float total = CycleTotal();
			m_CyclePending += timeslice / 86400.0 * m_Config.SeasonSpeedMultiplier * total / 365.0;
			if (m_CyclePending >= 0.001)
			{
				float before = m_State.CycleDays;
				m_State.CycleDays = before + m_CyclePending;
				// keep what the addition rounded away, so the clock does not drift
				m_CyclePending -= m_State.CycleDays - before;
				while (m_State.CycleDays >= total)
					m_State.CycleDays -= total;
			}
		}

		m_TickTimer += timeslice;
		if (m_TickTimer >= 5.0)
		{
			float step = m_TickTimer;
			m_TickTimer = 0;
			ComputeDayOfYear();
			ApplyDate();
			UpdateSnow();
			UpdatePrecipitationType();
			if (g_Game.GetMission() && g_Game.GetMission().GetWorldData())
				g_Game.GetMission().GetWorldData().DS_EnforceHaze();
		}

		m_SyncTimer += timeslice;
		if (m_SyncTimer >= 10.0)
		{
			m_SyncTimer = 0;
			SendState(null);
		}

		m_LiquidTimer += timeslice;
		if (m_LiquidTimer >= 60.0)
		{
			m_LiquidTimer = 0;
			UpdateLiquids();
		}

		m_SaveTimer += timeslice;
		if (m_SaveTimer >= 120.0)
		{
			m_SaveTimer = 0;
			SaveState();
		}

		m_LogTimer += timeslice;
		if (m_LogTimer >= 600.0)
		{
			m_LogTimer = 0;
			LogStatus("status");
		}

		if (m_Ice)
			m_Ice.UpdateServer(timeslice);
	}

	DS_PondIce GetIce()
	{
		return m_Ice;
	}
}

