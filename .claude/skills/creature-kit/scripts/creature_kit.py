#!/usr/bin/env python3
"""Creature kit driver: the offline harness in Assets/TerrainGen/Tools~/CreatureHarness, from the command line.

  creature_kit.py check <Species> [...]      the generic kit (CreatureKitTests) for these species assets
  creature_kit.py test [Class|filter ...]    any harness tests ("CreatureLegTests", "Class.Method", substring)
  creature_kit.py list [filter ...]          the tests the harness would run
  creature_kit.py species                    the species assets the kit discovers (bones, Validate, unknown keys)
  creature_kit.py catalogue [--write]        Config/Creatures/CATALOGUE.md + catalogue.json: fresh or STALE (exit 1),
                                             or regenerate them (the same bytes as the Unity menu)
  creature_kit.py kit-convert <Species> <NewName>
                                             write Config/Creatures/<NewName>.asset: a legacy species as kit parts +
                                             modules (kitVersion 1, mirror/pattern sugar); prove it golden-equal
                                             before replacing the original (design decision 4)
  creature_kit.py unity-compile              compile Scripts + Tests/EditMode against the real Unity DLLs
                                             (C# 9, NUnit, TestRunner): the gate before an Editor visit
  creature_kit.py new <Species> --from <Species|archetype> [--gen-dir DIR]
                                             scaffold Config/Creatures/<Species>.asset (+ .meta, fresh guid) from a
                                             shipped species (a legacy one is kit-converted first) or an archetype
                                             sketch (arthropod.spider, arthropod.crab: every plan number 0 = form
                                             default), and its generator <gen-dir>/<Species>.py (default Tools~/
                                             SpeciesGen) that rebuilds the asset with kityaml - edit, run, check
  creature_kit.py render <Species> [--phase P,Q] [--out DIR] [--views side,front34,top] [--seconds S]
                                             the look loop: the skinned mesh at each phase its own brain reaches
                                             (pose-dump: launch, glide, touchdown, dive, curled, walk ...; every phase
                                             seen when none named) drawn by Tools~/CreatureLook/render.py into
                                             <out>/<Species>.png (one row per phase) next to the OBJ files
  creature_kit.py stats <Species>            gait and stance numbers: speed (m/s, Froude), steps/s, duty, lift / L,
                                             step time (Froude), bob, rest reach share + IK s / pitch per leg, mesh
                                             size and build time, tick cost, the phases it reaches, the sweep's verdict
  creature_kit.py trace <Species> [--phase P] [--part ID] [--out f.csv] [--seconds S]
                                             the bone trace: a CSV row per tick of its own run (every phase): spine
                                             bends, the part's bones (position, forward, up, scale, det < 0 mirrored)
  creature_kit.py yaml-selftest              every asset round-trips through kityaml (load -> dump, and through a
                                             generated generator) byte for byte

Options (any command):
  --tg <path>       the TerrainGen tree to use (default: the one containing the cwd, else
                    <repo>/Assets/TerrainGen). Use it for a worktree: --tg ../wt/kit/Assets/TerrainGen
  --real-unity      build against the real 6000.2.6f2 UnityEngine.CoreModule.dll (math parity; tests that
                    reach engine-side code - ScriptableObject, Mesh - report NATIVE instead of running)
  -v                print every test's output, not only the failing ones
  --exclude-category <C>   skip tests in category C (e.g. Perf)
  --no-build        run the last build

Exit code: the harness's (number of failures; 0 = green), or the build's.
Offline results are not Unity results: .NET 8 MathF rounds differently from Mono (goldens differ; long or
chaotic runs can drift, see kKnownOffline in Program.cs). Unity runs once per finished feature.
"""
import argparse
import glob
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kityaml  # noqa: E402

HARNESS_REL = os.path.join("Tools~", "CreatureHarness")


def repo_root():
    here = os.path.abspath(os.path.dirname(__file__))
    for _ in range(6):
        if os.path.isdir(os.path.join(here, "ProjectSettings")):
            return here
        here = os.path.dirname(here)
    return None


def find_tg(arg):
    if arg:
        tg = os.path.abspath(arg)
    else:
        tg = None
        d = os.getcwd()
        while True:
            if os.path.isdir(os.path.join(d, "Scripts", "Creatures")) and os.path.isdir(os.path.join(d, "Config")):
                tg = d
                break
            cand = os.path.join(d, "Assets", "TerrainGen")
            if os.path.isdir(os.path.join(cand, "Scripts", "Creatures")):
                tg = cand
                break
            p = os.path.dirname(d)
            if p == d:
                break
            d = p
        if tg is None:
            root = repo_root()
            tg = os.path.join(root, "Assets", "TerrainGen") if root else None
    if not tg or not os.path.isdir(os.path.join(tg, "Scripts", "Creatures")):
        sys.exit(f"no TerrainGen tree at {tg} (use --tg)")
    return tg


