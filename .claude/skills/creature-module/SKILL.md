---
name: creature-module
description: Use, tune and extend the procedural creature module in this MarchingCubes repo (Assets/TerrainGen/Scripts/Creatures, Config/Creatures). Covers the spine chain, gait-grouped legs (two-bone and multi-segment arthropod IK), ground probes and cache, climbing on real geometry (ISurfaceProbe, CreatureSurfaces, up field, ClimbingBrain), body plans (ICreatureBody, tree octopus, winged serpent flight), CreatureWorld, the instanced GPU-skinned renderer and shaders, CreatureLab and the F3 view. Use it to add or size a species from data, tune legs, gait, IK, sway, climbing or looks, fix sliding feet, folds, jitter or flicker, judge performance, or plan agent work on creature branches. Trigger on creature, lizard, monitor, snake, beetle, spider, tarantula, octopus, tentacle, wyvern, wings, flight, climbing, gait, legs, IK, species, sizeScale, CreatureLab, cloak.
---

# Creature module

A 3D port of the user's Manim lizard (`Documents/video_manim/lizard.py`). A
steered head drags a bend-limited chain that rides the terrain (or climbs a
trunk). Legs stay planted until they lag, then step in gait groups. A species is
**data only**: one `CreatureSpecies` asset, one GPU-skinned instanced draw.

The user's priorities, in order: **1. it looks really good, 2. it is fast.** A
visible defect (stutter, fold, sliding foot, flicker) is a bug even when every
test passes. **The user does the visual inspection (R32)**: hand Unity over with a
"what to look at" note instead of taking screenshots.

Ground truth, in this order: the code (`git -C Assets/TerrainGen show <branch>:<path>`),
then the ledger `.superpowers/sdd/2026-10-16-creature-module/progress.md`
(gitignored; rulings R1–R32, every deferred minor), then the specs in
`docs/superpowers/specs/2026-10-1{6,7}-*.md` (each ends with **user decisions**,
which are binding). Trust those and `git log` over memory and over this skill.

## What exists (status 2026-10-18)

| Feature | Where | Status |
|---|---|---|
| spine, legacy legs, ground cache, renderer, lab | `feat/creatures` | merged |
| climbing (real geometry + terrain walls) | `feat/creatures` (9607482) | merged |
| R28 fixes, GcAllocs Recorder, `TerrainGen.Tests.Perf` | `feat/creatures` | merged |
| DesertSnake, DesertBeetle (legacy legs) | `feat/creatures` | merged |
| `Basis` quaternion renormalise | `feat/creatures` (4637176) | merged |
| tree octopus, `ICreatureBody`/`SpineBody`, cloak, 32 B instance | `feat/creature-octopus` (main tree) | **in progress**: jitter/cloak/4× size, then arm roles + swinging |
| winged serpent, flight modes, membrane part 8 | `feat/creature-wyvern` (`wt/wyvern`) | **in progress**: offline done, Editor phase queued |
| arthropod legs, DaddyLongLegs, Tarantula, beetle v2 | `feat/creature-legs` (`wt/legs`) | **in progress**: offline done, Editor phase queued |

Before relying on an in-progress API, check that the branch still holds it
(`git -C Assets/TerrainGen branch -a`, ledger tail). Never describe it as merged.

References, read on demand:
- `references/new-species.md`: the recipe, every field, legacy vs arthropod legs,
  the size pipeline, the part-id registry, the shipped values.
- `references/climbing.md`: surfaces, the up field, the climb rules, ClimbSpec, perf.
- `references/body-plans.md`: ICreatureBody, octopus, wyvern flight, arthropod
  legs (all in progress), the cloak, merge notes between those branches.
- `references/tuning-and-tests.md`: what pins what, running tests, the lab, baselines.
- `references/workflow.md`: offline harness first, Unity once per feature,
  worktrees, agent rules (stalls, scratch folders, small commits).
