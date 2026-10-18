# Workflow for creature work (and for agents doing it)

These rules come from the creature SDD (R1, R4, R32 and the stalls of 2026-10-17/18).
The Editor is the scarce resource: one Editor, many agents, a machine short on RAM.

## 1. Offline harness first

Develop and tune against a **pure-C# harness**, then visit Unity once.

- A `dotnet` console project (net8.0) that `<Compile Include=...>`s the real runtime
  sources from the submodule or worktree (`Scripts/Creatures/*.cs`) and the real test
  files, plus either:
  - small **UnityEngine stubs** (`Vector3`, `Quaternion`, `Mathf`, `Bounds`,
    `ScriptableObject`, `DensityField`; a `CLIMB_HARNESS`-style define), or
  - a reference to the **real** `UnityEngine.CoreModule.dll` of 6000.2.6f2 (the
    octopus harness), with an NUnit shim/mini-runner for `[Test]` methods.
- Analytic stand-ins for colliders and fields (SDF cylinders, planes, cliffs, holes).
- Capture **golden hashes** (FNV-1a over bone matrices for N ticks) before changing
  shared code, and assert them after every commit. Note: Mono's `Mathf` differs
  from .NET, so harness goldens are not Unity goldens; capture Unity's once in the Editor.
- Render stills with numpy/PIL when the shape matters (octopus `render.py`), but the
  user judges the look in Unity.
- Session examples (the scratchpad is per session; recreate rather than hunt):
  `climb_harness/`, `species_h7q/`, `octopus_proto/octo_tests/`,
  `wyvern_impl/harness/run.sh`, `legs_impl/`.
- **Give each agent its own scratch subfolder.** Two agents once shared
  `scratchpad/harness/` and `dotnet new console --force` overwrote the other's project.

Compile gates before the Editor:
`python .claude/skills/marchingcubes-workflow/scripts/compile_check.py --root <project root>`
(full path `C:\Users\tobia\AppData\Local\Programs\Python\Python312\python.exe`), and
the SDD's `compile.py` copy pointed at the worktree (also compiles Tests). Shaders
cannot be compiled offline.

## 2. Unity once per finished feature

- Verify the instance first (`mcpforunity://instances` → `MarchingCubes@…`,
  6000.2.6f2). The Editor has served on 8080 for this work although `CLAUDE.md` says 8040.
- `refresh_unity`, `read_console`, commit the generated `.meta` files.
- **One test class per `run_tests` job** (filter by class full name). Combined jobs
  were lost twice to domain reloads/session drops; a lost job costs the whole run.
- Routine filter `TerrainGen.Tests.Creature`; perf separately
  (`group_names: ["TerrainGen.Tests.Perf"]`); full suite last.
- Never start a test that runs over ~60 s while the user is watching.
- Stop play mode afterwards; keep sessions short (memory).

## 3. The user does the visual inspection (R32)

Agents **take no screenshots** unless the user is away. Finish with a hand-off: the
scene, the play-mode setup, and a **"what to look at"** list (e.g. "perched 30 s on
the Baobab: arms should not tremble; walk toward it: cloak ramps, no flicker").
User feedback drives the next fix. If shots are needed while the user is away, see
`gotchas.md` (Game-view capture, retake empty shots, delete your PNGs).

## 4. Parallel branches: git worktrees

- Worktrees live **outside `Assets/`**: `C:/Users/tobia/Documents/unity_stuff/wt/<name>/Assets/TerrainGen`
  (`git -C Assets/TerrainGen worktree add ../../../wt/<name>/Assets/TerrainGen -b <branch> <base>`).
- Give each a fake project root: junctions `wt/<name>/ProjectSettings` and
  `wt/<name>/Library/ScriptAssemblies` to the real project, so `compile_check --root wt/<name>` works.
- **Never create a worktree inside `Assets/`**: Unity imports it as a second copy of
  every script (one was created under `Assets/TerrainGen/wt` by accident and removed
  within seconds).
- Only the main tree is opened by the Editor. For a branch's Editor phase, switch the
  main tree's submodule to it (after committing everything), or merge first.
- Clean up with `git worktree remove` + `git worktree prune` when a branch merges.
- Do not check out branches in a tree another agent is using; read with `git show`.

## 5. Agent rules

- **Commit in small steps** (`wip(...)` is fine) so a stall loses minutes, not hours.
  Agents stall on the stream watchdog (600 s) and on Editor hangs.
- **Never resume a stalled Editor agent once a replacement is dispatched**: two
  agents drove the Editor at once on 2026-10-18. Save its WIP as a commit, then brief
  the fresh agent compactly.
- One agent in the Editor at a time; the controller serialises the queue.
- Report RED → GREEN with numbers, a before/after perf table, and the open risks.
- Parent repo: stage only the scene, the submodule pointer and docs. Never stage
  `.claude/settings.json`, `.mcp.json`, `CLAUDE.md`, `ProjectSettings/*`,
  `Assets/_CreatureSpike/`.
