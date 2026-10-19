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


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("command", choices=["check", "test", "list", "species", "catalogue", "kit-convert", "unity-compile"])
    ap.add_argument("names", nargs="*")
    ap.add_argument("--tg")
    ap.add_argument("--real-unity", action="store_true")
    ap.add_argument("--no-build", action="store_true")
    ap.add_argument("-v", action="store_true")
    ap.add_argument("--exclude-category", action="append", default=[])
    ap.add_argument("--write", action="store_true", help="catalogue: regenerate the files")
    a = ap.parse_args()
    tg = find_tg(a.tg)
    if a.command == "unity-compile":
        sys.exit(unity_compile(tg))
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
