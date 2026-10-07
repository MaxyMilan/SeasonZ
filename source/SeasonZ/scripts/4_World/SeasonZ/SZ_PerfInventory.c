//! On-demand local QA inventory. No normal update-path work; model counts are
//! resident objects, not culled renderer submissions or GPU triangle counts.
class SZ_PerfInventory
{
	static void Add(map<string, int> counts, Object obj)
	{
		if (!obj)
			return;
		string model = obj.GetShapeName();
		counts.Set(model, counts.Get(model) + 1);
	}
	static void Write(FileHandle file, string system, map<string, int> counts)
	{
		for (int i = 0; i < counts.Count(); i++)
			FPrintln(file, system + "," + counts.GetKey(i) + "," + counts.GetElement(i).ToString());
	}
}
