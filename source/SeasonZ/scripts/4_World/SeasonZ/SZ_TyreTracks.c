//! One side of a vehicle that lays a track: the wheel that lays it and where the next segment starts
class SZ_TrackSide
{
	int m_Wheel = -1;
	bool m_Has;
	vector m_Start;
}

class SZ_TrackCar
{
	CarScript m_Car;
	ref SZ_TrackSide m_Left;
	ref SZ_TrackSide m_Right;

	void SZ_TrackCar(CarScript car)
	{
		m_Car = car;
		m_Left = new SZ_TrackSide();
		m_Right = new SZ_TrackSide();
	}
}

//! Client: tyre tracks in the snow cover. Every vehicle near the camera that rolls over snow leaves a track behind the
//! rearmost wheel of each side (the front wheels run in the same ruts when driving straight). A track is made of 1 m
//! segments laid end to end along the wheel's path, so it follows bends; the rut, its tread and the snow pushed up
//! beside it run on from one segment into the next. Deep snow (9 cm and more) gives deep ruts with raised ridges.
//! Like footprints, tracks only form where the cover shows snow, fill during snowfall and vanish when the snow melts.
class SZ_TyreTracks
{
	static const int MAX_SEGMENTS = 1200;
	static const float SEGMENT = 1.0;
	static const float RANGE = 300.0;
	static const float MIN_CM = 2.0;
	static const float DEEP_CM = 9.0;
	//! a wheel more than this above the snow cover rolls on something else (a bridge, a floor)
	static const float ABOVE_LIMIT = 0.6;
	static const float ABOVE_COVER = 0.016;
	static const string MODEL_DIR = "SeasonZ\\data\\tracks\\sz_track_";

	protected static ref array<ref SZ_TrackCar> s_Cars;
	protected static ref array<ref SZ_Print> s_Segments;
	protected static ref map<string, float> s_Lift;
	protected static float s_Clock;
	protected static float s_FillTimer;

	static void Register(CarScript car)
	{
		if (!car)
			return;
		if (!s_Cars)
			s_Cars = new array<ref SZ_TrackCar>;
		foreach (SZ_TrackCar known : s_Cars)
		{
			if (known.m_Car == car)
				return;
		}
		s_Cars.Insert(new SZ_TrackCar(car));
	}

	static void Unregister(CarScript car)
	{
		if (!s_Cars)
			return;
		for (int i = s_Cars.Count() - 1; i >= 0; i--)
		{
			if (s_Cars[i].m_Car == car)
				s_Cars.Remove(i);
		}
	}

	static int GetCount()
	{
		if (!s_Segments)
			return 0;
		return s_Segments.Count();
	}

	static void Update(float timeslice, vector camera, float s0, float s1, float s2)
	{
		s_Clock += timeslice;
		if (!SZ_State.s_Valid)
			return;
		if (s_Cars && Math.Max(s0, Math.Max(s1, s2)) >= MIN_CM)
		{
			for (int i = s_Cars.Count() - 1; i >= 0; i--)
			{
				SZ_TrackCar tc = s_Cars[i];
				if (!tc.m_Car)
				{
					s_Cars.Remove(i);
					continue;
				}
				UpdateCar(tc, camera, s0, s1, s2);
			}
		}
		Fill(timeslice, s0, s1, s2);
	}

	protected static void UpdateCar(SZ_TrackCar tc, vector camera, float s0, float s1, float s2)
	{
		CarScript car = tc.m_Car;
		vector pos = car.GetPosition();
		if (vector.DistanceSq(pos, camera) > RANGE * RANGE)
		{
			tc.m_Left.m_Has = false;
			tc.m_Right.m_Has = false;
			return;
		}
		vector velocity = GetVelocity(car);
		if (velocity.LengthSq() < 0.01)
			return;

		// the rearmost wheel on the ground on each side
		int left = -1;
		int right = -1;
		float leftZ = 1000000.0;
		float rightZ = 1000000.0;
		int n = car.WheelCount();
		for (int w = 0; w < n; w++)
		{
			if (!car.WheelHasContact(w))
				continue;
			vector contact = car.WheelGetContactPosition(w);
			vector inCar = car.WorldToModel(contact);
			if (inCar[0] < 0)
			{
				if (inCar[2] < leftZ)
				{
					leftZ = inCar[2];
					left = w;
				}
			}
			else if (inCar[2] < rightZ)
			{
				rightZ = inCar[2];
				right = w;
			}
		}
		Follow(car, tc.m_Left, left, s0, s1, s2);
		Follow(car, tc.m_Right, right, s0, s1, s2);
	}

	//! lays the segments a wheel has rolled over since the last one
	protected static void Follow(CarScript car, SZ_TrackSide side, int wheel, float s0, float s1, float s2)
	{
		if (wheel < 0)
		{
			side.m_Has = false;
			return;
		}
		vector p = car.WheelGetContactPosition(wheel);
		if (!side.m_Has || side.m_Wheel != wheel)
		{
			side.m_Wheel = wheel;
			side.m_Has = true;
			side.m_Start = p;
			return;
		}
		float dx = p[0] - side.m_Start[0];
		float dz = p[2] - side.m_Start[2];
		float d = Math.Sqrt(dx * dx + dz * dz);
		// a jump (teleport, network catch-up): start again here
		if (d > SEGMENT * 6.0)
		{
			side.m_Start = p;
			return;
		}
		int guard = 0;
		while (d >= SEGMENT && guard < 6)
		{
			guard++;
			vector a = side.m_Start;
			vector b = Vector(a[0] + dx / d * SEGMENT, p[1], a[2] + dz / d * SEGMENT);
			PlaceSegment(a, b, p[1], s0, s1, s2);
			side.m_Start = b;
			dx = p[0] - b[0];
			dz = p[2] - b[2];
			d = Math.Sqrt(dx * dx + dz * dz);
		}
	}

