---
name: marchingcubes-workflow
description: How to work in the MarchingCubes Unity repo without losing time to the Editor — the Assets/TerrainGen submodule layout, compiling C# outside Unity, the Unity MCP server/bridge/session model and its port collisions with the SpaceGame project, routing tool calls to the right Editor instance, execute_code limits, play mode when the Editor is unfocused, screenshots for verification, crash logs, and what to do when the bridge drops. Use for any task in this repository that writes C#, shaders or assets, or that needs the Editor over MCP; use it before the first MCP call of a session and whenever an MCP result looks like the wrong project, an empty instance list, or a stalled reload. Also use when the user asks to publish these skills to their claude-skills marketplace.
---

# MarchingCubes workflow

The Editor is the last mile. Iterate on disk, compile offline, verify by
simulation where possible, then make one short visit to the Editor. This
repo's specifics are below; `references/unity-mcp.md` has the MCP mechanics
in full.

## Layout

- Project root: `C:\Users\tobia\Documents\unity_stuff\MarchingCubes`,
  Unity **6000.2.6f2**, URP 17, D3D11, text serialisation.
- Everything that matters is the git **submodule** `Assets/TerrainGen`
  (`Scripts/`, `Shaders/`, `Config/`, `Editor/`). Commit there, then bump the
  pointer in the parent. `git status` in the parent shows `M Assets/TerrainGen`
  for any submodule change.
- `Scripts/LSystem` is the only asmdef (`TerrainGen.LSystem`), so EditMode
  tests exist; nothing inside it may reference `DensityField`.
- Scene `Assets/Scenes/SampleScene.unity` is LFS and huge; the terrain,
  `PlantScatter`, the player and the `TargetTransform` live in it. Terrain
  geometry is never authored in the scene: edit fields and `Config/*.asset`.
- Per-project rules live in `CLAUDE.md` at the root; the MCP port there is
  the one to trust.

## Compile before the Editor sees it

`scripts/compile_check.py` builds every runtime and Editor script against the
installed Unity's assemblies with the dotnet SDK's Roslyn in ~10 s:

```bash
python .claude/skills/marchingcubes-workflow/scripts/compile_check.py
```

It reads `ProjectSettings/ProjectVersion.txt` to find the Editor, references
`Managed/UnityEngine/*.dll`, `UnityEditor.dll`, netstandard 2.1 and the
package assemblies already in `Library/ScriptAssemblies`, and compiles
`Assets/TerrainGen/Scripts` (minus the asmdef folder, referenced as a DLL)
plus `Assets/TerrainGen/Editor`. Shaders cannot be compiled offline; check
`ShaderUtil.ShaderHasError` in the Editor after any shader change, because
an errored material draws nothing and logs once.

## The Editor, in order

1. Read `mcpforunity://instances`. It must list `MarchingCubes@…` on
   6000.2.6f2. If it lists SpaceGame, or nothing, read
   `references/unity-mcp.md` before doing anything else; do not act on the
   wrong project's scene.
2. `refresh_unity` (force, compile) after file changes; poll
   `mcpforunity://editor/state` until `ready_for_tools` and
   `last_domain_reload_after_unix_ms` is newer than before. The bridge drops
   during every reload and comes back within a minute; a crash-restarted
   Editor may come back attached to a different server.
3. `read_console` for errors and warnings.
4. Play mode: `manage_editor play`, then set
   `Application.runInBackground = true` via `execute_code` if the Editor is
   unfocused, or the game sits on frame 1 forever. Stats through
   `execute_code` (CodeDom, C# 6, reflection on private members is fine).
   Screenshots via `manage_camera screenshot` with `camera: "Main Camera"`;
   positioned captures (`view_position` + `view_target`) also render
   `RenderMeshInstanced` draws. Read the PNG with the Read tool and *look*.
5. `manage_editor stop`. Delete any screenshots you added under
   `Assets/Screenshots` (plain `rm` plus a refresh; `AssetDatabase.DeleteAsset`
   is blocked by execute_code's safety filter).
6. Never restart the Editor, never toggle its MCP server, never touch the
   SpaceGame Editor. Ask.

## Verification standards from this repo

- Numeric parity between prototype and port ≤ 1e-4; flood fills for floaters;
  Python simulation of enumeration and topology *before* C#.
- Measure before and after any optimisation with a Stopwatch around the real
  method (reflection-invoke private methods; it costs nothing measurable).
  Report a before/after table, not adjectives.
- A change is done when it has been seen in play mode from the player's
  spawn (near a cube corner: the hardest case for scatter enumeration) and
  the stats read back are the ones the design predicts.

## Threads

Density fields, `ChunkMesher`, the L-system rewriter with `[ThreadStatic]`
scratch and `PlantScatter` builds all run off the main thread. Rules: no Unity
externs on workers (`Quaternion.Euler`, `Matrix4x4.TRS`, `Debug.Log` is fine),
no shared mutable scratch, and **dedicated `Thread`s for long-lived blocking
workers** — parking them on `Task.Run` crashed the Editor with a Mono
threadpool refcount fault.

## Publishing skills

The user keeps a plugin marketplace at `github.com/ffremming/claude-skills`
(`plugins/<name>/.claude-plugin/plugin.json` + `skills/<name>/SKILL.md`,
`.claude-plugin/marketplace.json`, and a validator under its scripts folder).
To export the skills in this repo in that layout:

```bash
python .claude/skills/marchingcubes-workflow/scripts/export_skills.py --out dist/marketplace
```

It writes the plugin tree, a `marketplace.json` fragment, and runs the same
validation rules (frontmatter name = folder, description ≤ 1024 chars,
referenced files exist). Copy `plugins/*` into the marketplace repo, merge
the entries into its `marketplace.json`, bump versions, run its
`validate.py`, push.
