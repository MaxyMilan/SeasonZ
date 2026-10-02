modded class MissionServer
{
	protected ref DS_ServerController m_DS_Server;

	override void OnInit()
	{
		super.OnInit();
		if (DS_Util.IsSeasonalWorld())
		{
			m_DS_Server = new DS_ServerController();
			m_DS_Server.Init();
		}
	}

	override void OnUpdate(float timeslice)
	{
		super.OnUpdate(timeslice);
		if (m_DS_Server)
			m_DS_Server.Update(timeslice);
	}

	override void InvokeOnConnect(PlayerBase player, PlayerIdentity identity)
	{
		super.InvokeOnConnect(player, identity);
		if (m_DS_Server && identity)
			m_DS_Server.SendState(identity);
	}

	override void OnMissionFinish()
	{
		if (m_DS_Server)
			m_DS_Server.SaveState();
		super.OnMissionFinish();
	}
}

modded class MissionGameplay
{
	protected ref DS_ClientController m_DS_Client;

	override void OnInit()
	{
		super.OnInit();
		if (DS_Util.IsSeasonalWorld())
			m_DS_Client = new DS_ClientController();
	}

	override void OnUpdate(float timeslice)
	{
		super.OnUpdate(timeslice);
		if (m_DS_Client)
			m_DS_Client.Update(timeslice);
	}

	override void OnMissionFinish()
	{
		if (m_DS_Client)
			m_DS_Client.Shutdown();
		super.OnMissionFinish();
	}
}

