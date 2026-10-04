//! Client: season visuals (snow cover, lighting, colour grading, grass under snow)
class SZ_ClientController
{
	protected ref SZ_SnowCarpet m_Carpet;
	protected ref SZ_TreeSwap m_Trees;
	protected ref SZ_RoofSnow m_Roofs;
	protected ref SZ_GrassCut m_Grass;
	protected ref SZ_PondIce m_Ice;
	protected PPERequester_SeasonZ m_PPE;
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

	SZ_TreeSwap GetTrees()
	{
		return m_Trees;
	}

	SZ_SnowCarpet GetCarpet()
	{
		return m_Carpet;
	}

	SZ_RoofSnow GetRoofs()
	{
		return m_Roofs;
	}

	SZ_PondIce GetIce()
	{
		return m_Ice;
	}

	//! test harness statistics: the ticks since part0 for one part (keeps the longest); returns the tick now
	protected int StatPart(int part, int part0)
	{
		int now = TickCount(0);
		int d = now - part0;
		if (d > SZ_State.s_StatPartMax[part])
			SZ_State.s_StatPartMax[part] = d;
		SZ_State.s_StatPartSum[part] = SZ_State.s_StatPartSum[part] + d;
		return now;
	}

	void Update(float timeslice)
	{
		if (!SZ_State.s_Valid)
			return;

		if (!m_HasSnow)
		{
			m_S0 = SZ_State.s_Snow0;
			m_S1 = SZ_State.s_Snow1;
			m_S2 = SZ_State.s_Snow2;
			m_HasSnow = true;
		}
		else
		{
			float rate = 0.35 * timeslice; // cm per second of visual catch-up
			m_S0 = Approach(m_S0, SZ_State.s_Snow0, rate);
			m_S1 = Approach(m_S1, SZ_State.s_Snow1, rate);
			m_S2 = Approach(m_S2, SZ_State.s_Snow2, rate);
		}

		vector camera = g_Game.GetCurrentCameraPosition();
		if (!SZ_State.s_StatPartMax)
		{
			SZ_State.s_StatPartMax = new array<int>;
			SZ_State.s_StatPartSum = new array<int>;
			for (int sp = 0; sp < 6; sp++)
			{
				SZ_State.s_StatPartMax.Insert(0);
				SZ_State.s_StatPartSum.Insert(0);
			}
		}
		int frame0 = TickCount(0);
		int part0 = frame0;

		if (!m_Carpet)
		{
			m_Carpet = new SZ_SnowCarpet();
			m_Carpet.Init();
		}
		m_Carpet.Update(timeslice, camera, m_S0, m_S1, m_S2);
		part0 = StatPart(0, part0);

		if (!m_Trees)
		{
			m_Trees = new SZ_TreeSwap();
			m_Trees.Init();
		}
		m_Trees.Update(timeslice, camera, SZ_State.s_DayOfYear, m_S0, m_S1, m_S2);
		part0 = StatPart(1, part0);

		if (!m_Roofs)
		{
			m_Roofs = new SZ_RoofSnow();
			m_Roofs.Init(m_Carpet.GetCell());
		}
		m_Roofs.Update(timeslice, camera, m_S0, m_S1, m_S2);
		part0 = StatPart(2, part0);

		if (!m_Grass)
			m_Grass = new SZ_GrassCut();
		m_Grass.Update(timeslice, camera, m_S0, m_S1, m_S2);
		part0 = StatPart(3, part0);

		if (!m_Ice)
		{
			m_Ice = new SZ_PondIce();
			m_Ice.Init();
		}
		m_Ice.Update(timeslice, camera);
		part0 = StatPart(4, part0);

		SZ_Footprints.Update(timeslice, m_S0, m_S1, m_S2);
		SZ_TyreTracks.Update(timeslice, camera, m_S0, m_S1, m_S2);
		part0 = StatPart(5, part0);
		SZ_State.s_StatPartFrames++;
		float tps = SZ_RoofSnow.DebugTicksPerSec();
		if (tps > 0 && TickCount(frame0) > tps * 0.008)
			SZ_State.s_StatPartSlow++;
		SZ_State.s_StatCarpet = m_Carpet.GetObjectCount();
		SZ_State.s_StatSkirts = m_Carpet.GetSkirtCount();
		SZ_State.s_StatTrees = m_Trees.GetSwappedCount();
		SZ_State.s_StatTreesKnown = m_Trees.GetKnownCount();
		SZ_State.s_StatTreeReach = m_Trees.GetReach();
		SZ_State.s_StatRoofs = m_Roofs.GetObjectCount();
		SZ_State.s_StatRays = m_Roofs.GetRayCount();
		SZ_State.s_StatCutters = m_Grass.GetCount();

		float depthHere = SZ_State.SnowAt(g_Game.SurfaceY(camera[0], camera[2]), m_S0, m_S1, m_S2);
		float cover = Math.Clamp(depthHere / 10.0, 0, 1);
		if (SZ_State.s_DebugCover >= 0)
			cover = SZ_State.s_DebugCover;

		m_PPETimer += timeslice;
		if (m_PPETimer >= 0.5)
		{
			m_PPETimer = 0;
			UpdateGrade(cover);
		}

		m_LightTimer += timeslice;
		if (m_LightTimer >= 2.0 || SZ_State.s_LightingDirty)
		{
			m_LightTimer = 0;
			UpdateLighting(cover);
		}

		m_LogTimer += timeslice;
		if (m_LogTimer >= 300.0)
		{
			m_LogTimer = 0;
			Print(string.Format("[SeasonZ] client: day=%1 snow here=%2 cm cover objects=%3 light=%4 trees=%5/%6 within %7 m ice plates=%8", SZ_State.s_DayOfYear, depthHere, m_Carpet.GetObjectCount(), m_LightIndex, m_Trees.GetSwappedCount(), m_Trees.GetKnownCount(), Math.Round(m_Trees.GetReach()), m_Ice.GetObjectCount()));
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
			m_PPE = PPERequester_SeasonZ.Cast(PPERequesterBank.GetRequester(PPERequester_SeasonZ));
			if (!m_PPE)
				return;
			m_PPE.Start();
		}

		float doy = SZ_State.s_DayOfYear;
		float sp = SZ_Calendar.Spring(doy);
		float su = SZ_Calendar.Summer(doy);
		float au = SZ_Calendar.Autumn(doy);
		float wi = SZ_Calendar.Winter(doy);

		float saturation = 1.0 + 0.06 * sp + 0.03 * su - 0.02 * au - 0.05 * wi - 0.16 * cover;
		float subR = 0.012 * wi + 0.03 * cover;
		float subG = 0.012 * au + 0.012 * cover;
		float subB = 0.05 * au + 0.015 * su;
		m_PPE.SZ_SetGrade(saturation, subR, subG, subB);
	}

