//! Snow baked per model: the roof snow of a map model, sampled once at full detail on a copy of it standing alone and
//! joined into one model per snow stage (tools/bake_snow.py). Every placement of the model draws it as one object in the
//! model's own space, instead of sampling its roofs with rays and drawing them as many pieces
class SZ_BakedSnow
{
	protected static ref map<string, string> s_Index;

	//! the name of the baked models of a map model (its shape, lower case), "" when it has none
	static string Find(string shape)
	{
		if (!s_Index)
		{
			s_Index = new map<string, string>;
			SZ_BakedIndex.Fill(s_Index);
		}
		string name;
		if (s_Index.Find(shape, name))
			return name;
		return "";
	}

	static int Count()
	{
		if (!s_Index)
			Find("");
		return s_Index.Count();
	}
}
