# Vesper Step 1 (Skeleton) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A dedicated VesperLab scene where Vesper exists as a skeleton only (spine with a jointed head, hind legs, wing arms with 4 long finger chains + a forward thumb claw), drawn by F3, moved by the shared walking/flight systems, and commanded from an "M" menu.

**Architecture:** Vesper is a kit species (`Vesper.asset` from `Vesper.py`) on FlowBody (the chain), DrakeLeg (hind legs), Leg2Bone wing arms and a new `DigitWing : WingPart` whose runtime owns per-finger 3D chains (air flex, gravity droop, bend limits) on top of the flight system's finger directions. An opt-in "skeleton only" switch makes the renderer draw nothing. A `CommandBrain : ICreatureBrain` turns menu commands into flight/walk calls; a `VesperLab` MonoBehaviour spawns Vesper on flat ground with perch rocks and shows the M menu.

**Tech Stack:** Unity 6000.2.6f2 C#, NUnit EditMode tests, offline harness `Tools~/CreatureHarness` via `.claude/skills/creature-kit/scripts/creature_kit.py`, Python generator (`kityaml`), Unity MCP (port 8040) for the scene.

**Spec:** `docs/superpowers/specs/2026-10-21-vesper-skeleton-design.md` (incl. "Builder-check answers").

## Global Constraints

- Kit rules: namespace `CreatureKit`, `[Serializable]`, `[Part]`/`[Param]` on every public field, `Validate` returns null or the first problem naming `id`, `CopyArrays` clones arrays; author at scale 1 in metres; lengths × s, times × √s, Hz ÷ √s.
- Zero GC in `Step`/`WriteBones`/`EncapsulateBounds`/`DrawDebug`; main thread.
- Shared-system changes are opt-in data flags, off by default; every shipped species bit-identical (CreatureKitTests, LegacyLegsGoldenTests, mesh-bytes tests green).
- Each new invariant has a RED proof. Every new `.cs` has a Unity `.meta`.
- Old Input Manager (`Input.GetKeyDown`), IMGUI (`OnGUI`) for the menu, as OctopusLab/GrassLab.
- Unity MCP: verify `mcpforunity://instances` = `MarchingCubes@…` on 6000.2.6f2 before acting; port 8040.
- The Apex and every other species stay untouched.
- Commits end with `Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>`; parent-repo commits by path only.

## Review Focus

1. **A command given mid-transition** (e.g. "Walk" during Launch, "Fly" during Touchdown, "Perch" with no reachable perch): the brain must queue or redirect, never stall or snap. Test in Task 4 (`Command_DuringTransition_Completes`, `Perch_NoPerch_FallsBackToLand`).
2. **Size jitter / scale changes** (respawn at another scale from the Inspector): finger chains keep Froude timing and length scaling. Test in Task 2 (`DigitWing_Froude`).
3. **Folded fingers on the ground while the wrist is planted**: droop must never pull the planted wrist or push a finger into the ground. Test in Task 2 (`DigitWing_Folded_DroopsAboveGround_WristPlanted`).
4. **Pressing M while the menu is open / during play-mode respawn**: the menu toggles cleanly and survives a respawn. Test in Task 5 (`Lab_Respawn_KeepsMenuAndCommand`, EditMode-testable logic in a plain class).
5. **F3 with Vesper while other creatures exist**: Vesper's digits are drawn; other species unaffected (part runtimes already go through `DrawDebug`). Test in Task 2 (`DigitWing_DrawDebug_DrawsEveryJoint`).

---

## File map

| File (relative to `Assets/TerrainGen/`) | Responsibility | Task |
|---|---|---|
| `Scripts/Creatures/CreatureSpecies.cs`, renderer path (`CreatureRenderer.cs` or `CreatureWorld.cs`), `Tests/EditMode/CreatureKitAssets.cs` | opt-in `skeletonOnly`: no draw; kit skip reasons | 1 |
| `Scripts/Creatures/Kit/DigitWing.cs` (+ runtime) | `DigitWing : WingPart` + `DigitWingRuntime` finger chains | 2 |
| `Tools~/SpeciesGen/Vesper.py`, `Config/Creatures/Vesper.asset(.meta)` | the species | 3 |
| `Scripts/Creatures/CommandBrain.cs` | menu commands -> sim/flight calls | 4 |
| `Scripts/Creatures/VesperLab.cs`, `Scripts/Editor/...BuildVesperLab` (editor menu), `Assets/Scenes/VesperLab.unity` (parent repo) | scene, spawn, perches, M menu | 5 |
| tests `Tests/EditMode/Creature{SkeletonOnly,DigitWing,Vesper,CommandBrain,VesperLab}Tests.cs` | | 1-5 |

