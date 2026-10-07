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
			if (IsServer())
				return;
			Param4<int, string, ref array<float>, ref array<int>> data = new Param4<int, string, ref array<float>, ref array<int>>(0, "", null, null);
			if (!ctx.Read(data) || !data.param3)
				return;
			string world;
			GetWorldName(world);
			world.ToLower();
			if (data.param2 != world || !SZ_PondProtocol.Valid(data.param1, data.param2, data.param4))
				return;
			array<float> v = data.param3;
			array<int> carry = data.param4;
			if (v.Count() != 9 || v[0] != 2.0)
				return;
			if (!(v[1] >= 0 && v[1] < 365) || !SZ_PersistentState.InRange(v[5], -100, 100))
				return;
			if (!SZ_PersistentState.InRange(v[2], 0, 1000) || !SZ_PersistentState.InRange(v[3], 0, 1000) || !SZ_PersistentState.InRange(v[4], 0, 1000))
				return;
			if (!SZ_PersistentState.InRange(v[6], 0, 10000) || !SZ_PersistentState.InRange(v[7], 0, 10000) || !SZ_PersistentState.InRange(v[8], 0, 10000))
				return;
			bool changed = SZ_State.s_PondWorld != world || !SZ_State.s_PondCarry || SZ_State.s_PondCarry.Count() != carry.Count();
			bool hasCarry = false;
			for (int pi = 0; pi < carry.Count(); pi++)
			{
				if (carry[pi] != 0 && carry[pi] != 1)
					return;
				if (carry[pi] == 1)
					hasCarry = true;
				if (!changed && SZ_State.s_PondCarry[pi] != carry[pi])
					changed = true;
			}
			SZ_State.s_DayOfYear = v[1];
			SZ_State.s_Snow0 = v[2];
			SZ_State.s_Snow1 = v[3];
			SZ_State.s_Snow2 = v[4];
			SZ_State.s_TempAnomaly = v[5];
			SZ_State.s_Ice0 = v[6];
			SZ_State.s_Ice1 = v[7];
			SZ_State.s_Ice2 = v[8];
			SZ_State.s_PondCarry = carry;
			SZ_State.s_HasPondCarry = hasCarry;
			SZ_State.s_PondWorld = world;
			if (changed)
				SZ_State.s_PondRevision++;
			SZ_State.s_Valid = true;
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