	protected static void PlaceSegment(vector a, vector b, float wheelY, float s0, float s1, float s2)
	{
		vector c = (a + b) * 0.5;
		// only where the cover shows snow: thin snow lies in patches
		if (!SZ_SnowCarpet.CoversAt(c[0], c[2]))
			return;
		float ground = g_Game.SurfaceY(c[0], c[2]);
		float snow = SZ_State.SnowAt(ground, s0, s1, s2);
		if (snow < MIN_CM)
			return;
		float hc = SZ_SnowCarpet.CoverHeightAt(c[0], c[2]);
		if (wheelY > hc + ABOVE_LIMIT)
			return;
		float ha = SZ_SnowCarpet.CoverHeightAt(a[0], a[2]);
		float hb = SZ_SnowCarpet.CoverHeightAt(b[0], b[2]);
		vector flat = Vector(b[0] - a[0], 0, b[2] - a[2]);
		flat.Normalize();
		vector across = Vector(flat[2], 0, -flat[0]);
		float hl = SZ_SnowCarpet.CoverHeightAt(c[0] - across[0] * 0.25, c[2] - across[2] * 0.25);
		float hr = SZ_SnowCarpet.CoverHeightAt(c[0] + across[0] * 0.25, c[2] + across[2] * 0.25);

		// the segment lies along the cover: pitched between its ends, rolled across the rut
		vector fwd = Vector(b[0] - a[0], hb - ha, b[2] - a[2]);
		fwd.Normalize();
		vector span = Vector(across[0] * 0.5, hr - hl, across[2] * 0.5);
		vector up = SZ_Footprints.Cross(fwd, span);
		if (up[1] < 0)
			up = up * -1.0;
		up.Normalize();
		vector side = SZ_Footprints.Cross(up, fwd);
		side.Normalize();
		float centre = Math.Max(hc, 0.5 * (ha + hb));

		string model = MODEL_DIR + "shallow.p3d";
		if (snow >= DEEP_CM)
			model = MODEL_DIR + "deep.p3d";
		Object o = g_Game.CreateStaticObjectUsingP3D(model, Vector(c[0], centre + ABOVE_COVER, c[2]), "0 0 0", 1.0, true);
		if (!o)
			return;
		if (!s_Lift)
			s_Lift = new map<string, float>;
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
		mat[3] = Vector(c[0], centre + ABOVE_COVER, c[2]) + up * lift;
		o.SetTransform(mat);

		if (!s_Segments)
			s_Segments = new array<ref SZ_Print>;
		SZ_Print seg = new SZ_Print();
		seg.m_Obj = o;
		seg.m_Time = s_Clock;
		s_Segments.Insert(seg);
		while (s_Segments.Count() > MAX_SEGMENTS)
			RemoveAt(0);
	}

	protected static void RemoveAt(int i)
	{
		SZ_Print seg = s_Segments[i];
		if (seg && seg.m_Obj)
			g_Game.ObjectDelete(seg.m_Obj);
		s_Segments.RemoveOrdered(i);
	}

	//! fills tracks during snowfall (oldest first) and removes them where the snow is gone
	protected static void Fill(float timeslice, float s0, float s1, float s2)
	{
		if (!s_Segments || s_Segments.Count() == 0)
		{
			s_FillTimer = 0;
			return;
		}
		s_FillTimer += timeslice;
		if (s_FillTimer < 1.0)
			return;
		float fillSeconds = s_FillTimer;
		s_FillTimer = 0;

		float snowfall = g_Game.GetWeather().GetSnowfall().GetActual();
		float fillStep = 0;
		if (snowfall > 0.05)
			fillStep = fillSeconds / (120.0 + 900.0 * (1.0 - Math.Clamp(snowfall, 0, 1)));

		for (int i = s_Segments.Count() - 1; i >= 0; i--)
		{
			SZ_Print seg = s_Segments[i];
			if (!seg.m_Obj)
			{
				s_Segments.RemoveOrdered(i);
				continue;
			}
			// A mark born within this fill interval did not see the earlier part of it.
			seg.m_Fill += fillStep * Math.Clamp((s_Clock - seg.m_Time) / fillSeconds, 0, 1);
			vector sp = seg.m_Obj.GetPosition();
			if (seg.m_Fill >= 1.0 || SZ_State.SnowAt(sp[1], s0, s1, s2) < 0.8)
				RemoveAt(i);
		}
	}

	static void Clear()
	{
		s_FillTimer = 0;
		if (!s_Segments)
			return;
		while (s_Segments.Count() > 0)
			RemoveAt(s_Segments.Count() - 1);
	}
}