- `references/gotchas.md`: lessons that each cost hours (Editor, shaders, colour
  space, quaternions, GC counter, perf noise, R25 holes).

## Where things are

Submodule `Assets/TerrainGen`, assembly `TerrainGen.Runtime` (global namespace).
Tests in `Tests/EditMode/Creature*Tests.cs` (namespace `TerrainGen.Tests`), perf
tests in `TerrainGen.Tests.Perf` (category `Perf`).

```
CreatureSpecies (SO)  spine joints, legs[], locomotion, look, scale, climb (ClimbSpec)
   │                  [octopus: bodyPlan + cephalopod]  [wyvern: wings[] + flight]  [legs: LegSpec.segments]
   ├─► CreatureSim        per individual: head steering, chain, ground, sway, frames, Up[], bones
   │     ├─ CreatureLegs  rest points, joint ranges, gait groups, steps, TwoBoneIK (| ArthropodLegIK)
   │     ├─ IGroundProbe  Flat | FieldGroundProbe → CachedGroundProbe (0.5 m lattice, Hermite .Smooth)
   │     │   └ ISurfaceProbe  CompositeSurfaceProbe = terrain + PhysicsSurfaceProbe (real colliders)
   │     ├─ CreatureClimb  up field, anticipation fan, pitch limiter, steepness factors
   │     └─ ICreatureBrain WanderBrain | ClimbingBrain (wraps Wander) | [FlightBrain]
   ├─► CreatureMeshBuilder  rest-pose skinned mesh at runtime (< 5 ms); CreatureRestPose = bind
   └─► CreatureRenderer     bone × bind → _Bones, one RenderMeshPrimitives per species
CreatureWorld   Spawn/Despawn, TickAll (back faces on), LateUpdate render, terrain rebind
CreatureSurfaces + ClimbableFlora + SurfaceMeshCache + EnclosurePlant   climbable real meshes
CreatureLab + CreatureEnclosure + EnclosureArea    lab layout, curb, safe disc, Baobab (plantScale 2.0)
CreatureDebugView (F3)   chain, joint ellipses, IK, ups, surface sources, climb goal (no alloc)
```

A sub-step (`CreatureSim.SubStep`): head steering in the tangent plane → chain
step on `Path[]` (cone bend limits) → grounding through `spineGround` then
`RestoreLengths` (R25) → [climbing: pitch limiter] → gait sway → frames → legs.

Bones: spine `0..N-1`, then legs via `sp.LegBone(leg, part)` (legacy = 3 per leg;
arthropod = one per segment, `LegBoneLayout` prefix sums on `feat/creature-legs`),
then 2 eyes via `sp.EyeBone(e)`. Never hard-code `N + 3·leg`. Frames: +Z forward,
+Y up, +X right; bone matrices `TRS(origin, Basis(f, u), sizeScale)`.

Spawn: `CreatureWorld.Spawn(sp, pos, fwd, brain, area, seed, scaleOverride)`; the
area comes from `CreatureEnclosure.AreaFor(sp, maxScale)`.

## Adding a species, in short

Full recipe: `references/new-species.md`.
1. Copy the nearest asset in `Config/Creatures/` (DesertMonitor, DesertSnake,
   DesertBeetle; TestSnake/TestHexapod are test fixtures). **Author at scale 1** in metres.
2. Spine profile, then legs. **Pick the leg model**: legacy two-bone (lizard-like
   limbs; empty `segments`) or arthropod (insects, spiders; `segments[]`, branch
   `feat/creature-legs` until merged).
3. Locomotion, sway, look. Then **size**: `species.scale` × per-individual
   `look.sizeJitter` = `sizeScale`; lab `scaleOverrides`; timing ∝ √scale.
   **Every size-dependent quantity derives from `sizeScale`**, so two individuals of
   different size both look and behave right. Test at 0.9× and 1.1×.
4. Tests that load the asset (copy `CreatureExtensibilityTests` /
   `CreatureDesertSpeciesTests`), then add to `CreatureLab.species` + `scaleOverrides`.

