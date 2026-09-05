#!/usr/bin/env python3
"""Compile the project's C# outside Unity with the dotnet SDK's Roslyn.

Catches type and syntax errors in ~10 s without a domain reload. Not a
substitute for the Editor (no shader compile, no serialization), but it is
the gate before one.

usage: python compile_check.py [--root <project>] [--no-editor]
"""
import argparse
import glob
import os
import re
import subprocess
import sys


def find_unity(root):
    ver = open(os.path.join(root, "ProjectSettings", "ProjectVersion.txt"), encoding="utf-8").read()
    m = re.search(r"m_EditorVersion:\s*(\S+)", ver)
    if not m:
        sys.exit("cannot read ProjectVersion.txt")
    version = m.group(1)
    for hub in (r"C:\Program Files\Unity\Hub\Editor", os.path.expanduser("~/Unity/Hub/Editor"),
                "/Applications/Unity/Hub/Editor"):
        cand = os.path.join(hub, version, "Editor", "Data")
        if os.path.isdir(cand):
            return version, cand
        cand = os.path.join(hub, version, "Unity.app", "Contents")
        if os.path.isdir(cand):
            return version, cand
    sys.exit(f"Unity {version} not found under the Hub")


def find_csc():
    dotnet = r"C:\Program Files\dotnet\sdk" if os.name == "nt" else "/usr/share/dotnet/sdk"
    sdks = sorted(glob.glob(os.path.join(dotnet, "*", "Roslyn", "bincore", "csc.dll")))
    if not sdks:
        sys.exit("no dotnet SDK with Roslyn found")
    return sdks[-1]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=None, help="Unity project root (default: walk up from cwd)")
    ap.add_argument("--no-editor", action="store_true", help="skip Assets/TerrainGen/Editor")
    args = ap.parse_args()

    root = args.root or os.getcwd()
    while not os.path.isdir(os.path.join(root, "ProjectSettings")):
        parent = os.path.dirname(root)
        if parent == root:
            sys.exit("not inside a Unity project")
        root = parent

    version, data = find_unity(root)
    refs = glob.glob(os.path.join(data, "Managed", "UnityEngine", "UnityEngine*.dll"))
    refs.append(os.path.join(data, "NetStandard", "ref", "2.1.0", "netstandard.dll"))
    if not args.no_editor:
        refs.append(os.path.join(data, "Managed", "UnityEditor.dll"))
        refs += glob.glob(os.path.join(data, "Managed", "UnityEngine", "UnityEditor*.dll"))
    for name in ("TerrainGen.LSystem", "Unity.RenderPipelines.Universal.Runtime",
                 "Unity.RenderPipelines.Core.Runtime", "Unity.InputSystem", "Unity.Mathematics",
                 "Unity.Burst", "Unity.Collections"):
        p = os.path.join(root, "Library", "ScriptAssemblies", name + ".dll")
        if os.path.exists(p):
            refs.append(p)

    scripts = os.path.join(root, "Assets", "TerrainGen", "Scripts")
    srcs = [p for p in glob.glob(os.path.join(scripts, "**", "*.cs"), recursive=True)
            if os.sep + "LSystem" + os.sep not in p]  # own asmdef, referenced as a DLL above
    if not args.no_editor:
        srcs += [p for p in glob.glob(os.path.join(root, "Assets", "TerrainGen", "Editor", "*.cs"))
                 if "LSystemGrammarAssetEditor" not in p]  # lives in the LSystem assembly's editor scope

    out_dir = os.path.join(root, "Library", "ClaudeCompileCheck")
    os.makedirs(out_dir, exist_ok=True)
    rsp = os.path.join(out_dir, "args.rsp")
    defines = "UNITY_6000_0_OR_NEWER;UNITY_2022_1_OR_NEWER" + ("" if args.no_editor else ";UNITY_EDITOR")
    lines = [f'/r:"{r}"' for r in refs] + [f'"{s}"' for s in srcs]
    lines.append(f'/nologo /target:library /out:"{os.path.join(out_dir, "check.dll")}" '
                 f'/nowarn:CS0618,CS0649,CS0414,CS0168,CS0219,CS0108,CS0162 /langversion:9 /define:{defines}')
    open(rsp, "w", encoding="utf-8").write("\n".join(lines))

    print(f"Unity {version}: {len(refs)} references, {len(srcs)} sources")
    proc = subprocess.run(["dotnet", "exec", find_csc(), "@" + rsp], capture_output=True, text=True)
    output = (proc.stdout + proc.stderr).strip()
    errors = [l for l in output.splitlines() if "error CS" in l]
    for l in errors[:40]:
        print(l)
    if proc.returncode != 0:
        print(f"FAILED: {len(errors)} error(s)")
        sys.exit(1)
    print("OK")


if __name__ == "__main__":
    main()
