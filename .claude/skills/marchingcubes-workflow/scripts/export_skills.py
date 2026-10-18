#!/usr/bin/env python3
"""Export .claude/skills/* into the ffremming/claude-skills marketplace layout.

    plugins/<name>/.claude-plugin/plugin.json
    plugins/<name>/skills/<name>/SKILL.md (+ references/, scripts/)
    marketplace.plugins.json   (entries to merge into .claude-plugin/marketplace.json)

and validates the result with the same rules that repo's scripts/validate.py
applies: frontmatter name == folder, non-empty description <= 1024 chars,
files referenced from SKILL.md exist, plugin.json name == directory.

usage: python export_skills.py --out dist/marketplace [--version 1.0.0] [--author Ferdinand]
"""
import argparse
import json
import os
import re
import shutil
import sys

CATEGORY = {
    "noise-terrain": ("gamedev", ["procedural", "terrain", "noise", "unity", "csharp"]),
    "lsystem-grammars": ("gamedev", ["procedural", "l-system", "plants", "unity", "csharp"]),
    "vegetation-scatter": ("gamedev", ["procedural", "vegetation", "instancing", "lod", "unity"]),
    "isosurface-meshing": ("gamedev", ["marching-cubes", "transvoxel", "voxel", "lod", "unity"]),
    "marchingcubes-workflow": ("gamedev", ["unity", "mcp", "workflow", "marchingcubes"]),
    "creature-module": ("gamedev", ["procedural", "creatures", "animation", "ik", "gpu-skinning", "unity"]),
}


def frontmatter(path):
    text = open(path, encoding="utf-8").read()
    m = re.match(r"^---\r?\n(.*?)\r?\n---\r?\n", text, re.S)
    if not m:
        return None, text
    fields, key = {}, None
    for line in m.group(1).splitlines():
        kv = re.match(r"^([A-Za-z0-9_-]+):\s*(.*)$", line)
        if kv:
            key = kv.group(1)
            fields[key] = kv.group(2).strip()
        elif key and line.strip():
            fields[key] += " " + line.strip()
    return fields, text


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--version", default="1.0.0")
    ap.add_argument("--author", default="Ferdinand")
    ap.add_argument("--skills", default=None, help="source dir (default: the .claude/skills this script lives in)")
    args = ap.parse_args()

    here = os.path.dirname(os.path.abspath(__file__))
    skills_dir = args.skills or os.path.abspath(os.path.join(here, "..", ".."))
    out = os.path.abspath(args.out)
    plugins_dir = os.path.join(out, "plugins")
    if os.path.isdir(plugins_dir):
        shutil.rmtree(plugins_dir)
    os.makedirs(plugins_dir)

    entries, errors = [], []
    for name in sorted(os.listdir(skills_dir)):
        src = os.path.join(skills_dir, name)
        skill_md = os.path.join(src, "SKILL.md")
        if not os.path.isfile(skill_md):
            continue
        fields, body = frontmatter(skill_md)
        if not fields:
            errors.append(f"{name}: no frontmatter"); continue
        if fields.get("name") != name:
            errors.append(f"{name}: frontmatter name '{fields.get('name')}' != folder")
        desc = fields.get("description", "")
        if not desc:
            errors.append(f"{name}: empty description")
        elif len(desc) > 1024:
            errors.append(f"{name}: description is {len(desc)} chars (max 1024)")
        for ref in sorted(set(re.findall(r"`(references/[^`]+|scripts/[^`]+)`", body))):
            if not os.path.exists(os.path.join(src, ref)):
                errors.append(f"{name}: points at '{ref}', which does not exist")

        dst = os.path.join(plugins_dir, name, "skills", name)
        shutil.copytree(src, dst, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        manifest = {"name": name, "version": args.version, "description": desc.split(". ")[0].rstrip(".") + ".",
                    "author": {"name": args.author}}
        os.makedirs(os.path.join(plugins_dir, name, ".claude-plugin"))
        with open(os.path.join(plugins_dir, name, ".claude-plugin", "plugin.json"), "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2)
        category, tags = CATEGORY.get(name, ("gamedev", ["unity"]))
        entries.append({"name": name, "source": f"./plugins/{name}", "description": manifest["description"],
                        "version": args.version, "category": category, "tags": tags,
                        "author": {"name": args.author}})

    with open(os.path.join(out, "marketplace.plugins.json"), "w", encoding="utf-8") as f:
        json.dump(entries, f, indent=2)
    # A complete catalog too, so the marketplace repo's validate.py can run on
    # this directory as-is (and so `/plugin marketplace add <out>` works for a
    # local test before anything is merged upstream).
    os.makedirs(os.path.join(out, ".claude-plugin"), exist_ok=True)
    catalog = {"name": "marchingcubes-skills", "owner": {"name": args.author},
               "metadata": {"description": "Procedural generation skills from the MarchingCubes project: noise terrain, "
                            "L-system grammars, vegetation scatter, isosurface meshing, and the repo workflow.",
                            "version": args.version},
               "plugins": entries}
    with open(os.path.join(out, ".claude-plugin", "marketplace.json"), "w", encoding="utf-8") as f:
        json.dump(catalog, f, indent=2)

    for e in errors:
        print("ERROR:", e)
    print(f"exported {len(entries)} plugin(s) to {out}" + (f" with {len(errors)} error(s)" if errors else ""))
    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
