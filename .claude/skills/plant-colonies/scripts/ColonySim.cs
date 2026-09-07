// Offline colony simulator: the real L-system rewriter (TerrainGen.LSystem.dll)
// with a 2D turtle of its own, a flat 24 m plot grid, the 3x3 neighbour walk,
// the spacing rule and a cover mask. Prints termination stats and writes
// "letter x z spacing" per placed plant for a map render.
//
// args: <grammar.txt> <iterations> <letters:spacing,...> <colonyChance> <out.txt> [seed]
using System;
using System.Collections.Generic;
using System.IO;
using LSystems;

static class Program
{
    struct Cand { public char sym; public float x, z, scale, spacing, cover; public int order; }

    static uint Hash(uint a, uint b, uint seed)
    {
        uint h = seed ^ 0x9E3779B9u; h ^= a * 0x85EBCA6Bu; h = (h ^ (h >> 13)) * 0xC2B2AE35u; h ^= b * 0x27D4EB2Fu; h = (h ^ (h >> 16)) * 0x165667B1u; return h ^ (h >> 15);
    }
    static float Val(int ix, int iz, uint seed) => (Hash((uint)ix, (uint)iz, seed) & 0xFFFFFF) / 16777215f * 2f - 1f;
    static float Noise(float x, float z, uint seed)
    {
        int ix = (int)Math.Floor(x), iz = (int)Math.Floor(z); float fx = x - ix, fz = z - iz;
        fx = fx * fx * (3 - 2 * fx); fz = fz * fz * (3 - 2 * fz);
        float a = Val(ix, iz, seed), b = Val(ix + 1, iz, seed), c = Val(ix, iz + 1, seed), d = Val(ix + 1, iz + 1, seed);
        return (a + (b - a) * fx) + ((c + (d - c) * fx) - (a + (b - a) * fx)) * fz;
    }
    static float Fbm(float x, float z, uint seed) { float s = 0, amp = 1f, f = 1, norm = 0; for (int o = 0; o < 3; o++) { norm += amp; s += amp * Noise(x * f + o * 19.19f, z * f - o * 7.77f, seed + (uint)o * 131); amp *= 0.5f; f *= 2f; } return s / norm; }
    static float Cover(float x, float z, float scale, float th, float soft, uint seed)
    {
        float v = Fbm(x / scale + 31.7f, z / scale - 11.3f, seed);
        float t = Math.Clamp((v - (th - soft)) / (2f * soft), 0f, 1f); return t * t * (3 - 2 * t);
    }

    // 2D turtle: + - yaw, f move, [ ] stack; markers = any other symbol.
    static void Walk(LModuleString word, List<(char, float, float, float)> markers)
    {
        var stack = new Stack<(float, float, float)>();
        float x = 0, z = 0, ang = 0;
        for (int i = 0; i < word.Count; i++)
        {
            LModule m = word[i]; float p0 = m.ParamCount > 0 ? word.GetParam(i, 0) : float.NaN;
            switch (m.Symbol)
            {
                case '+': ang += float.IsNaN(p0) ? 90f : p0; break;
                case '-': ang -= float.IsNaN(p0) ? 90f : p0; break;
                case 'f': case 'F': { float l = float.IsNaN(p0) ? 1f : p0; x += (float)Math.Sin(ang * Math.PI / 180) * l; z += (float)Math.Cos(ang * Math.PI / 180) * l; break; }
                case '[': stack.Push((x, z, ang)); break;
                case ']': if (stack.Count > 0) (x, z, ang) = stack.Pop(); break;
                case '&': case '^': case '/': case '\\': case '$': case '!': case '|': case 'g': case 'G': Console.WriteLine("WARNING: out-of-plane symbol " + m.Symbol); break;
                default: markers.Add((m.Symbol, x, z, float.IsNaN(p0) ? 1f : p0)); break;
            }
        }
    }

