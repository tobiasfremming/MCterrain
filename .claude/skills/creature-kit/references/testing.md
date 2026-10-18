# Testing a species: the harness and the generic kit

## The offline harness (`Assets/TerrainGen/Tools~/CreatureHarness/`)

| file | what |
|---|---|
| `CreatureHarness.csproj` | globs `Scripts/Creatures/**/*.cs` and the creature tests (`Creature*`, `Arthropod*`, `Octopus*`, `Winged*`, `LegacyLegs*`, `GcAllocs`, `TestFields`) minus two documented lists: `UnityOnlySources`, `UnityOnlyTests` (each with its reason). New files are picked up automatically. Define `CREATURE_HARNESS`. |
| `Stubs/UnityEngine*.cs` | stubbed engine (default mode). Math is the scratch `legs_impl` harness's, bit for bit, so the offline goldens hold: **add members, never change existing arithmetic**. `Stubs/HarnessRendering.cs` (both modes) makes `CreatureRenderer`'s CPU path (skin, bounds) run like `-nographics`. |
| `Stubs/HarnessYaml.cs`, `HarnessEditor.cs` | `AssetDatabase.LoadAssetAtPath/FindAssets/GUIDToAssetPath` over the committed `.asset` YAML (Unity serialization rules, unknown keys reported). |
| `Stubs/UnityOnlyMirrors.cs` | verbatim copies of the few pure statics of excluded files tests reach (`CreatureLab.EnclosureRadius/MaxScale`, `CreatureWorldTests.kMonitorPath`). Keep in sync. |
| `Stubs/HarnessProfiling.cs` | `Profiling.Recorder` over CoreCLR's exact allocation counter, so the real `GcAllocs.cs` (and its positive control) runs. |
| `MiniNUnit.cs`, `Program.cs` | NUnit subset + runner: `[Test]`, `[TestCase]`, `[TestFixtureSource]`, SetUp/TearDown, Ignore/Inconclusive; statuses PASS, FAIL, SKIP, NATIVE (real-Unity mode reached engine code), XFAIL/XPASS (`kKnown`). |
| `HarnessSelfTests.cs` | the harness checks itself (exact integer equality: a wrong golden once passed; every asset loads with no unknown keys). |

Modes: stub (default; everything runs) and `--real-unity` (the real CoreModule: pure math such as
`ArthropodIKTests` and the octopus solvers run with Unity's own `Mathf`; anything touching a
`ScriptableObject`, `Mesh` or `Object.name` reports NATIVE - 94 pass, 227 native on 2026-10-18). The
renderer's GPU types are harness no-ops in both modes (`Stubs/HarnessRendering.cs`).

Extras: `-p:TG=<tree>` builds against another TerrainGen tree (e.g. a `git archive` of an older commit, to
tell a regression from a pre-existing failure); `-p:HarnessExtra=<folder>` compiles your scratch `.cs`
experiments in (namespace `TerrainGen.Tests.*`, `[Test]` methods) without touching the tree.

Baseline 2026-10-18 (feat/creature-kit): 315 pass, 9 skipped, 6 known, 0 failed, ~24 s.

## The generic kit (`Tests/EditMode/CreatureKitTests.cs`, `CreatureKitAssets.cs`)

One fixture per asset in `Config/Creatures` (`[TestFixtureSource]`; discovery through
`AssetDatabase.FindAssets`, which the harness serves from the same YAML). Checks are problem functions in
`KitChecks` (null = fine) so the RED tests prove each one bites without catching NUnit asserts.

| # | test | rule |
|---|---|---|
| 1 | `Validate` | `sp.Validate()` is null |
| 2 | `NoMissingTypes` | `m_Script` is CreatureSpecies.cs; every serialized key is a field (offline: nested keys too) |
| 3 | `Layout` | spine, legs, wings, eyes contiguous = BoneCount; bind poses = BoneCount; skin indices in range, weights sum to 1, every bone skinned |
| 4 | `MeshTime` | renderer mesh builds < 5 ms (best of 3) |
| 5 | `MaxBend` | 5 s minimum-radius circle: no inverted triangle; the chain reaches its bend limit (bite) |
| 6 | `Bounds` | renderer culling bounds hold every skinned vertex of the largest individual |
| 7 | `Wander` | 5 min in the lab area (aviary + roof for flyers), seeds at the smallest and largest individual: joints, feet, knees inside; travel guard (1 body length per 30 s) |
| 8 | `Gait` | planted feet fixed (< 1e-5 x s), never over-reached, every walking leg steps, feelers never, never two gait groups in the air |
| 9 | `Size` | Froude similarity: 0.9x and 1.1x walk the same motion (dt x sqrt s): distance/s, height/s within 1 %, steps within 1 % or one |
| 10 | `Gc` | brain + tick + bones allocate 0 after warm-up (positive control first) |
| 11 | `Perf` | `[Category("Perf")]` median tick + bones <= `PerfBudgetMs` (legacy default 0.1 ms) |
| 12 | `Lab` | habitat from the data (Plain, Climbable, Aviary, Grove); the enclosure's safe disc >= half a body length, or `FlightBrain.FitsAviary` |

RED proofs (`CreatureKitRedTests`): safe radius 0 trips the travel guard; a 1.0x individual claimed as
1.1x fails Size (ratio 0.954); an allocating tick counts 12000; an out-of-range skin index is reported.

Skips (`CreatureKitAssets.SkipReason`): cephalopod - checks 5-11 (OctopusCreature is not a CreatureSim;
its own Octopus*Tests until T1.2/T3.3); legless - Gait.

### Findings and known offline results (2026-10-18)

| test | kind | detail |
|---|---|---|
| `CreatureKitTests(WingedSerpent).Gait` | finding (Unity too) | a hind foot at full reach is dragged while the gait throttle holds the body at 0 in a weaving walk; Unity: weave t=3.60, foot 3 slid 0.574 mm |
| `CreatureKitTests(TestHexapod).Size` | finding (Unity too) | stop-go walk (27 %): Unity 5.1733 vs 5.3894 (4.2 % apart; 1.4 % offline) - test fixture |
| `CreatureKitTests(WingedSerpent).Size` | offline only | stop-go chaos: 6 % apart offline, PASSES in Unity (2026-10-18) |
| `CreatureKitTests(DesertMonitor).MaxBend`, `CreatureMonitorTests.Monitor_MaxBend_NoInvertedTriangles`, `CreatureMonitorTests.Monitor_TightTurn_LegsClearTheTrunk` | offline only | near-zero triangle / wander drift offline; all PASS in Unity (2026-10-18) |
| `CreatureKitTests(TreeOctopus).MeshTime` | watch | 5.9 and 8.4 ms vs the 5 ms limit in two Unity runs on a busy machine; recheck on a quiet one (Tarantula MeshTime/Perf failed once under load, passed on rerun) |

Unity 2026-10-18: CreatureKitTests 108 run (incl. the Perf cases, which cannot be excluded by group filter), CreatureKitRedTests 4/4, CreatureMonitorTests 12/12.


The monitor, beetle and spiders are exactly Froude-similar offline (identical normalised numbers at
0.8x..1.2x); the stop-go species are not, which is what the Size check exposes.

## Unity

- `creature_kit.py unity-compile` first (compiles Tests too; `compile_check.py` does not).
- One class per `run_tests` job: `TerrainGen.Tests.CreatureKitTests` (all fixtures), then
  `TerrainGen.Tests.CreatureKitRedTests`, then the Perf test separately (category Perf, quiet machine).
- Unity goldens differ from the harness's (`LegacyLegsGoldenTests` keeps both).
