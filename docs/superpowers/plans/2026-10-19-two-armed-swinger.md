# Two-armed swinger Implementation Plan

> **For agentic workers:** executed natively by the implementer (superpowers:executing-plans), TDD per task. Steps use checkbox (`- [ ]`) syntax.

**Goal:** A second cephalopod species ("Swinger"): small body, two long arms that brachiate, 4-6 short mouth tentacles that only feed, hunting small tree-climbing spiders in its own lab grove — on the SAME octopus code path.

**Architecture:** Generic, data-backed, additive changes to the octopus core (`CephalopodSpec` gets `minHolds`, `mouthCount`, `mouth`, `form`); a mouth-tentacle set in `OctopusBody` (one-way coupled chains, bones in the Body block after the 6 soft bones); a `MouthFeeder` the controller ticks only when the body has mouths; `OctopusBrain` gets a creep-and-feed path used only with a feeder. 8-arm TreeOctopus untouched (mouthCount 0 → identical code paths, goldens unchanged).

**Tech Stack:** Unity 6000.2.6f2 C# (TerrainGen.Runtime), offline harness `creature_kit.py test`, `compile_check.py`, `creature_kit.py unity-compile`.

**Spec:** `docs/superpowers/specs/2026-10-19-two-armed-swinger-design.md`

## Global Constraints

- Not the creature kit authoring flow; octopus code path + species data (`Config/Creatures/Swinger.asset`, `TreeSpider.asset`).
- Octopus-core changes generic, minimal, additive (another agent edits ArmCoordinator/OctopusBody/OctopusController/TentacleAgent on feat/octopus-coordination).
- Contact only on real geometry; size = species.scale × look.sizeJitter; timing ∝ √scale; zero GC per tick; offline only.
- F3 + Show Roles readout works for it (mouth tentacles show role Feed).

## Review Focus

- Both arms holding when one is told to let go by strain / overload / spread: must never reach zero holds while hanging → `Swinger_TwoArmGrip_NeverZeroHolds` runs travel + idle + feeding.
- A prey that moves away mid-creep: brain gives up / re-stalks, never strikes with arms → feeding test asserts no arm ever in `Strike`.
- Body overload pin release (`ReleaseOverloadedPins`) on the last hold → guarded by minHolds in the same test.
- Sizes 0.9×/1.1× of the species scale behave the same → size test.
- Existing species: octopus classes + goldens unchanged → full harness diff vs baseline (647 pass / 3 known octopus failures).

---

### Task 1: Spec fields + two-arm grip rule
**Files:** Modify `Scripts/Creatures/Octopus/OctopusSpecs.cs`, `OctopusController.cs` (ctor: `Board.MinAnchorsHanging = spec.MinHolds`), `OctopusBody.cs` (overload release only while another arm holds when MinHolds == 1). Test: `Tests/EditMode/SwingerTests.cs`.
- Produces: `CephalopodSpec.minHolds/MinHolds (0 → 2)`, `SwingerTests.Spec()` (2 arms, minHolds 1, small body).
- [ ] RED `Swinger_TwoArmGrip_NeverZeroHolds`: bars 1 arm-length apart, travel 40 s√s at scale 1: holds never 0 after spawn anchoring, ≥ 2 transfers.
- [ ] GREEN, run octopus classes unchanged, commit.

### Task 2: Brachiation progress
- [ ] RED `Swinger_Brachiates_AcrossGrove` (OctopusGroves.Row with hints, goal in the far tree, ≥ 2 of 3 layouts arrive in 30 s√s, never zero holds). GREEN by tuning the species/defaults only through data (`minHolds`) or generic two-arm fixes in the coordinator (arms − 4 hang rule already gives 1+1 groups). Commit.

### Task 3: Mouth tentacles (body + bones + mesh)
**Files:** `OctopusSpecs.cs` (`mouthCount`, `mouth` TentacleSpec, `mouthRing`), `OctopusShape.cs` (`MouthRoot/MouthDir/MouthRot`), `OctopusBody.cs` (`Mouth[]`, `MouthCount`, `MouthBone(m,k)`, `BoneCountFor`), `OctopusMeshBuilder.cs` (`Mouth(m)` tube), `Kit/Parts.cs` (`SoftBody.BoneCount = 6 + mouth bones`).
- Bone layout: arms, 6 soft, mouth (m × MouthSegments), eyes, siphon (octopus: mouthCount 0 → unchanged).
- [ ] RED `Swinger_Mouth_BonesAndMesh` (bone count, mesh skin indices in range, bind × world = I, mouths follow body). GREEN. Commit.

### Task 4: Feeding with mouth tentacles only
**Files:** Create `Scripts/Creatures/Octopus/MouthFeeder.cs`; modify `OctopusTypes.cs` (`ArmRole.Feed` appended, `OctopusEvents.Eaten`), `OctopusController.cs` (`Feeder` ticked if non-null), `OctopusBrain.cs` (stalk → creep → feed → eat when `c.Feeder != null`).
- [ ] RED `Swinger_Feeds_WithMouthTentaclesOnly`: prey on the bar 1.5 L away: seen, approached, grabbed by a mouth tentacle, `Eaten` fires; no arm ever in Strike; holds never 0. GREEN. Commit.

### Task 5: Species, size, GC
**Files:** `Config/Creatures/Swinger.asset` (+meta), `form` look switch in `KitRender`/`CreatureRenderer` if needed.
- [ ] RED `Swinger_Asset_Loads` + `Swinger_SizeVariation_0_9_1_1` (brachiation at 0.9/1.1 × scale) + `Swinger_NoGc`. Kit check `creature_kit.py check Swinger`. GREEN, commit.

### Task 6: Climbing prey spiders + lab grove
**Files:** `Config/Creatures/TreeSpider.asset` (small arthropod, `climb.canClimb`), `OctopusLab.cs` (prey count, prey climb on grove trunks, eaten → respawn), `CreatureLabRoster.cs`/`CreatureLab.cs`/`Editor/CreatureLabScene.cs` (every grove species gets its own OctopusLab, placed one after another).
- [ ] RED `TreeSpider_ClimbsTrunk` (ClimbingBrain on a cylinder: head rises ≥ 1.5 m, feet on the bark). If climbing fails: spiders on branch tops, documented. GREEN, commit.

### Task 7: Verify + hand-off
- [ ] Full harness vs baseline, `compile_check.py`, `unity-compile`, catalogue fresh; F3/roles readout prints mouth roles. NEEDS_EDITOR report with the Unity checklist.
