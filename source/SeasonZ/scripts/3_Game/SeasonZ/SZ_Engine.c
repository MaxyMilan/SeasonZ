//! Client side season colour grading
class PPERequester_SeasonZ extends PPERequester_GameplayBase
{
	protected float m_SZ_Sat = -1;
	protected float m_SZ_R = -1;
	protected float m_SZ_G = -1;
	protected float m_SZ_B = -1;

	void SZ_SetGrade(float saturation, float subR, float subG, float subB)
	{
		if (Math.AbsFloat(saturation - m_SZ_Sat) < 0.002 && Math.AbsFloat(subR - m_SZ_R) < 0.002 && Math.AbsFloat(subG - m_SZ_G) < 0.002 && Math.AbsFloat(subB - m_SZ_B) < 0.002)
			return;

		m_SZ_Sat = saturation;
		m_SZ_R = subR;
		m_SZ_G = subG;
		m_SZ_B = subB;

		array<float> color = new array<float>;
		color.Insert(subR);
		color.Insert(subG);
		color.Insert(subB);
		color.Insert(0.0);

		SetTargetValueFloat(PostProcessEffectType.Glow, PPEGlow.PARAM_SATURATION, false, saturation, 40, PPOperators.MULTIPLICATIVE);
		SetTargetValueColor(PostProcessEffectType.Glow, PPEGlow.PARAM_COLORIZATIONCOLOR, color, 40, PPOperators.SUBSTRACT);
	}
}

modded class PPERequesterRegistrations
{
	override protected void RegisterAdditionalRequesters()
	{
		super.RegisterAdditionalRequesters();
		PPERequesterBank.RegisterRequester(PPERequester_SeasonZ);
	}
}

//! receives the season state on clients
modded class DayZGame
{
	override void OnRPC(PlayerIdentity sender, Object target, int rpc_type, ParamsReadContext ctx)
	{
		if (rpc_type == SZ_Const.RPC_STATE && !target)
		{
			Param8<float, float, float, float, float, float, float, float> data = new Param8<float, float, float, float, float, float, float, float>(0, 0, 0, 0, 0, 0, 0, 0);
			if (ctx.Read(data))
			{
				SZ_State.s_DayOfYear = data.param1;
				SZ_State.s_Snow0 = data.param2;
				SZ_State.s_Snow1 = data.param3;
				SZ_State.s_Snow2 = data.param4;
				SZ_State.s_TempAnomaly = data.param5;
				SZ_State.s_Ice0 = data.param6;
				SZ_State.s_Ice1 = data.param7;
				SZ_State.s_Ice2 = data.param8;
				SZ_State.s_Valid = true;
			}
			return;
		}

		super.OnRPC(sender, target, rpc_type, ctx);
	}
}

//! vanilla re-applies the base lighting on some events; the client controller re-applies the season lighting afterwards
modded class WorldLighting
{
	override void SetGlobalLighting(int lightingID)
	{
		super.SetGlobalLighting(lightingID);
		SZ_State.s_LightingDirty = true;
	}
}

