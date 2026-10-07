modded class MissionServer
{
	protected ref SZ_ServerController m_SZ_Server;

	override void OnInit()
	{
		super.OnInit();
		if (SZ_Util.IsSeasonalWorld())
		{
			m_SZ_Server = new SZ_ServerController();
			m_SZ_Server.Init();
		}
	}

	override void OnUpdate(float timeslice)
	{
		super.OnUpdate(timeslice);
		if (m_SZ_Server)
			m_SZ_Server.Update(timeslice);
	}

	override void InvokeOnConnect(PlayerBase player, PlayerIdentity identity)
	{
		super.InvokeOnConnect(player, identity);
		if (m_SZ_Server && identity)
			m_SZ_Server.SendState(identity);
	}

	override void OnMissionFinish()
	{
		if (m_SZ_Server)
			m_SZ_Server.Shutdown();
		m_SZ_Server = null;
		super.OnMissionFinish();
	}
}

modded class MissionGameplay
{
	protected ref SZ_ClientController m_SZ_Client;

	override void OnInit()
	{
		super.OnInit();
		if (SZ_Util.IsSeasonalWorld())
			m_SZ_Client = new SZ_ClientController();
	}

	override void OnUpdate(float timeslice)
	{
		super.OnUpdate(timeslice);
		if (m_SZ_Client)
			m_SZ_Client.Update(timeslice);
	}

	override void OnMissionFinish()
	{
		if (m_SZ_Client)
			m_SZ_Client.Shutdown();
		m_SZ_Client = null;
		// A later connection must wait for its own server's state.
		if (!g_Game.IsServer())
			SZ_State.s_Valid = false;
		super.OnMissionFinish();
	}
}

