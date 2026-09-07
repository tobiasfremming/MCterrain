// Eight-seed check for plant profiles. Run through unityMCP execute_code
// (CodeDom, C# 6) after refreshing assets. Edit the NAMES array.
//
// Per profile: grammar parse errors, termination (deriving two more
// iterations must not change the word), unmapped marker symbols, height and
// width range, minY (parts below the ground), triangle range, and the lean
// direction per seed (degrees, from the centroid of the upper half of the
// skeleton) which should scatter around the compass rather than repeat.
string[] NAMES = { "PodTreePlant" };
uint[] seeds = { 1, 2, 3, 7, 44, 901, 1965, 4242 };
var sb = new System.Text.StringBuilder();
foreach (var name in NAMES)
{
    var profile = UnityEditor.AssetDatabase.LoadAssetAtPath<PlantProfile>("Assets/TerrainGen/Config/Flora/" + name + ".asset");
    if (profile == null) { sb.AppendLine(name + ": missing"); continue; }
    if (!profile.grammar.IsValid) { sb.Append(name + ": GRAMMAR ERRORS:"); foreach (var e in profile.grammar.Errors) sb.Append(" | " + e); sb.AppendLine(); continue; }
    var g = profile.grammar.Grammar; int iters = profile.grammar.EffectiveIterations;
    var rw = new LSystems.LSystemRewriter { MaxModules = 250000 };
    float hMin = 1e9f, hMax = 0f, wMin = 1e9f, wMax = 0f, minY = 0f; int tMin = int.MaxValue, tMax = 0, bad = 0; string unmapped = "";
    var angles = new System.Text.StringBuilder();
    foreach (var seed in seeds)
    {
        var word = rw.Rewrite(g, iters, seed); int n0 = word.Count; bool trunc = rw.Truncated;
        if (n0 != rw.Rewrite(g, iters + 2, seed).Count || trunc) bad++;
        var skel = LSystems.TurtleInterpreter.Build(word, profile.turtle);
        foreach (var mk in skel.Markers) if (!profile.TryGetPart(mk.Symbol, out _) && unmapped.IndexOf(mk.Symbol) < 0) unmapped += mk.Symbol;
        Vector3 sum = Vector3.zero; int cnt = 0; float top = 0f;
        foreach (var nd in skel.Nodes) top = Mathf.Max(top, nd.Position.y);
        foreach (var nd in skel.Nodes) if (nd.Position.y > top * 0.5f) { sum += nd.Position; cnt++; }
        Vector3 c = cnt > 0 ? sum / cnt : Vector3.zero;
        float ang = Mathf.Atan2(c.z, c.x) * Mathf.Rad2Deg; if (ang < 0) ang += 360f;
        angles.Append(" " + Mathf.RoundToInt(ang));
        var mesh = PlantMeshBuilder.Build(skel, profile, PlantMeshLod.Lod0);
        int tris = (int)((mesh.GetIndexCount(0) + mesh.GetIndexCount(1)) / 3);
        float h = mesh.bounds.size.y, w = Mathf.Max(mesh.bounds.size.x, mesh.bounds.size.z);
        minY = Mathf.Min(minY, mesh.bounds.min.y);
        hMin = Mathf.Min(hMin, h); hMax = Mathf.Max(hMax, h); wMin = Mathf.Min(wMin, w); wMax = Mathf.Max(wMax, w);
        tMin = System.Math.Min(tMin, tris); tMax = System.Math.Max(tMax, tris);
        UnityEngine.Object.DestroyImmediate(mesh);
    }
    sb.AppendLine(name + ": iters=" + iters + " height " + hMin.ToString("F1") + ".." + hMax.ToString("F1")
        + " width " + wMin.ToString("F1") + ".." + wMax.ToString("F1") + " minY " + minY.ToString("F2")
        + " tris " + tMin + ".." + tMax + (bad > 0 ? " NOT-TERMINATED x" + bad : " ok")
        + (unmapped.Length > 0 ? " UNMAPPED " + unmapped : "") + " lean:" + angles);
}
return sb.ToString();