    static int Main(string[] args)
    {
        string text = File.ReadAllText(args[0]); int iters = int.Parse(args[1]);
        var spacing = new Dictionary<char, float>();
        foreach (var kv in args[2].Split(',')) { var p = kv.Split(':'); spacing[p[0][0]] = float.Parse(p[1], System.Globalization.CultureInfo.InvariantCulture); }
        float chance = float.Parse(args[3], System.Globalization.CultureInfo.InvariantCulture);
        string outPath = args[4]; uint worldSeed = args.Length > 5 ? uint.Parse(args[5]) : 5150u;
        var ci = System.Globalization.CultureInfo.InvariantCulture;
        float cScale = args.Length > 6 ? float.Parse(args[6], ci) : 140f, cTh = args.Length > 7 ? float.Parse(args[7], ci) : 0f, cSoft = args.Length > 8 ? float.Parse(args[8], ci) : 0.3f;

        if (!LSystemParser.TryParse(text, out LSystemGrammar g, out var errs)) { foreach (var e in errs) Console.WriteLine("PARSE " + e); return 1; }
        var rw = new LSystemRewriter { MaxModules = 20000 };

        // termination + marker stats over 60 seeds
        int bad = 0, minM = int.MaxValue, maxM = 0; float reach = 0; var letters = new HashSet<char>(); double sumM = 0;
        var mk = new List<(char, float, float, float)>();
        for (uint s = 1; s <= 60; s++)
        {
            var w = rw.Rewrite(g, iters, s); int n0 = w.Count; bool tr = rw.Truncated;
            var w2 = rw.Rewrite(g, iters + 2, s); if (w2.Count != n0 || tr) bad++;
            mk.Clear(); Walk(rw.Rewrite(g, iters, s), mk);
            minM = Math.Min(minM, mk.Count); maxM = Math.Max(maxM, mk.Count); sumM += mk.Count;
            foreach (var t in mk) { reach = Math.Max(reach, (float)Math.Sqrt(t.Item2 * t.Item2 + t.Item3 * t.Item3)); letters.Add(t.Item1); if (!spacing.ContainsKey(t.Item1)) Console.WriteLine("WARNING: letter '" + t.Item1 + "' has no species"); }
        }
        Console.WriteLine("iters=" + iters + " markers " + minM + ".." + maxM + " mean " + (sumM / 60).ToString("F1") + " reach " + reach.ToString("F1") + " m letters=" + string.Concat(letters) + (bad > 0 ? " NOT-TERMINATED x" + bad : " ok"));

        // flat plot grid simulation
        const float size = 24f; const int N = 14;
        var cands = new List<Cand>(); var accepted = new List<Cand>(); var placed = new List<Cand>();
        int candTotal = 0, glade = 0, spaced = 0;
        for (int a = 0; a < N; a++) for (int b = 0; b < N; b++)
        {
            cands.Clear(); accepted.Clear();
            for (int da = -1; da <= 1; da++) for (int db = -1; db <= 1; db++)
            {
                int na = a + da, nb = b + db;
                uint plotHash = Hash(unchecked((uint)(0x7F * 73856093 + na)), (uint)nb, worldSeed);
                var rng = new LRandom(plotHash, 0x51ED27u + 0x9E3779B9u);
                if (rng.NextFloat() > chance) continue;
                float fa = rng.NextFloat(), fb = rng.NextFloat(); uint cs = rng.NextUInt();
                mk.Clear(); Walk(rw.Rewrite(g, iters, cs), mk);
                foreach (var t in mk)
                {
                    float pick = rng.NextFloat(), yaw = rng.NextFloat(), acc = rng.NextFloat(), cov = rng.NextFloat();
                    float x = (na + fa) * size + t.Item2, z = (nb + fb) * size + t.Item3;
                    if ((int)Math.Floor(x / size) != a || (int)Math.Floor(z / size) != b) continue;
                    if (!spacing.TryGetValue(t.Item1, out float sp)) continue;
                    cands.Add(new Cand { sym = t.Item1, x = x, z = z, scale = t.Item4, spacing = sp, cover = cov, order = cands.Count });
                }
            }
            cands.Sort((p, q) => { int c = q.spacing.CompareTo(p.spacing); return c != 0 ? c : p.order.CompareTo(q.order); });
            foreach (var c in cands)
            {
                candTotal++;
                if (c.cover > Cover(c.x, c.z, cScale, cTh, cSoft, unchecked(worldSeed * 2654435761u + 0xC0FEu))) { glade++; continue; }
                bool blocked = false;
                foreach (var o in accepted) { float need = Math.Min(c.spacing, o.spacing); float dx = c.x - o.x, dz = c.z - o.z; if (dx * dx + dz * dz < need * need) { blocked = true; break; } }
                if (blocked) { spaced++; continue; }
                accepted.Add(c);
            }
            placed.AddRange(accepted);
        }
        Console.WriteLine("grid " + N + "x" + N + " plots: candidates " + candTotal + ", glade-rejected " + glade + ", spacing-rejected " + spaced + ", placed " + placed.Count + " (" + (placed.Count / (float)(N * N)).ToString("F1") + " per plot)");
        using (var sw = new StreamWriter(outPath))
            foreach (var c in placed) sw.WriteLine(c.sym + " " + c.x.ToString("F1", System.Globalization.CultureInfo.InvariantCulture) + " " + c.z.ToString("F1", System.Globalization.CultureInfo.InvariantCulture) + " " + c.spacing.ToString("F1", System.Globalization.CultureInfo.InvariantCulture));
        return 0;
    }
}
