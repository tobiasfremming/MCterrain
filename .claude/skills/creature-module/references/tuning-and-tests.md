# Tuning, tests and the lab

## Running the tests

1. Offline first: the harness (`workflow.md`) and
   `compile_check.py [--root <worktree project>]` (full Python path
   `C:\Users\tobia\AppData\Local\Programs\Python\Python312\python.exe`).
2. **Editor open:** MCP `run_tests`, mode EditMode, **one test class per job**, e.g.
   filter `TerrainGen.Tests.CreatureClimbTests` (a regex on the full name). The
   routine group filter is `TerrainGen.Tests.Creature`. Verify the instance first.
3. **Editor closed:** `bash .superpowers/sdd/2026-10-16-creature-module/run_tests.sh <label> <filter>`
   (batch mode, 60–80 s; refuses while an Editor is open; the Editor-path shader test is
   ignored under `-nographics`).
4. **Perf tests** live in `TerrainGen.Tests.Perf`, category `Perf`, outside the routine
   filter. Run them on demand (`group_names: ["TerrainGen.Tests.Perf"]`) on a quiet
   machine. They also run in a full EditMode run.
5. **Full suite:** TerrainGen.Tests + TerrainGen.LSystem.Tests. Last counts: 230/230
   after the species merge; after climbing, Creature 159/159 and the TerrainGen.Tests
   assembly 200/201 (only `Perf_100Lizards` under load). Re-read the ledger for now.

## What pins what

| You changed | Run | The tests that bite |
|---|---|---|
| spine data | `CreatureSimSpineTests`, `CreatureMeshTests` | `Chain_SegmentLengthsExact`, `Chain_BendWithinLimit`, `Build_TailTaper_NoKink`, `MeshBuilder_MaxBend_NoInvertedTriangles` |
| legacy leg data | `CreatureLegTests`, `CreatureMonitorTests`, species tests | `Legs_TightTurn_JointRangesStayBounded`, `*_TightTurn_LegsClearTheTrunk`, `PlantedFeet_DoNotMove`, `Legs_OnSlope_FeetWithinTolerance`, `*_MaxBend_NoInvertedTriangles` |
| monitor gait | `CreatureMonitorTests` | `Monitor_CruiseSpeed`, `Monitor_FrontFootReachesForward`, `Monitor_StrideLength`, `Gait_SpineSway_*` |
| gait groups | | `Gait_NeverTwoGroupsSteppingAtOnce`, `Gait_EveryLegSteps`, `Hexapod_TripodGait_NeverOverlaps` |
| brain, enclosure, scale | `CreatureContainmentTests`, `CreatureEnclosureTests` | `Containment_LongWander_*`, `Containment_ScaledMonitor_LabRadius_AllInside`, `Wander_AvoidsObstacle_*`, `Lab_Placement_NeighboursNeverOverlap`, `Lab_ScaleChange_RespawnsAtNewSize`, `Curb_Rebuild_DestroysTheOldMesh` |
| ground probes, cache | `CreatureGroundProbeTests` | `Hole_Overhanging_*`, `Hole_Bowl_*` (plain and `_ClimbingGround_`), `Cached_OverhangColumn_*`, `Cached_DigInvalidation_*`, `Cached_Smooth_StepCells_StayWithinNodeHeights` |
| climbing | `CreatureClimbTests`, `Perf.CreatureClimbPerfTests` | `Walking_*_BitIdentical`, `Climb_GroundToTrunk_NoFold`, `Climb_TerrainCliff_UpAndOver`, `Climb_OverhangPastLimit_Blocks`, `Perf_Walking100_Unchanged` |
| desert species | `CreatureDesertSpeciesTests` | snake undulation (head > 0.15 m, mid-body > 0.10 m), beetle gait, MaxBend |
| world, rebind | `CreatureWorldTests` | `World_PhysicsFieldRebuilt_RebindsProbeCachesAndEdits`, `World_SpawnTickRender_NoAllocAfterWarmup`, `Monitor_OnDesertWorld_TickDoesNotAllocate` |
| renderer, shader | `CreatureRendererTests`, `CreatureShaderTests` | `CreatureShader_EditorRuntimeCompile_NoErrors`, `Renderer_Bounds_ContainEverySkinnedVertex`, `Instance_StructIs16Bytes` |
| anything in the tick | `TerrainGen.Tests.Perf` | `Perf_OneLizard_Under0_1ms`, `Perf_100Lizards_Under3ms` (bound 4 ms, R23), `Build_Time_Under5ms` |
| in-progress branches | `Octopus*Tests`, `CreatureOctopus*Tests`, `CreatureBodyTests`; `WingedSerpent*Tests`, `CreatureWinged*`; `ArthropodIKTests`, `CreatureSpiderTests`, `LegacyLegsGoldenTests` | see `body-plans.md` |

