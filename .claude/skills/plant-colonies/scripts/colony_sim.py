"""Offline colony placement simulator.

Compiles ColonySim.cs against the project's TerrainGen.LSystem.dll (the real
parser and rewriter) with the dotnet SDK's Roslyn, runs it, and renders a map.

    python colony_sim.py --biome DolomiteBiome [--out map.png]
    python colony_sim.py --grammar my.lsys --letters "T:4,m:0.8,a:1.8" \
        [--iterations 22] [--chance 0.45] [--scale 140] [--threshold 0.05] [--softness 0.25]

--biome reads the Biome asset: its flora list (symbol, minSpacing), the colony
grammar asset it references (source + iterations) and the cover settings.
Prints termination stats and the per-plot density; the map goes next to the
grammar (or to --out).
"""
import argparse, glob, json, os, re, shutil, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
CONFIG = os.path.join(ROOT, "Assets", "TerrainGen", "Config")


def unity_data():
    version = open(os.path.join(ROOT, "ProjectSettings", "ProjectVersion.txt")).read().split()[1]
    return os.path.join(r"C:\Program Files\Unity\Hub\Editor", version, "Editor", "Data")


def build(work):
    data = unity_data()
    refs = glob.glob(os.path.join(data, "Managed", "UnityEngine", "UnityEngine*.dll"))
    refs.append(os.path.join(data, "NetStandard", "ref", "2.1.0", "netstandard.dll"))
    lsys = os.path.join(ROOT, "Library", "ScriptAssemblies", "TerrainGen.LSystem.dll")
    if not os.path.exists(lsys):
        sys.exit("TerrainGen.LSystem.dll not built yet; open the project in the Editor once")
    refs.append(lsys)
    cscs = sorted(glob.glob(r"C:\Program Files\dotnet\sdk\*\Roslyn\bincore\csc.dll"))
    if not cscs:
        sys.exit("no dotnet SDK with Roslyn found")
    exe = os.path.join(work, "ColonySim.dll")
    src = os.path.join(HERE, "ColonySim.cs")
    if os.path.exists(exe) and os.path.getmtime(exe) > max(os.path.getmtime(src), os.path.getmtime(lsys)):
        return exe
    rsp = os.path.join(work, "build.rsp")
    with open(rsp, "w") as f:
        f.write('-nologo -target:exe -langversion:latest -nowarn:CS1701,CS1702 -out:"%s"\n' % exe)
        for r in refs:
            f.write('-r:"%s"\n' % r)
        f.write('"%s"\n' % src)
    p = subprocess.run(["dotnet", "exec", cscs[-1], "@" + rsp], capture_output=True, text=True)
    if p.returncode != 0:
        print(p.stdout, p.stderr)
        sys.exit("compile failed")
    json.dump({"runtimeOptions": {"tfm": "net9.0", "framework": {"name": "Microsoft.NETCore.App", "version": "9.0.0"}}},
              open(os.path.join(work, "ColonySim.runtimeconfig.json"), "w"))
    for r in refs:
        if "ScriptAssemblies" in r or "CoreModule" in r:
            shutil.copy(r, work)
    return exe


def yaml_scalar(s):
    # single-quoted YAML scalar as written by plant_assets.yaml_source
    body = s.strip()[1:-1]
    return body.replace("\n\n    ", "\n").replace("\n    ", " ").replace("''", "'")