def harness_dir(tg):
    h = os.path.join(tg, HARNESS_REL)
    if not os.path.isfile(os.path.join(h, "CreatureHarness.csproj")):
        sys.exit(f"{tg} has no {HARNESS_REL} (branch before the creature kit?)")
    return h


def build(tg, real):
    h = harness_dir(tg)
    cmd = ["dotnet", "build", "-c", "Release", "-nologo", "-v", "q"]
    if real:
        cmd.append("-p:RealUnity=true")
    proc = subprocess.run(cmd, cwd=h, capture_output=True, text=True)
    out = proc.stdout + proc.stderr
    errors = sorted(set(re.sub(r"\s*\[[^\]]*\.csproj\]\s*$", "", l).strip() for l in out.splitlines() if ": error " in l))
    for e in errors[:40]:
        print(e)
    if proc.returncode != 0:
        print(f"BUILD FAILED ({len(errors)} errors)")
        sys.exit(proc.returncode or 1)
    return os.path.join(h, "bin", "RealUnity" if real else "Release", "net8.0", "CreatureHarness.dll")


def run(tg, real, args, no_build):
    dll = os.path.join(harness_dir(tg), "bin", "RealUnity" if real else "Release", "net8.0", "CreatureHarness.dll")
    if not no_build:
        dll = build(tg, real)
    env = dict(os.environ, CREATURE_HARNESS_TG=tg)
    return subprocess.call(["dotnet", dll] + args, env=env)


# ---------------------------------------------------------------- unity-compile

def unity_compile(tg):
    project = os.path.dirname(os.path.dirname(tg))   # <project>/Assets/TerrainGen
    ver_file = os.path.join(project, "ProjectSettings", "ProjectVersion.txt")
    if not os.path.isfile(ver_file):
        sys.exit(f"{project} is not a Unity project root (worktrees need the ProjectSettings junction)")
    version = re.search(r"m_EditorVersion:\s*(\S+)", open(ver_file, encoding="utf-8").read()).group(1)
    data = os.path.join(r"C:\Program Files\Unity\Hub\Editor", version, "Editor", "Data")
    if not os.path.isdir(data):
        sys.exit(f"Unity {version} not found at {data}")
    lib = os.path.join(project, "Library", "ScriptAssemblies")
    refs = glob.glob(os.path.join(data, "Managed", "UnityEngine", "UnityEngine*.dll"))
    refs += glob.glob(os.path.join(data, "Managed", "UnityEngine", "UnityEditor*.dll"))
    # Managed/UnityEditor.dll duplicates UnityEditor.CoreModule's types (CS0433 on AssetDatabase): modules only
    refs.append(os.path.join(data, "NetStandard", "ref", "2.1.0", "netstandard.dll"))
    # NUnit is a net40 assembly: its System.Attribute lives in mscorlib, forwarded by Unity's facade
    refs.append(os.path.join(data, "NetStandard", "compat", "2.1.0", "shims", "netfx", "mscorlib.dll"))
    for name in ("TerrainGen.LSystem", "Unity.RenderPipelines.Universal.Runtime", "Unity.RenderPipelines.Core.Runtime",
                 "Unity.InputSystem", "Unity.Mathematics", "Unity.Burst", "Unity.Collections", "UnityEngine.TestRunner",
                 "UnityEditor.TestRunner", "Unity.AI.Navigation", "Unity.PerformanceTesting"):
        p = os.path.join(lib, name + ".dll")
        if os.path.exists(p):
            refs.append(p)
    # a worktree's fake project root junctions only Library/ScriptAssemblies: look in the main project too
    libs = [os.path.join(project, "Library")] + ([os.path.join(repo_root(), "Library")] if repo_root() else [])
    nunit = [n for l in libs for n in glob.glob(os.path.join(l, "PackageCache", "com.unity.ext.nunit*", "net40", "unity-custom", "nunit.framework.dll"))]
    if not nunit:
        sys.exit("nunit.framework.dll not found under Library/PackageCache (open the project in Unity once)")
    refs.append(nunit[0])
    srcs = [p for p in glob.glob(os.path.join(tg, "Scripts", "**", "*.cs"), recursive=True)
            if os.sep + "LSystem" + os.sep not in p]
    srcs += glob.glob(os.path.join(tg, "Tests", "EditMode", "*.cs"))
    out_dir = os.path.join(project, "Library", "ClaudeCompileCheck")
    os.makedirs(out_dir, exist_ok=True)
    rsp = os.path.join(out_dir, "kit_tests.rsp")
    lines = [f'/r:"{r}"' for r in refs] + [f'"{s}"' for s in srcs]
    lines.append(f'/nologo /target:library /out:"{os.path.join(out_dir, "kit_tests.dll")}" '
                 '/nowarn:CS0618,CS0649,CS0414,CS0168,CS0219,CS0108,CS0162,CS0436 /langversion:9 '
                 '/define:UNITY_6000_0_OR_NEWER;UNITY_2022_1_OR_NEWER;UNITY_EDITOR;UNITY_INCLUDE_TESTS')
    open(rsp, "w", encoding="utf-8").write("\n".join(lines))
    sdks = sorted(glob.glob(os.path.join(r"C:\Program Files\dotnet\sdk", "*", "Roslyn", "bincore", "csc.dll")))
    print(f"Unity {version}: {len(refs)} references, {len(srcs)} sources (Scripts + Tests/EditMode)")
    proc = subprocess.run(["dotnet", "exec", sdks[-1], "@" + rsp], capture_output=True, text=True)
    errors = [l for l in (proc.stdout + proc.stderr).splitlines() if "error CS" in l]
    for l in errors[:25]:
        print(l)
    if proc.returncode != 0:
        print(f"FAILED: {len(errors)} error(s)")
        return 1
    print("OK")
    return 0