**Do not change `CreatureSim`, `CreatureLegs`, `CreatureMeshBuilder` or
`CreatureRenderer` for one species.** If data cannot express it, make a **generic**
data-backed change (as R16 joint limits, ClimbSpec, LegSpec.segments did) and keep
every other species bit-identical (golden hashes) and green.

## Rules

1. **Containment is structural.** The head is clamped to `safeRadius`; the chain
   follows the head's path. Never steer the body directly or bypass `Bounds`.
2. **Ground comes from the density field; climbing contact from the real render
   mesh.** Positive = solid, normal = −gradient. A probe answers the **nearest**
   surface (R25). Climbing uses the object's own LOD0 bark via colliders: **no
   capsules, SDFs or proxy shapes**, ever (user constraint).
3. **Terrain is climbable only as a wall**: steeper than 50° over a relief ≥ ½ body
   length (R30/R31). Smaller relief (dug holes) is walked exactly as R25 tuned it.
   Max surface angle 140° (`ClimbSpec.MaxSurfaceAngle`). Details: `climbing.md`.
4. **Nothing allocates per frame.** Check with `GcAllocs.Count` and its positive
   control `AssertCounterWorks()`, never `GC.GetAllocatedBytesForCurrentThread` (reads
   0 on Unity Mono).
5. **Main thread only.** No `Task.Run`, no Burst, no new packages.
6. **Planted feet are fixed** (< 1e-5 m); segment lengths exact (holes ≤ 5 %);
   feet within 2 cm × scale of the surface.
7. **Fix a gait problem in the gait**, not by loosening a mesh test (R12).
8. **Colour space:** Inspector colours are sRGB; decode exactly once where they
   enter shading (`SetColor` does it, `SetVector`/vertex colours do not). See `gotchas.md`.
9. **Part ids are a registry** (0 body, 1 leg, 2 foot, 3 eye, 4–7 octopus, 8 wyvern
   membrane, 9 arthropod band). Take the next free id; never reuse one.
10. **Measure before and after** with a Stopwatch around the real tick; report a table.

## Performance budget

| | budget | measured |
|---|---|---|
| 1 monitor (scale 4, DesertWorld), walking | ≤ 0.1 ms | 0.031–0.046 ms |
| 100 monitors | ≤ 4 ms (R23) | 3.65–3.99 ms: **at the bound**, fails under load (R29) |
| 1 monitor climbing real bark | ≤ 0.25 ms | 0.17 ms median, p90 0.21 |
| draws | 1 per species + shadow + depth + DepthNormals | same |
| GC per frame | 0 | 0 |

One field sample ≈ 2.3 µs; anything adding field samples per tick shows at once,
per-joint work shows at 100 creatures. Re-run `TerrainGen.Tests.Perf` after touching
the tick, on a quiet machine, and A/B in one session when the machine is loaded.

## Workflow, in short (`references/workflow.md`)

- Develop against an **offline pure-C# harness** (real sources, stub or real
  `UnityEngine` DLL); `compile_check.py --root <worktree project>` before the Editor.
- Run Unity tests **once per finished feature**, **one test class per `run_tests` job**.
- Parallel branches: git worktrees **outside `Assets/`** (`unity_stuff/wt/<name>`)
  with ProjectSettings + Library/ScriptAssemblies junctions. Never inside `Assets/`.
- Agents commit in small steps. Never resume a stalled Editor agent once a
  replacement has been dispatched. Only one agent drives the Editor at a time.

## Other skills

- `marchingcubes-workflow`: Editor/MCP instance check, `compile_check.py`, refresh,
  publishing skills (`export_skills.py`).
- `noise-terrain` / `isosurface-meshing`: when the problem is the ground itself.
- `vegetation-scatter` / `lsystem-grammars`: plant prototypes, bark submeshes,
  skeletons (octopus hints), plant colours.
- `superpowers:systematic-debugging`: before fixing jitter or a fold; repro test first.