def read_biome(name):
    path = os.path.join(CONFIG, name + ".asset")
    s = open(path, encoding="utf-8").read()
    letters = {}
    for m in re.finditer(r"  - label: (\w+)\n(.*?)(?=\n  - label: |\n  colony:|\Z)", s, re.S):
        block = m.group(2)
        sym = re.search(r"symbol: (\S*)", block)
        sp = re.search(r"minSpacing: ([\d.]+)", block)
        en = re.search(r"enabled: (\d)", block)
        if sym and sym.group(1) and sp and (not en or en.group(1) == "1"):
            letters[sym.group(1)] = (m.group(1), float(sp.group(1)))
    g = re.search(r"colony: \{fileID: 11400000, guid: ([0-9a-f]{32})", s)
    if not g:
        sys.exit(name + " has no colony grammar")
    gpath = None
    for meta in glob.glob(os.path.join(CONFIG, "**", "*.asset.meta"), recursive=True):
        if ("guid: " + g.group(1)) in open(meta, encoding="utf-8").read():
            gpath = meta[:-5]
            break
    if not gpath:
        sys.exit("grammar asset for guid " + g.group(1) + " not found")
    gs = open(gpath, encoding="utf-8").read()
    src = yaml_scalar(re.search(r"\n  source: ('.*?')\n  iterations:", gs, re.S).group(1))
    iters = int(re.search(r"\n  iterations: (\d+)", gs).group(1))
    m = re.search(r"#iterations:\s*(\d+)", src)
    if m:
        iters = int(m.group(1))

    def num(key, default):
        mm = re.search(r"\n  %s: ([\d.\-]+)" % key, s)
        return float(mm.group(1)) if mm else default
    settings = (num("colonyChance", 0.6), num("coverScale", 140), num("coverThreshold", 0), num("coverSoftness", 0.3))
    return src, iters, letters, settings, os.path.basename(gpath)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--biome")
    ap.add_argument("--grammar")
    ap.add_argument("--letters", default="", help="letter:spacing,... (a letter with no species is ignored)")
    ap.add_argument("--iterations", type=int)
    ap.add_argument("--chance", type=float, default=0.45)
    ap.add_argument("--scale", type=float, default=140)
    ap.add_argument("--threshold", type=float, default=0.05)
    ap.add_argument("--softness", type=float, default=0.25)
    ap.add_argument("--seed", type=int, default=5150)
    ap.add_argument("--out")
    a = ap.parse_args()

    work = os.path.join(os.environ.get("TEMP", HERE), "colonysim")
    os.makedirs(work, exist_ok=True)
    names = {}
    if a.biome:
        src, iters, letters, (chance, scale, th, soft), gname = read_biome(a.biome)
        spacing = ",".join("%s:%s" % (l, sp) for l, (n, sp) in letters.items())
        names = {l: n.replace("Plant", "") for l, (n, sp) in letters.items()}
        title = a.biome + " (" + gname + ")"
        gpath = os.path.join(work, a.biome + ".lsys")
        open(gpath, "w", encoding="utf-8").write(src)
    else:
        if not a.grammar:
            sys.exit("--biome or --grammar")
        gpath = a.grammar
        src = open(gpath, encoding="utf-8").read()
        m = re.search(r"#iterations:\s*(\d+)", src)
        iters = a.iterations or (int(m.group(1)) if m else 12)
        spacing = a.letters
        chance, scale, th, soft = a.chance, a.scale, a.threshold, a.softness
        title = os.path.basename(gpath)
    if not spacing:
        sys.exit("no letters: every species needs a symbol")

    exe = build(work)
    out = os.path.join(work, "placed.txt")
    r = subprocess.run(["dotnet", exe, gpath, str(iters), spacing, str(chance), out, str(a.seed), str(scale), str(th), str(soft)],
                       capture_output=True, text=True)
    print(r.stdout.strip())
    if r.stderr.strip():
        print(r.stderr.strip()[:600])
    if r.returncode != 0 or not os.path.exists(out):
        sys.exit(1)

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    pts = [l.split() for l in open(out)]
    fig, ax = plt.subplots(figsize=(9, 9))
    cmap = plt.get_cmap("tab20")
    for i, l in enumerate(sorted(set(p[0] for p in pts))):
        xs = [float(p[1]) for p in pts if p[0] == l]
        zs = [float(p[2]) for p in pts if p[0] == l]
        s = [min(400, max(6, (float(p[3]) * 3) ** 2)) for p in pts if p[0] == l]
        ax.scatter(xs, zs, s=s, color=cmap(i % 20), alpha=0.8, edgecolors="none",
                   label="%s %s (%d)" % (l, names.get(l, ""), len(xs)))
    for k in range(15):
        ax.axhline(k * 24, color="#ddd", lw=0.4)
        ax.axvline(k * 24, color="#ddd", lw=0.4)
    ax.set_xlim(0, 14 * 24); ax.set_ylim(0, 14 * 24); ax.set_aspect("equal")
    ax.set_title(title + ": 14x14 plots of 24 m, chance %.2f, cover %.0f m / %.2f / %.2f" % (chance, scale, th, soft))
    ax.legend(fontsize=7, loc="upper left", bbox_to_anchor=(1.01, 1))
    fig.tight_layout()
    png = a.out or os.path.splitext(gpath)[0] + "_map.png"
    fig.savefig(png, dpi=80)
    print("map:", png)


if __name__ == "__main__":
    main()
