//! Local perf harness. Histogram is opt-in; nothing is logged per frame.
modded class MissionGameplay
{
	protected ref array<int> m_APBins;
	protected int m_APFrames;
	protected float m_APTotal;
	protected float m_APMax;
	protected int m_AP33;
	protected int m_AP50;
	protected int m_AP100;

	override void OnUpdate(float timeslice)
	{
		super.OnUpdate(timeslice);
		if (!m_APBins)
			return;
		float ms = timeslice * 1000.0;
		int bin = Math.Clamp(Math.Ceil(ms), 0, 1000);
		m_APBins[bin] = m_APBins[bin] + 1;
		m_APFrames++;
		m_APTotal += ms;
		m_APMax = Math.Max(m_APMax, ms);
		if (ms > 33.333)
			m_AP33++;
		if (ms > 50.0)
			m_AP50++;
		if (ms > 100.0)
			m_AP100++;
	}

	protected int APPercentile(float fraction)
	{
		int need = Math.Ceil(m_APFrames * fraction);
		int have = 0;
		for (int i = 0; i < m_APBins.Count(); i++)
		{
			have += m_APBins[i];
			if (have >= need)
				return i;
		}
		return 1000;
	}

	override protected bool DST_Extra2(string cmd)
	{
		if (cmd.IndexOf("frameperf") == 0)
		{
			if (m_APBins && m_APFrames > 0)
				Print(string.Format("[DSTest] frameperf frames=%1 mean_ms=%2 p95_ms_le=%3 p99_ms_le=%4 max_ms=%5 over33=%6 over50=%7 over100=%8", m_APFrames, m_APTotal / m_APFrames, APPercentile(0.95), APPercentile(0.99), m_APMax, m_AP33, m_AP50, m_AP100));
			if (!m_APBins)
				m_APBins = new array<int>;
			m_APBins.Clear();
			for (int b = 0; b <= 1000; b++)
				m_APBins.Insert(0);
			m_APFrames = 0;
			m_APTotal = 0;
			m_APMax = 0;
			m_AP33 = 0;
			m_AP50 = 0;
			m_AP100 = 0;
			Print("[DSTest] frameperf reset");
			return true;
		}
		if (cmd.IndexOf("detailnear ") == 0)
		{
			TStringArray dn = new TStringArray;
			cmd.Split(" ", dn);
			SZ_State.s_DebugCarpetDetailNear = dn[1].ToFloat();
			Print("[DSTest] detailnear " + SZ_State.s_DebugCarpetDetailNear.ToString());
			return true;
		}
		if (cmd.IndexOf("carpetidle ") == 0)
		{
			SZ_State.s_DebugCarpetIdle = cmd.IndexOf("carpetidle 1") == 0;
			Print("[DSTest] carpetidle " + SZ_State.s_DebugCarpetIdle.ToString());
			return true;
		}
		if (cmd.IndexOf("perfinventory") == 0)
		{
			FileHandle apFile = OpenFile("$profile:astra_models.csv", FileMode.WRITE);
			if (apFile && m_SZ_Client)
			{
				FPrintln(apFile, "system,model,count");
				if (m_SZ_Client.GetCarpet())
					m_SZ_Client.GetCarpet().PerfInventory(apFile);
				if (m_SZ_Client.GetRoofs())
					m_SZ_Client.GetRoofs().PerfInventory(apFile);
				if (m_SZ_Client.GetTrees())
					m_SZ_Client.GetTrees().PerfInventory(apFile);
				CloseFile(apFile);
			}
			Print("[DSTest] perfinventory complete");
			return true;
		}
		return super.DST_Extra2(cmd);
	}
}