# ---------------------------------------------------------------- authoring tools (kit services)

def creatures_dir(tg):
    return os.path.join(tg, "Config", "Creatures")


ARCHETYPES = {
    # name: (class, the sketch's numbers) - every other plan number 0 = the form's default
    "arthropod.spider": ("ArthropodPlan", {"form": 0, "bodyLength": 0.41}),   # the tarantula's
    "arthropod.crab": ("ArthropodPlan", {"form": 1, "bodyLength": 0.31}),     # the stone crab's
}


def archetype_sketch(tg, name, arch):
    import json
    cls, sketch = ARCHETYPES[arch]
    cat = json.load(open(os.path.join(creatures_dir(tg), "catalogue.json"), encoding="utf-8"))
    part = next((p for p in cat["parts"] if p["name"] == cls), None)
    if part is None:
        sys.exit(f"{cls} is not in catalogue.json (catalogue --write?)")
    data = {}
    for prm in part["params"]:
        n, t = prm["name"], prm["type"]
        if "." in n:
            continue
        if n == "id":
            data[n] = "plan"
        elif n == "at":
            data[n] = kityaml.at(0)
        elif n in sketch:
            data[n] = sketch[n]
        elif t.endswith("[]") or t.startswith("List"):
            data[n] = "[]"
        elif t == "string":
            data[n] = ""
        else:
            data[n] = 0
    sp = kityaml.Species(name, scale=1)
    sp.add_part(cls, data)
    return sp


