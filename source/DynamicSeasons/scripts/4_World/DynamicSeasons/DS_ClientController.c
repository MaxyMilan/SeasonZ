//! Client: season visuals (snow cover, lighting, colour grading, grass under snow)
class DS_ClientController
{
	protected ref DS_SnowCarpet m_Carpet;
	protected ref DS_TreeSwap m_Trees;
	protected ref DS_RoofSnow m_Roofs;
	protected ref DS_GrassCut m_Grass;
	protected ref DS_PondIce m_Ice;
	protected PPERequester_DynamicSeasons m_PPE;
	protected float m_S0;
	protected float m_S1;
	protected float m_S2;
	protected bool m_HasSnow;
	protected float m_PPETimer;
	protected float m_LightTimer;
	protected float m_GrassTimer;
	protected float m_LogTimer;
	protected int m_LightIndex = -1;
	protected int m_LightBase = -1;

	DS_TreeSwap GetTrees()
	{
		return m_Trees;
	}

	DS_SnowCarpet GetCarpet()
	{
		return m_Carpet;
	}

	DS_RoofSnow GetRoofs()
	{
		return m_Roofs;
	}

	DS_PondIce GetIce()
	{
		return m_Ice;
	}

	//! test harness statistics: the ticks since part0 for one part (keeps the longest); returns the tick now
	protected int StatPart(int part, int part0)
	{
		int now = TickCount(0);
		int d = now - part0;
		if (d > DS_State.s_StatPartMax[part])
			DS_State.s_StatPartMax[part] = d;
		DS_State.s_StatPartSum[part] = DS_State.s_StatPartSum[part] + d;
		return now;
	}

	void Update(float timeslice)
	{
		if (!DS_State.s_Valid)
			return;

		if (!m_HasSnow)
		{
			m_S0 = DS_State.s_Snow0;
			m_S1 = DS_State.s_Snow1;
			m_S2 = DS_State.s_Snow2;
			m_HasSnow = true;
		}
		else
		{
			float rate = 0.35 * timeslice; // cm per second of visual catch-up
			m_S0 = Approach(m_S0, DS_State.s_Snow0, rate);
			m_S1 = Approach(m_S1, DS_State.s_Snow1, rate);
			m_S2 = Approach(m_S2, DS_State.s_Snow2, rate);
		}

		vector camera = g_Game.GetCurrentCameraPosition();
		if (!DS_State.s_StatPartMax)
		{
			DS_State.s_StatPartMax = new array<int>;
			DS_State.s_StatPartSum = new array<int>;
			for (int sp = 0; sp < 6; sp++)
			{
				DS_State.s_StatPartMax.Insert(0);
				DS_State.s_StatPartSum.Insert(0);
			}
		}
		int frame0 = TickCount(0);
		int part0 = frame0;

		if (!m_Carpet)
		{
			m_Carpet = new DS_SnowCarpet();
			m_Carpet.Init();
		}
		m_Carpet.Update(timeslice, camera, m_S0, m_S1, m_S2);
		part0 = StatPart(0, part0);

		if (!m_Trees)
		{
			m_Trees = new DS_TreeSwap();
			m_Trees.Init();
		}
		m_Trees.Update(timeslice, camera, DS_State.s_DayOfYear, m_S0, m_S1, m_S2);
		part0 = StatPart(1, part0);

		if (!m_Roofs)
		{
			m_Roofs = new DS_RoofSnow();
			m_Roofs.Init(m_Carpet.GetCell());
		}
		m_Roofs.Update(timeslice, camera, m_S0, m_S1, m_S2);
		part0 = StatPart(2, part0);

		if (!m_Grass)
			m_Grass = new DS_GrassCut();
		m_Grass.Update(timeslice, camera, m_S0, m_S1, m_S2);
		part0 = StatPart(3, part0);

		if (!m_Ice)
		{
			m_Ice = new DS_PondIce();
			m_Ice.Init();
		}
		m_Ice.Update(timeslice, camera);
		part0 = StatPart(4, part0);

		DS_Footprints.Update(timeslice, m_S0, m_S1, m_S2);
		DS_TyreTracks.Update(timeslice, camera, m_S0, m_S1, m_S2);
		part0 = StatPart(5, part0);
		DS_State.s_StatPartFrames++;
		float tps = DS_RoofSnow.DebugTicksPerSec();
		if (tps > 0 && TickCount(frame0) > tps * 0.008)
			DS_State.s_StatPartSlow++;
		DS_State.s_StatCarpet = m_Carpet.GetObjectCount();
		DS_State.s_StatSkirts = m_Carpet.GetSkirtCount();
		DS_State.s_StatTrees = m_Trees.GetSwappedCount();
		DS_State.s_StatTreesKnown = m_Trees.GetKnownCount();
		DS_State.s_StatTreeReach = m_Trees.GetReach();
		DS_State.s_StatRoofs = m_Roofs.GetObjectCount();
		DS_State.s_StatRays = m_Roofs.GetRayCount();
		DS_State.s_StatCutters = m_Grass.GetCount();

		float depthHere = DS_State.SnowAt(g_Game.SurfaceY(camera[0], camera[2]), m_S0, m_S1, m_S2);
		float cover = Math.Clamp(depthHere / 10.0, 0, 1);
		if (DS_State.s_DebugCover >= 0)
			cover = DS_State.s_DebugCover;

		m_PPETimer += timeslice;
		if (m_PPETimer >= 0.5)
		{
			m_PPETimer = 0;
			UpdateGrade(cover);
		}

		m_LightTimer += timeslice;
		if (m_LightTimer >= 2.0 || DS_State.s_LightingDirty)
		{
			m_LightTimer = 0;
			UpdateLighting(cover);
		}

		m_LogTimer += timeslice;
		if (m_LogTimer >= 300.0)
		{
			m_LogTimer = 0;
			Print(string.Format("[DynamicSeasons] client: day=%1 snow here=%2 cm cover objects=%3 light=%4 trees=%5/%6 within %7 m ice plates=%8", DS_State.s_DayOfYear, depthHere, m_Carpet.GetObjectCount(), m_LightIndex, m_Trees.GetSwappedCount(), m_Trees.GetKnownCount(), Math.Round(m_Trees.GetReach()), m_Ice.GetObjectCount()));
		}
	}