	protected string LightingFile(int baseConfig, int index)
	{
		string baseName = "default";
		if (baseConfig == 1)
			baseName = "darknight";

		if (index <= 0)
			return "dz\\data\\lighting\\lighting_" + baseName + ".txt";
		return SZ_Const.DATA + "lighting\\ds_" + baseName + "_" + SZ_Util.Pad2(index) + ".txt";
	}

	protected void UpdateLighting(float cover)
	{
		int baseConfig = CfgGameplayHandler.GetLightingConfig();
		if (SZ_State.s_DebugLightBase >= 0)
			baseConfig = SZ_State.s_DebugLightBase;
		if (baseConfig != 0 && baseConfig != 1)
			return;

		float winter = SZ_Calendar.Winter(SZ_State.s_DayOfYear);
		float blend = Math.Clamp(cover * 0.85 + winter * 0.15, 0, 1);
		int index = Math.Round(blend * 10.0);
		if (SZ_State.s_DebugLightIndex >= 0)
			index = SZ_State.s_DebugLightIndex;
		if (index == m_LightIndex && baseConfig == m_LightBase && !SZ_State.s_LightingDirty)
			return;

		g_Game.GetWorld().LoadNewLightingCfg(LightingFile(baseConfig, index));
		m_LightIndex = index;
		m_LightBase = baseConfig;
		SZ_State.s_LightingDirty = false;
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
		SZ_Footprints.Clear();
		SZ_TyreTracks.Clear();

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

