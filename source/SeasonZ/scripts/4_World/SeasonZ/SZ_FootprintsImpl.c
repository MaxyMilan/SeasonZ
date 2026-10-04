class SZ_Print
{
	Object m_Obj;
	float m_Time;
}

//! Client: footprints in the snow cover. Every footstep on snow leaves a print aligned to the ground; fresh snowfall
//! slowly fills old prints and they vanish when the snow melts. A print is a hollow with the boot's tread and the snow
//! pushed up around it (normal map and ambient occlusion; deep prints also raise the rim as geometry). Thin snow lies
//! in patches: footsteps only sound like snow and leave prints where the cover shows snow (SZ_SnowCarpet.CoversAt).
//! The boot sinks deeper from 9 cm.
class SZ_Footprints
{
	static const int MAX_PRINTS = 320;
	static const float MIN_CM = 2.0;
	static const float DEEP_CM = 9.0;
	static const string MODEL_DIR = "SeasonZ\\data\\prints\\ds_print_";
	//! height of the print's base plane above the snow cover (the cover floats a few centimetres over the terrain)
	static const float ABOVE_COVER = 0.018;
	//! snowfall fills a print: after FILL_HEAVY seconds at full snowfall, up to FILL_HEAVY + FILL_LIGHT in the lightest
	//! snowfall (a print of a few centimetres takes most of an hour to fill in a steady snowfall)
	static const float FILL_HEAVY = 600.0;
	static const float FILL_LIGHT = 3000.0;

	protected static ref array<ref SZ_Print> s_Prints;
	//! how far each print model reaches below its origin (binarising centres a model on its bounding box)
	protected static ref map<string, float> s_Lift;
	protected static float s_Clock;
	protected static float s_FillTimer;

	static int GetCount()
	{
		if (!s_Prints)
			return 0;
		return s_Prints.Count();
	}

	static vector Cross(vector a, vector b)
	{
		return Vector(a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]);
	}

	static void OnStep(DayZPlayerImplement player, bool left)
	{
		if (!player || !SZ_State.s_Valid)
			return;
		// sitting in a vehicle leaves no prints (they would push the prints of the walk out of the MAX_PRINTS kept)
		if (player.IsInVehicle())
			return;
		if (!s_Prints)
			s_Prints = new array<ref SZ_Print>;

		// only where the footstep itself sounded like snow
		SurfaceAnimationBone limb = SurfaceAnimationBone.RightBackLimb;
		string bone = "RightFoot";
		if (left)
		{
			limb = SurfaceAnimationBone.LeftBackLimb;
			bone = "LeftFoot";
		}
		if (player.GetSurfaceType(limb) != SZ_SnowGround.SNOW_SURFACE)
			return;

		vector pos = player.GetPosition();
		int boneIndex = player.GetBoneIndexByName(bone);
		if (boneIndex >= 0)
		{
			vector fp = player.GetBonePositionWS(boneIndex);
			pos[0] = fp[0];
			pos[2] = fp[2];
		}
		PlaceAt(pos, player.GetDirection(), left);
	}

	static void PlaceAt(vector pos, vector dir, bool left)
	{
		if (!s_Prints)
			s_Prints = new array<ref SZ_Print>;
		float ground = g_Game.SurfaceY(pos[0], pos[2]);
		float snow = SZ_State.SnowAt(ground, SZ_State.s_Snow0, SZ_State.s_Snow1, SZ_State.s_Snow2);
		if (snow < MIN_CM)
			return;
		string model = MODEL_DIR + "shallow_";
		if (snow >= DEEP_CM)
			model = MODEL_DIR + "deep_";
		if (left)
			model += "l.p3d";
		else
			model += "r.p3d";
		PlaceModel(model, pos, dir);
	}

	//! places one print model on the snow cover at pos, pointing along dir (also used by the test harness)
	static Object PlaceModel(string model, vector pos, vector dir)
	{
		if (!s_Prints)
			s_Prints = new array<ref SZ_Print>;
		if (!s_Lift)
			s_Lift = new map<string, float>;
		// just above the snow cover, which floats a few centimetres over the terrain and a little more over roads
		float cover = SZ_SnowCarpet.CoverHeightAt(pos[0], pos[2]);
		vector up = g_Game.SurfaceGetNormal(pos[0], pos[2]);
		// forward along the slope
		vector fwd = dir - up * vector.Dot(dir, up);
		if (fwd.Length() < 0.01)
			return null;
		fwd.Normalize();
		vector side = Cross(up, fwd);

		Object o = g_Game.CreateStaticObjectUsingP3D(model, Vector(pos[0], cover + ABOVE_COVER, pos[2]), "0 0 0", 1.0, true);
		if (!o)
			return null;
		float lift;
		if (!s_Lift.Find(model, lift))
		{
			vector box[2];
			o.ClippingInfo(box);
			lift = -box[0][1];
			s_Lift.Set(model, lift);
		}

		vector mat[4];
		mat[0] = side;
		mat[1] = up;
		mat[2] = fwd;
		mat[3] = Vector(pos[0], cover + ABOVE_COVER, pos[2]) + up * lift;
		o.SetTransform(mat);

		SZ_Print p = new SZ_Print();
		p.m_Obj = o;
		p.m_Time = s_Clock;
		s_Prints.Insert(p);
		while (s_Prints.Count() > MAX_PRINTS)
			RemoveAt(0);
		return o;
	}

	protected static void RemoveAt(int i)
	{
		SZ_Print p = s_Prints[i];
		if (p && p.m_Obj)
			g_Game.ObjectDelete(p.m_Obj);
		s_Prints.Remove(i);
	}

	//! fills prints during snowfall (oldest first) and removes them where the snow is gone
	static void Update(float timeslice, float s0, float s1, float s2)
	{
		s_Clock += timeslice;
		if (!s_Prints || s_Prints.Count() == 0)
			return;

		s_FillTimer += timeslice;
		if (s_FillTimer < 1.0)
			return;
		s_FillTimer = 0;

		float snowfall = g_Game.GetWeather().GetSnowfall().GetActual();
		if (snowfall > 0.05)
		{
			// heavy snowfall covers a print within minutes, light snow takes most of an hour
			float maxAge = FILL_HEAVY + FILL_LIGHT * (1.0 - Math.Clamp(snowfall, 0, 1));
			while (s_Prints.Count() > 0 && s_Clock - s_Prints[0].m_Time > maxAge)
				RemoveAt(0);
		}

		for (int i = s_Prints.Count() - 1; i >= 0; i--)
		{
			SZ_Print p = s_Prints[i];
			if (!p.m_Obj)
			{
				s_Prints.Remove(i);
				continue;
			}
			vector pp = p.m_Obj.GetPosition();
			if (SZ_State.SnowAt(pp[1], s0, s1, s2) < 0.8)
				RemoveAt(i);
		}
	}

	static void Clear()
	{
		if (!s_Prints)
			return;
		while (s_Prints.Count() > 0)
			RemoveAt(s_Prints.Count() - 1);
	}
}