---

### Task 1: Skeleton-only species (no draw) + kit skip reasons

**Files:** Modify `Scripts/Creatures/CreatureSpecies.cs` (field), the place the world/renderer builds and draws a species mesh (find via `CreatureWorld.Spawn` -> `CreatureRenderer`), `Scripts/Creatures/Kit/Modules.cs` or a new look module `SkeletonOnly` (choose: a `[Module("SkeletonOnly", Look)]` that sets `CreatureSpecies.skeletonOnly` in `Configure`), `Tests/EditMode/CreatureKitAssets.cs` (`SkipReason`). Test: `Tests/EditMode/CreatureSkeletonOnlyTests.cs`.

**Interfaces — Produces:** `public bool CreatureSpecies.skeletonOnly` (default false, not serialized by legacy assets); module `CreatureKit.SkeletonOnly` (no fields) whose `Configure(CreatureSpecies)` sets it true; skip reason string `"skeleton only: no skin until step 3"` for checks MeshTime, MaxBend, Bounds, PoseSweep, Group.

- [ ] **Step 1: Tests** — `SkeletonOnly_SpawnsAndTicks_DrawsNothing` (a FlowKit species + SkeletonOnly: world spawn works, the renderer issues no draw for it / builds no mesh; sim ticks 120 frames); `SkeletonOnly_Off_ShippedUnchanged` (DesertMonitor's mesh bytes unchanged — reuse the mesh-bytes helper); `Red_SkeletonOnly_Ignored` (flag set but renderer path forced to draw via a test hook → the draw-count assertion fails).
- [ ] **Step 2:** run → FAIL. **Step 3:** implement the module, the flag, the renderer/world skip (opt-in, no change when false), the `SkipReason` entries. **Step 4:** run the new tests + `CreatureKitTests` + `CreatureMeshEmitterTests` + `LegacyLegsGoldenTests` → PASS. **Step 5:** commit `feat(creatures): skeleton-only species (opt-in, no draw) + kit skips`.

### Task 2: DigitWing — the wing as finger chains

**Files:** Create `Scripts/Creatures/Kit/DigitWing.cs` (part + `DigitWingRuntime`), `Tests/EditMode/CreatureDigitWingTests.cs`.

**Interfaces:**
- Consumes: `WingPart` (`arm`, `spec`, `FlightBones`), `CreatureWings` state (finger directions, fold, `ThumbTip`), `CreatureFlight` (`Mode`, `AirWeight`), `AngleChain` if useful, `FlowKit` helpers (`Tests/EditMode/CreatureFlowFixtures.cs`).
- Produces: `[Part("DigitWing", PartKind.Wing)] public sealed class DigitWing : WingPart` with fields `fingerSegments` (int, default 4), `fingerRadius` (m, root radius per finger, `float[]` one per finger, default {0.018, 0.016, 0.014, 0.012}), `fingerTaper` (0.4), `flexDeg` (max air bend per joint, 10), `flexHz` (2), `flexDamping` (0.5), `droopDeg` (max gravity droop per joint on the ground, 8), `maxBendDeg` (25), `thumbLength` (m, 0.08), `thumbCurlDeg` (40), `thumbSegments` (2); `BoneCount = FlightBones + fingers × fingerSegments + thumbSegments`. `public sealed class DigitWingRuntime : IPartRuntime` (stage Late) exposing `Vector3 Joint(int finger, int k)` (world), `int Fingers`, `int Segments`, `float BendDeg(int finger, int k)`; `DrawDebug` draws every finger joint and segment and the thumb claw (with a small circle per joint at its radius). No mesh (`EmitMesh` emits nothing).
- Finger roots at the wrist; each finger's rest direction = the flight system's finger direction (spread in the air, folded on the ground) from `CreatureWings`; each joint follows the previous one with a damped 3D spring (air: driven by the beat's angular rate — lag; gliding: a small billow up), plus gravity droop on the ground (toward world down, limited by `droopDeg`, never below the ground plane + finger radius), all clamped by `maxBendDeg`. The thumb claw: `thumbSegments` short bones from the wrist pointing forward (along the arm's forward/leading side), curling down by `thumbCurlDeg`.

- [ ] **Step 1: Tests** (fixture: a FlowKit species with FlowBody, Leg2Bone wing arm, DigitWing mirrored, DrakeLeg, Walk + Fly + FlightExcursion, SkeletonOnly): `DigitWing_Bones_Layout` (bone count, contiguous, skinning not required); `DigitWing_FlyingFingersLag` (outer joint's bend peaks after the root's in steady beating by ≥ 0.05 beat); `DigitWing_Folded_DroopsAboveGround_WristPlanted` (wing-walk 10 s: every finger joint above ground + radius; tips lower than with droop 0 by ≥ 1 cm × s; the planted wrist/ThumbTip drift < 1 % of arm length); `DigitWing_BendLimits` (|bend| ≤ maxBendDeg through launch/beat/glide/touchdown); `DigitWing_Froude` (0.9× / 1.1× bend curves equal in Froude time within 2 %); `DigitWing_NoGC`; `DigitWing_DrawDebug_DrawsEveryJoint` (a recording `ICreatureDebugDraw` gets ≥ fingers × segments + thumb lines); REDs: `Red_DigitWing_Stiff` (flexDeg 0 → lag test fails), `Red_DigitWing_NoDroop` (droopDeg 0 → droop test fails), `Red_DigitWing_IntoGround` (ground clamp off via hook → above-ground fails).
- [ ] **Step 2:** run → FAIL. **Step 3:** implement. **Step 4:** run new tests + `CreatureKitTests` → PASS. **Step 5:** commit `feat(kit): DigitWing - wing arms with long finger chains (air flex, gravity droop) and a forward thumb claw`.

### Task 3: The Vesper species

**Files:** Create `Tools~/SpeciesGen/Vesper.py`, `Config/Creatures/Vesper.asset` + `.meta` (fresh GUID), `Tests/EditMode/CreatureVesperTests.cs`.

**Interfaces:** Consumes Tasks 1-2, FlowBody, DrakeLeg, Leg2Bone, Eyes (required by compose), modules Walk, Fly (with the Apex's proven flight flags `airNeckStance`, `launchHeadOnNeck`, `touchdownAtStance`, `launchTailBySegment` as needed), QuadLaunch, SkeletonOnly. Produces `CreatureVesperTests.Vesper()` loader.

- [ ] **Step 1: Write `Vesper.py`** (from scratch with `kityaml`; numbers may start from `Tools~/SpeciesGen/Apex.py`'s skeleton numbers, nothing visual): FlowBody chain head-tip..tail-tip (head = first 3-4 joints with tight `bendLimitDeg` ≤ 6°, `rigidHeadJoints` 0; raised neck; long tail), per-joint radii (halfWidth/halfHeight as the future skin), Leg2Bone wing arm (upper ≈ 0.4 × forearm, the Apex's proven pole/restOffset), DigitWing (4 fingers, fingerLengths long — the 4 fingers span the wing — + thumb), DrakeLeg hind legs, Eyes on the head joint, scale ≈ 4, modules above. Run it; `creature_kit.py species` loads.
- [ ] **Step 2: Tests:** `Vesper_Composes` (one FlowBody, two DigitWing with 4 fingers + thumb, two DrakeLeg, two wing-arm Leg2Bone, SkeletonOnly; head joints' bend limits ≤ 6°); `Vesper_WalksOnFoldedWings` (walk 20 s: wing wrists plant, hind feet plant, kit Gait clean); `Vesper_FliesAndLands` (from the ground under FlightBrain reaches launch/beat/glide/flare/touchdown/wing-walk within 120 s·√s); `Vesper_Bob` (girdle p-p ≥ 0.06 × body length, head ≤ ⅓ of it); `creature_kit.py check Vesper` green with the skeleton-only skips; REDs where a threshold is new.
- [ ] **Step 3:** tune `Vesper.py` until green. **Step 4:** commit `feat(creatures): Vesper - skeleton-only species (FlowBody, DigitWing, DrakeLeg)`.

### Task 4: CommandBrain — the menu's commands

**Files:** Create `Scripts/Creatures/CommandBrain.cs`, `Tests/EditMode/CreatureCommandBrainTests.cs`.

**Interfaces — Produces:** `public enum CreatureCommand { Stand, WalkAround, WalkTo, Fly, Circle, Land, Perch }`; `public sealed class CommandBrain : ICreatureBrain` with `CommandBrain(EnclosureArea area, int seed)`, `void Command(CreatureCommand c, Vector3 point = default)`, `CreatureCommand Current { get; }`, `string Doing { get; }` (human-readable state, e.g. "landing to walk"), `Vector3 Target(CreatureSim sim, float dt)`. Uses only `CreatureFlight` public calls (`Launch`, `SteerTo`, `SetGoals`, `Land` incl. perch `source/axis`, `CancelLanding`, `Mode`) and `sim.Halt`. Perch spots: scan `CreatureSurfaces` / `PhysicsSurfaceProbe` like `FlightBrain.ChoosePerch` (copy the minimal logic, do not refactor FlightBrain); if none reachable → `Land` on open ground and `Doing` says so.
- Walk commands while airborne → land first, then walk; Fly while walking → Launch then SteerTo; Circle → steady bank circle of radius ≥ the flight's turn radius inside the area; Stand → Halt (on the ground) or land then Halt (in the air); WalkTo(point) → walk to the point's ground projection, then Stand.

- [ ] **Step 1: Tests** (Vesper from Task 3 or the Task 2 fixture): one test per command from both ground and air start (`Command_<X>_FromGround`, `_FromAir`) asserting the end state within a Froude time bound (e.g. Fly → Air within 10 s·√s; Land → Ground; WalkTo → head within 1 body length of the point; Stand → speed < 2 % body length/s; Circle → ≥ 1 full turn, altitude band, inside the area; Perch with a rock collider → Perched); `Command_DuringTransition_Completes` (Walk during Launch, Fly during Touchdown); `Perch_NoPerch_FallsBackToLand`; `CommandBrain_NoGC`; REDs: a brain ignoring transitions (hook) fails `_FromAir` walk.
- [ ] **Step 2-4:** FAIL → implement → PASS. **Step 5:** commit `feat(creatures): CommandBrain - Stand, WalkAround, WalkTo, Fly, Circle, Land, Perch with natural transitions`.

### Task 5: VesperLab scene + M menu

**Files:** Create `Scripts/Creatures/VesperLab.cs` (runtime MonoBehaviour), `Scripts/Creatures/VesperLabMenu.cs` (plain class: menu state, testable), an editor menu `Marching Cubes/Build Vesper Lab` (in the Editor assembly folder the project uses for `Rebuild Creature Lab`), `Tests/EditMode/CreatureVesperLabTests.cs`; then (Unity, via MCP) `Assets/Scenes/VesperLab.unity` in the parent repo.

**Interfaces:** Consumes `CreatureWorld` (`SetGround(new FlatGroundProbe(0), null)`, `Spawn(sp, pos, fwd, brain, area, seed)`), `EnclosureArea.For`, `CreatureDebugView` (F3, `show` default on in VesperLab), `CommandBrain`, `SimplePlayerController` (or an orbit camera), perch objects with colliders on the flight system's surface mask (`GroundSource.Physics` per the recon). Produces `VesperLab` fields: `species` (Vesper.asset), `scale` (0 = asset), `seed`, `menuKey` (KeyCode.M), `perchCount` (3). `VesperLabMenu`: `bool Open`, `void Toggle()`, `void Pick(CreatureCommand c)`, `string Status`.

- [ ] **Step 1: Tests (EditMode, plain logic):** `Menu_Toggle_OpenClose`, `Menu_Pick_SendsCommand` (the brain's `Current` changes), `Lab_Respawn_KeepsMenuAndCommand` (respawn on species edit keeps the selected command), `Lab_Spawns_OnFlatGround_InsideArea`.
- [ ] **Step 2-4:** FAIL → implement (`VesperLab`: Awake builds world ground + area + perches (3 rock/post GameObjects with colliders), spawns Vesper with a `CommandBrain`; Update: M toggles the menu; OnGUI: buttons for each command + "Doing: …" + F3 hint; respawns when the species asset changes in play mode, as the lab does) → PASS.
- [ ] **Step 5: Editor menu** `Build Vesper Lab`: creates `Assets/Scenes/VesperLab.unity` with camera (player controller), directional light, URP volume copied like the Creature Lab builder, ground plane visual, a `Creatures` object with `CreatureWorld` (material assigned), `CreatureDebugView` (show = true), `VesperLab`. Offline: `unity-compile`. Commit `feat(creatures): VesperLab - one Vesper, flat ground, perches, M menu; Build Vesper Lab menu`.
- [ ] **Step 6 (controller, Unity via MCP):** verify the instance; run `CreatureSkeletonOnlyTests`, `CreatureDigitWingTests`, `CreatureVesperTests`, `CreatureCommandBrainTests`, `CreatureVesperLabTests`, `CreatureKitTests` (one class per job); execute `Marching Cubes/Build Vesper Lab`; open the scene; commit `Assets/Scenes/VesperLab.unity` (+ .meta) in the parent repo by path; hand-off note: press Play, F3 skeleton, M menu, what to look at (spine/head joints, finger chains flex and droop, thumb claw, walking on folded wings, the bob), and the Inspector numbers to change.
