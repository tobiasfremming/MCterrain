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
| 13 | `PoseSweep` | the mesh skinned through **every phase** its own brain and modules reach (`CreatureKitPoseSweep.cs`): no inverted triangle, no vertex normal flipped against its triangle or pinched (< 0.2) where the bind was clean, no spine kink (> limit + 45 deg); every required phase reached |
| 14 | `Group` | a roster group (`count` > 1), spawned as the lab does (`LabGroup`), own brains, 3 min: no two members' fitted capsules (`BoneCapsules`) overlap while in sight (`CreatureKitGroupCheck.cs`) |

`Gait` (8) also checks the **drawn** feet (kit services): each planted walking leg's drawn tip - the rest foot carried by
the leg's last bone; a wing-walking arm's thumb claw (`CreatureWings.ThumbTip`) - drifts < 1 % of the leg's length from
its sim foot over a plant (a part that re-poses leg bones after CreatureLegs could otherwise slide in the picture; a
Tuck's curl is exempt). MaxBend's message names the part (`KitPoseSweep.BonePart`) and the vertex positions.

### The pose sweep (check 13)

- Driver: `KitPoseSweep.Run(sp, scale, seed)` - its lab area (aviary for a flyer), `BrainFactory` (the species' own
  behaviours: FlightBrain, a ModularBrain with SkyHunt / Burrow / School ...), 1/60 s ticks; samples at 10 Hz and every
  frame for 0.6 s (x sqrt s) after a phase change. Adaptive length: >= 90 s, until every required phase is seen + 30 s,
  at most 360 s (Froude seconds).
- Phases: `CreatureKit.PosePhases` (Kit/Services) - channels over the shipped systems (flight: wing-walk, launch, beat,
  glide, flare, touchdown; soar: beat, glide (+barrel, loop); hunt: stoop, pull-up; burrow: dig-in, dive, under, rise
  (+to-hole, lunge); tuck: curling, curled, uncurling (+peeking); display: rearing, display; stumble; labels only:
  tongue, jaw, tendril). **A new system with phases implements `IPosePhases`** (runtime, locomotion mode or behaviour;
  `PhaseRequired` marks what the sweep must reach) and gets the sweep for free.
- Reports: `inverted: flight=launch t=17.43 s: triangle 17608 of wing.R bone 4 (bones 49/49) at (...) (...) (...)`.
  The full list per phase: `creature_kit.py stats <Species>` (last lines) or `KitPoseSweep.Run(..., stopAtFirst: false)`.
- First-run findings (2026-10-20, kKnown): a sail-wing flyer (launch: wing bone mirrored, fixed by fanRearRollsWithFan), Delver (dive / lunge / rise: neck blend),
  Hexadrake (launch elbow, shoulder triangle in every flight phase, 64 deg kink), KomodoDragon (tongue fork sliver),
  SkyDragon (shoulder blends in launch / beat / flare, touchdown), WingedSerpent (shoulder blend, touchdown 75 deg kink);
  drawn feet: thumb claws on the sail-wing flyer and WingedSerpent skated 3-4 %; groups: RockCrab, Delver, ShaggyMonitor members touch
  (walking brains have no separation - `KitGroup` + `Separation` are the fix's service).

RED proofs (kit services): the manta's body mirrored only while gliding is reported with `soar=glide` and a part
(MaxBend never flies); a 5 s Hexadrake run reports the phases it never reached; the strider's unpinned tips fail the
drawn-feet rule; five crabs steered into one point touch.

### Material slots (kit services)

`CreatureMaterialSlotsTests`: every shipped species keeps the legacy ids (no named kind, table = registry + Layers rows
by part id, every part id its mesh emits counted as used); a species-local kind takes the lowest free kit slot and its
vertices and Layers row use it (KitMonitor + a test patch: slot 10); too many kinds is reported. Kit `Validate` (check
1) also asserts `MaterialSlots.For(sp).Problem` is null.

### Apex redesign lessons (feat/apex-v3, 2026-10-21)

- **One bind source: `CreatureRestPose.BindSim(sp, wings)`.** The rest sim with `StraightenBind` for a tall-stance winged
  species. `PartMeshEmitter.Rest`, `BoneWorld`, `WingedMeshBuilder.RestBoneWorld` and surface parts (Dewlap via
  `PartMeshEmitter.ForBind`) all use it; a part building rest geometry from `CreatureRestPose.Sim` drifts off the drawn body
  (`Red_Dewlap_PlainRestGeometry`). A `restAtSpacing` species (FlowBody `restAtStance`) is not straightened; its rib rest
  lengths come from `CreatureSim.RestRun`.
- **`RestMeshCache`** (`Kit/Services`): surface parts record the rest mesh they emit and replay it when the data is the same.
  Key = `RestMeshCache.MixData(part)` (reflection over serialized data, plus the body for PitRow/Dewlap, rest joints, bind
  bones, test hooks): a new serialized field needs no key edit, a non-serialized input does. Cap 64 entries, cleared when full.
  Open: `MixData` type gaps, replay remap untested. RED `Red_OneKey_StaleMesh`.
- **Steep raised neck + winged body: three flips, four opt-in `FlightSpec` flags** (default off; `FlyModule()` in
  `CreatureFleshWingTests` sets them; each has a RED with the flag off):
  - `launchHeadOnNeck`: neck front (joints 0-1) inverted in launch/climb-out (the walking frames put bone 0 level).
  - `airNeckStance` 0..1: AirChain cones keep that share of the stance bends. 0-0.15 keel seam flips (joints 6-7), 0.95+ the
    back under the hump flips, 0.2-0.9 clean. Head target stays on the flight line. AirTwist ignores it.
  - `touchdownAtStance`: a ground landing lays the body at its stance (+ `CreatureLegs.HoldDroop`); else a 28-56 deg chest kink.
  - `launchTailBySegment`: a launch from standing or a circling walk lerped two far-apart tail curves, `Relength` then folded
    the tail 90-178 deg (hundreds of inverted triangles, ~0.4 s). Segments are now slerped, held in `AirChain.ConeAt`, tail
    bones get transported frames. Side effect: a walking tail already over its limit pops ~1 deg at launch tick 1.
- **A bob needs beats.** `kLift >= 0.3` with `kGrip >= 0.7` settles into a glide (0 beats); `kLift <= 0.2, kGrip 0.4` cannot leave
  ground effect. Measure girdle p-p, head/girdle ratio and the tail lag (signed per-station lags, each step in (0, 0.45) beat).
- **Named-kind slots:** `CreatureMaterialSlotsTests.NamedSlotRowProblem` asserts each named slot's row (Layers row, else the kind's
  default, else legacy); `kNamedKindSpecies` lists species allowed named kinds (Apex).
- **Look is tested, each with a RED:** closed solids (2 triangles per edge), crest ripple/outline, `SteepProblem` / `BroadProblem`
  on the species, `Head_OpenMouth_OnlyMouthInside` (63 rays), `InsideMouthProblem(walkSeconds)` for a walking pose,
  `Dewlap_HeavyBob_RimNeverTurnsOver`, `Tail_NoKink`. Test hooks: `internal static ...ForTest`, reset in `finally`.
- **KNOWN FINDING, fix flag exists but is OFF:** `WingedSerpent` (standing launch) and `Hexadrake` (standing and circling) fold
  their tail on launch (166 deg over the limit; 328 / 587 inverted body triangles). `launchTailBySegment` cleans the body but
  raises WingedSerpent's limb inversions 46 -> 116 (WingedSerpent part 8 bones 47/48 and Hexadrake part 1 bones 38/39 already
  invert at launch tick 5; SkyDragon's twist chain 15-574). Needs its own look before turning the flag on. User wants a reminder.
- Unity still owes: `CreatureKitTests(Apex)`, `CreatureApexTests`, `CreatureDewlapTests` (long chaotic runs; Mono floats may diverge).

### Pops: per-tick jumps (Vesper task D, feat/vesper, 2026-10-21)

Measure the largest per-tick step of the head and the girdle (ticks inside one mode, and through each transition): a pop
is a step many times the girdle's. Two opt-in `FlightSpec` flags (off = shipped flyers bit-identical; on for Vesper):
- `headStabiliseBounded`: the AirChain head stabiliser filters only the vertical bob over `headStabilise`, turns and the
  trunk's lead direction over 0.15 s, its smoothed girdle within 0.25 neck lengths, the target within 40 deg of the trunk.
  Off, `smoothPos` trails a turn by ~v x tau (14 m on Vesper's 4.4 m neck at headStabilise 1.2; 8.9 m on the Apex at 0.6)
  and `Contain()` cuts the outward velocity (the trunk's leader turned 62 deg in a tick): the bend-limited neck flips.
  Vesper 7.45 -> 0.48 m (girdle 0.13); **shipped flyers have it too (flag off)**: Apex 4.3 m, Hexadrake / WingedSerpent
  0.7 m on a 0.5 m neck; Pterodactyl and SkyDragon (twist) clean. Lowering headStabilise alone does not fix it (0.15: 2.5 m).
- `touchdownFromHover`: `BeginTouchdown` on a tick's last sub-step showed the walking restart's laid body (perch: girdle on
  the point; touchdownAtStance: the stance) for one tick, the blend carried it back the next. Rock perch girdle 2.9 m /
  1.6 m -> 0.33 / 0.41 m, open-ground head 2.4 m -> 0.15 m. Affects every perching flyer and the Apex (flag off).
- Still open: on a rock perch the draped tail tip swings up to 7 m in one tick late in the touchdown (Drape over the edge).
Tests: `CreatureVesperTests.Vesper_Flight_NoHeadJump`, `Vesper_Touchdown_NoGirdleJump` (+ REDs).

### Debugging tools (offline)

- `creature_kit.py stats <Species>`: speed (m/s, Froude), steps/s, duty, lift / L and step time (Froude) per leg, rest
  reach share and IK s / pitch, bob, mesh size and build time, tick cost, the phases it reaches, the sweep's verdict.
- `creature_kit.py trace <Species> [--phase touchdown] [--part neck] [--out f.csv]`: the bone trace - a CSV row per
  tick of its own run: spine bends, the part's bones (position, forward, up, scale, det < 0 = mirrored). Replaces the
  hand-written joint dumps.
- `creature_kit.py render <Species> [--phase launch,glide] [--out DIR]`: pose-dump (OBJ per phase, colours from the
  species' look and Layers) + `Tools~/CreatureLook/render.py` (painter, back-face culling, ground). Replaces the scratch
  render2.py / PoseDump.cs copies.

RED proofs (`CreatureKitRedTests`): safe radius 0 trips the travel guard; a 1.0x individual claimed as
1.1x fails Size (ratio 0.954); an allocating tick counts 12000; an out-of-range skin index is reported.

Skips (`CreatureKitAssets.SkipReason`): cephalopod - checks 5-11, 13, 14 (OctopusCreature is not a CreatureSim;
its own Octopus*Tests until T1.2/T3.3); legless - Gait.

### Findings and known offline results (2026-10-18)

| test | kind | detail |
|---|---|---|
| `CreatureKitTests(WingedSerpent).Gait` | finding (Unity too) | a hind foot at full reach is dragged while the gait throttle holds the body at 0 in a weaving walk; Unity: weave t=3.60, foot 3 slid 0.574 mm |
| `CreatureKitTests(TestHexapod).Size` | finding (Unity too) | stop-go walk (27 %): Unity 5.1733 vs 5.3894 (4.2 % apart; 1.4 % offline) - test fixture |
| `CreatureKitTests(WingedSerpent).Size` | offline only | stop-go chaos: 6 % apart offline, PASSES in Unity (2026-10-18) |
| `CreatureKitTests(DesertMonitor).MaxBend`, `CreatureMonitorTests.Monitor_MaxBend_NoInvertedTriangles`, `CreatureMonitorTests.Monitor_TightTurn_LegsClearTheTrunk` | offline only | near-zero triangle / wander drift offline; all PASS in Unity (2026-10-18) |
| `CreatureKitTests(TreeOctopus).MeshTime` | watch | 5.9 and 8.4 ms vs the 5 ms limit in two Unity runs on a busy machine; recheck on a quiet one (Tarantula MeshTime/Perf failed once under load, passed on rerun) |

Archetype classes (offline, 2026-10-20, feat/arthropod-archetype): `CreatureArchetypeTests` (spider form = Tarantula
parity incl. rest stance s/pitch and gait numbers; every form's legs stand in their rest shape; override by id and
`.L`/`.R`; legPairs 1/6, bad formula, posture bounds, short legs = compose errors; generated Tuck last; the shipped
crabs come from the plan, stand unbent, walk sideways; the stone crab compact and its tuck derived),
`CreatureSidewaysTests` (travel along the lateral axis at 0.9/1/1.1x, RED forward travel, the kit gait check, side
flips without foot slides, turn about the middle, forward shuffle at the forward factor, containment 0.9x/1.1x,
Froude size, rigid body required). `CreatureTuckTests`: a limb root that plugs in under the shell (a crab's basis, a
cheliped's merus) may sink no deeper than it sits standing (+2 mm); free segments keep the 1.2 cm bound.

Phase 5 classes (offline, 2026-10-19): `CreatureWaveGaitTests` (lift-off order 100 %, duty factor 1 - 1/G at
0.9/1/1.1x, never two neighbouring feet of a side in the air, RED event-driven 19 %), `CreatureHexadrakeTests`
(Folded compose, never plants, no membrane flips + steady folded fingers, flies/lands/folds again, RED),
`CreatureTendrilTests` (socket, drawn stretch, touch/hold/let go, settled hold still, Froude, no inverted tube,
RED), `CreatureTuckTests` (RockCrab: Tuck + EyeStalk + the sim's posture inputs - tucked and asleep within
curlSeconds + 0.2 s, 0 change per frame tucked, nothing out of the shell at 0.9x/1.1x, no inverted triangle through a
whole cycle, uncurl walks on, Froude frames equal, random scares staggered, no GC; RED walking moves / standing pokes
out). Perf (.NET): RockCrab 21 us walking (tucked: asleep, less), GiantCentipede 46-48 us (42 arthropod legs; Mono may approach the 0.1 ms default),
TentacleCrab 34-41 us, Hexadrake 17-20 us.

Unity 2026-10-18: CreatureKitTests 108 run (incl. the Perf cases, which cannot be excluded by group filter), CreatureKitRedTests 4/4, CreatureMonitorTests 12/12.


The monitor, beetle and spiders are exactly Froude-similar offline (identical normalised numbers at
0.8x..1.2x); the stop-go species are not, which is what the Size check exposes.

## Unity

- `creature_kit.py unity-compile` first (compiles Tests too; `compile_check.py` does not).
- One class per `run_tests` job: `TerrainGen.Tests.CreatureKitTests` (all fixtures), then
  `TerrainGen.Tests.CreatureKitRedTests`, then the Perf test separately (category Perf, quiet machine).
- Unity goldens differ from the harness's (`LegacyLegsGoldenTests` keeps both).