For a new species, add a test block covering: `IsAsAuthored`; builds and wanders
contained (5 simulated minutes, two seeds); gait never overlaps, every leg steps;
planted feet fixed; tight turn: joint ranges bounded and legs clear the trunk; MaxBend 0
inversions; legless: `Undulates` with head **and** mid-body sway; **size variation**:
the acceptance bounds hold at 0.9× and 1.1× scale; perf for a crowd if it is cheap to
spawn many.

Test hygiene: show RED first (behavioural RED beats compile RED); assert minima (and
maxima where "too much" is a defect, as the octopus squish), not means; a test that
cannot fail is worse than none (the old GC tests, an early undulation-fade test);
guards for known-open defects pin the current value (the R28 `worstBend` guards).

## Tuning workflow

1. Write or extend the failing test for the visible defect (sliding, fold, stutter,
   tucked leg, tremble, flicker).
2. Change **data** first: limits, pole, rest offset, threshold, overshoot, knee blend,
   step duration, ClimbSpec factors.
3. Tune in the harness; run the species' tests and the monitor tests (shared paths,
   sensitive monitor tune) in Unity once.
4. Hand Unity to the user with a "what to look at" note (R32): side view, head close-up,
   top-down mid-turn, a dune slope, beside / on the Baobab. Name the anti-goals to check:
   sausage segments, kinks, facets, sliding or floating feet, legs through the body,
   tail outside the curb.
5. If data cannot fix it, propose a generic data-backed mechanism, never a per-species branch.

## The Creature Lab

- **Scene:** `Assets/Scenes/CreatureLab.unity` (LFS), built by
  `Marching Cubes/Rebuild Creature Lab` (`Editor/CreatureLabScene.cs`) on
  `Config/Creatures/CreatureLabWorldConfig.asset` (flat world, DesertWorld dunes, plants
  off; keep it out of `Config/Test`). Current lab: DesertMonitor, DesertSnake,
  DesertBeetle (parent 13fa328), Baobab `plantScale` 2.0 (f9368de).
- **`CreatureLab`** (on `Creatures`, next to `CreatureWorld` and `CreatureDebugView`):
  `species[]`, `scaleOverrides[]`, `spacing` 25, `arcRadius` 30, `searchRadius` 15,
  `seed`, `borderMaterial`, `enclosurePlant`, `plantScale`, `plantOffset` 0.45 R.
  Places enclosures once the ground answers (up to 10 s), on an arc on the sun side,
  flattest of 16 candidates, neighbours r_a + r_b + 4 m apart. Climbers get a
  `ClimbingBrain` and a climbable tree; cap = min(1.5 body lengths, 0.45 × plant height).
- In progress: `OctopusLab` (grove + prey, octopus branch) and the aviary for flying
  species (14 m × 10 m, posts, boulders, wyvern branch) are required lab deliverables.
- **Enclosure:** 12 × 30 cm sandstone curb following the sand, no colliders.
- **F3** toggles `CreatureDebugView` (Game view needs focus; from MCP set `show = true`).

## Baselines

| | value |
|---|---|
| monitor scale 1: cruise / reach / stride / tight-turn swing | 0.62 m/s / 0.63 L / 1.01 L / 59–60° |
| monitor scale 4 cruise | 1.25 m/s (√4 timing) |
| 1 monitor scale 4, DesertWorld | 0.031–0.046 ms walking; 0.17 ms climbing real bark |
| 100 monitors | 3.65–3.99 ms (≤ 4) |
| per-tick profile, scale 4 (µs) | ground 10, sway 7, frames 6, legs 11, chain 2 |
| holes (R25) | 0 flips, 0 % stretch, feet 0.1 cm; worst bend 61° / 54° |
| tight turn (R28) | trunk clearance +6.5 cm, girdle +5.7 cm |
| snake (TestSnake 40° @ 0.4 Hz) | head 31.6 cm, joint 20 19.5 cm, 0.60 m/s |
| hexapod | 0 overlapping tripod ticks, 34–35 steps per leg in 15 s |