def cmd_new(tg, a):
    if len(a.names) != 1 or not a.source:
        sys.exit("new: <Species> --from <Species|archetype> (archetypes: " + ", ".join(ARCHETYPES) + ")")
    name, src = a.names[0], a.source
    path = os.path.join(creatures_dir(tg), name + ".asset")
    if os.path.exists(path):
        sys.exit(f"{path} exists")
    if src in ARCHETYPES:
        sp = archetype_sketch(tg, name, src)
        note = f"Scaffolded from the archetype {src} (creature_kit.py new): plan numbers 0 = the form's default."
    else:
        sp = kityaml.load(os.path.join(creatures_dir(tg), src + ".asset"))
        if not sp.kit:
            # a legacy asset: its kit form first (the harness writes it), then from there
            rc = run(tg, a.real_unity, ["kit-convert", src, name], a.no_build)
            if rc != 0:
                sys.exit(rc)
            sp = kityaml.load(path)
            os.remove(path)
        sp.rename(name)
        note = f"Scaffolded from {src} (creature_kit.py new)."
    sp.save(path)
    gen_dir = a.gen_dir or os.path.join(tg, "Tools~", "SpeciesGen")
    os.makedirs(gen_dir, exist_ok=True)
    gen = os.path.join(gen_dir, name + ".py")
    with open(gen, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(kityaml.to_python(sp, note=note))
    print(f"wrote {path} (+ .meta)")
    print(f"wrote {gen}")
    print(f"next: edit {name}.py, run it (python {name}.py {tg}), creature_kit.py check {name}; then the lab roster (references/lab.md)")
    return 0


def cmd_render(tg, a):
    if len(a.names) != 1:
        sys.exit("render: <Species> [--phase P,Q]")
    name = a.names[0]
    out = os.path.abspath(a.out or os.path.join(os.getcwd(), "look"))
    os.makedirs(out, exist_ok=True)
    for f in glob.glob(os.path.join(out, name + "_*.obj")):
        os.remove(f)
    args = ["pose-dump", name, "--out", out] + (["--phase", a.phase] if a.phase else []) + (["--seconds", a.seconds] if a.seconds else [])
    rc = run(tg, a.real_unity, args, a.no_build)
    objs = sorted(glob.glob(os.path.join(out, name + "_*.obj")))
    if not objs:
        return rc or 1
    renderer = os.path.join(tg, "Tools~", "CreatureLook", "render.py")
    png = os.path.join(out, name + ".png")
    return subprocess.call([sys.executable, renderer] + objs + ["--out", png, "--views", a.views])


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("command", choices=["check", "test", "list", "species", "catalogue", "kit-convert", "unity-compile",
                                        "new", "render", "stats", "trace", "yaml-selftest"])
    ap.add_argument("names", nargs="*")
    ap.add_argument("--tg")
    ap.add_argument("--real-unity", action="store_true")
    ap.add_argument("--no-build", action="store_true")
    ap.add_argument("-v", action="store_true")
    ap.add_argument("--exclude-category", action="append", default=[])
    ap.add_argument("--write", action="store_true", help="catalogue: regenerate the files")
    ap.add_argument("--from", dest="source", help="new: the species or archetype to start from")
    ap.add_argument("--gen-dir", help="new: where the generator goes (default <tg>/Tools~/SpeciesGen)")
    ap.add_argument("--phase", help="render: phases, comma list; trace: a label substring")
    ap.add_argument("--part", help="trace: the part whose bones to trace")
    ap.add_argument("--out", help="render: output folder; trace: the CSV")
    ap.add_argument("--seconds", help="render / trace: run length (x sqrt s; default the sweep's adaptive run)")
    ap.add_argument("--views", default="side,front34,top", help="render: views (side, front, front34, top, rear34, hero, ...)")
    a = ap.parse_args()
    tg = find_tg(a.tg)
    if a.command == "unity-compile":
        sys.exit(unity_compile(tg))
    if a.command == "yaml-selftest":
        probs = kityaml.selftest(creatures_dir(tg))
        for p in probs:
            print(p)
        print("OK: every asset round-trips" if not probs else f"{len(probs)} problem(s)")
        sys.exit(1 if probs else 0)
    if a.command == "new":
        sys.exit(cmd_new(tg, a))
    if a.command == "render":
        sys.exit(cmd_render(tg, a))
    if a.command in ("stats", "trace"):
        if len(a.names) != 1:
            sys.exit(f"{a.command}: name one species")
        args = [a.command, a.names[0]]
        if a.command == "trace":
            for flag, v in (("--phase", a.phase), ("--part", a.part), ("--out", a.out), ("--seconds", a.seconds)):
                if v:
                    args += [flag, os.path.abspath(v) if flag == "--out" else v]
        sys.exit(run(tg, a.real_unity, args, a.no_build))
    extra = (["-v"] if a.v else []) + sum((["--exclude-category", c] for c in a.exclude_category), [])
    if a.command == "species":
        sys.exit(run(tg, a.real_unity, ["species"], a.no_build))
    if a.command == "catalogue":
        sys.exit(run(tg, a.real_unity, ["catalogue"] + (["--write"] if a.write else []), a.no_build))
    if a.command == "kit-convert":
        if len(a.names) != 2:
            sys.exit("kit-convert: <Species> <NewName> (e.g. kit-convert DesertSnake KitSnake)")
        rc = run(tg, a.real_unity, ["kit-convert"] + a.names, a.no_build)
        if rc == 0:
            print(f"next: a .meta for {a.names[1]}.asset (Unity writes one on import; offline: copy a species .meta "
                  f"with a fresh guid), then: creature_kit.py check {a.names[1]}")
        sys.exit(rc)
    if a.command == "list":
        sys.exit(run(tg, a.real_unity, ["list"] + a.names, a.no_build))
    if a.command == "check":
        if not a.names:
            sys.exit("check: name at least one species (e.g. check DesertMonitor)")
        # CreatureKitTests is a [TestFixtureSource] over the species assets: one fixture per asset name
        sys.exit(run(tg, a.real_unity, ["test"] + [f"CreatureKitTests({n})." for n in a.names] + extra, a.no_build))
    sys.exit(run(tg, a.real_unity, ["test"] + a.names + extra, a.no_build))


if __name__ == "__main__":
    main()