	protected float Approach(float current, float target, float maxStep)
	{
		if (current < target)
			return Math.Min(current + maxStep, target);
		return Math.Max(current - maxStep, target);
	}

	protected void UpdateGrade(float cover)
	{
		if (!m_PPE)
		{
			m_PPE = PPERequester_DynamicSeasons.Cast(PPERequesterBank.GetRequester(PPERequester_DynamicSeasons));
			if (!m_PPE)
				return;
			m_PPE.Start();
		}

		float doy = DS_State.s_DayOfYear;
		float sp = DS_Calendar.Spring(doy);
		float su = DS_Calendar.Summer(doy);
		float au = DS_Calendar.Autumn(doy);
		float wi = DS_Calendar.Winter(doy);

		float saturation = 1.0 + 0.06 * sp + 0.03 * su - 0.02 * au - 0.05 * wi - 0.16 * cover;
		float subR = 0.012 * wi + 0.03 * cover;
		float subG = 0.012 * au + 0.012 * cover;
		float subB = 0.05 * au + 0.015 * su;
		m_PPE.DS_SetGrade(saturation, subR, subG, subB);
	}

	protected string LightingFile(int baseConfig, int index)
	{
		string baseName = "default";
		if (baseConfig == 1)
			baseName = "darknight";

		if (index <= 0)
			return "dz\\data\\lighting\\lighting_" + baseName + ".txt";
		return DS_Const.DATA + "lighting\\ds_" + baseName + "_" + DS_Util.Pad2(index) + ".txt";
	}

	protected void UpdateLighting(float cover)
	{
		int baseConfig = CfgGameplayHandler.GetLightingConfig();
		if (DS_State.s_DebugLightBase >= 0)
			baseConfig = DS_State.s_DebugLightBase;
		if (baseConfig != 0 && baseConfig != 1)
			return;

		float winter = DS_Calendar.Winter(DS_State.s_DayOfYear);
		float blend = Math.Clamp(cover * 0.85 + winter * 0.15, 0, 1);
		int index = Math.Round(blend * 10.0);
		if (DS_State.s_DebugLightIndex >= 0)
			index = DS_State.s_DebugLightIndex;
		if (index == m_LightIndex && baseConfig == m_LightBase && !DS_State.s_LightingDirty)
			return;

		g_Game.GetWorld().LoadNewLightingCfg(LightingFile(baseConfig, index));
		m_LightIndex = index;
		m_LightBase = baseConfig;
		DS_State.s_LightingDirty = false;
	}

	void Shutdown()
	{
		if (m_Carpet)
			m_Carpet.Clear();
		m_Carpet = null;

		if (m_Trees)
			m_Trees.Clear();
		m_Trees = null;

		if (m_Roofs)
			m_Roofs.Clear();
		m_Roofs = null;
		if (m_Grass)
			m_Grass.Clear();
		m_Grass = null;
		if (m_Ice)
			m_Ice.Clear();
		m_Ice = null;
		DS_Footprints.Clear();
		DS_TyreTracks.Clear();

		if (m_PPE)
			m_PPE.Stop();

		if (m_LightIndex > 0 && g_Game && g_Game.GetWorld())
		{
			int baseConfig = CfgGameplayHandler.GetLightingConfig();
			if (baseConfig == 0 || baseConfig == 1)
				g_Game.GetWorld().LoadNewLightingCfg(LightingFile(baseConfig, 0));
		}
		m_LightIndex = -1;
	}
}

