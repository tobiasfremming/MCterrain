# Creature Kit: implementation plan

Spec: `docs/superpowers/specs/2026-10-18-creature-kit-design.md`.
Base: feat/creature-integration after the legs merge is committed (nothing starts until `git -C Assets/TerrainGen status` is clean).
Branch: `feat/creature-kit`, worktree `unity_stuff/wt/kit/Assets/TerrainGen` (ProjectSettings + Library/ScriptAssemblies junctions; never inside Assets/).
Rules: small commits; RED first; `compile_check.py --root wt/kit` + harness green before any Editor visit; every existing test and the golden hashes stay green; Unity: one test class per run_tests job; parent repo stages only docs, the submodule pointer and (with the user's go-ahead) `CreatureLab.unity`.
Legend: [P] offline / parallel worktree · [E] needs the Editor (serialised by the controller) · User: what the user looks at.

## Phase 0: tooling, no shared files (can start now)

- **T0.1 [P] Checked-in offline harness.** `Tools~/CreatureHarness/{csproj, Stubs/*.cs, MiniNUnit.cs, Program.cs}`, `.claude/skills/creature-kit/scripts/creature_kit.py` (`check`, `test <Class>`, `--real-unity`). Globs `Scripts/Creatures/**/*.cs` minus a documented exclude list; tests behind `#if !CREATURE_HARNESS_EXCLUDE`. Runs CreatureSimSpineTests, CreatureLegTests, ArthropodIKTests, LegacyLegsGoldenTests; RED: a deliberately wrong golden fails, then removed.
- **T0.2 [P] Generic kit fixture over the legacy fields.** `Tests/EditMode/CreatureKitTests.cs`, `CreatureKitAssets.cs` (asset discovery; harness reads YAML through the same loader). The 12 generic checks (spec §3c), per-species skip list with reasons. RED proofs: wander with safe radius 0; size variation with sizeScale 1 vs expected 1.1; GC positive control. [E] once: CreatureKitTests, then perf separately.
- **T0.3 [P] Skill skeleton** `.claude/skills/creature-kit/` (spec §3 outline), marked in progress.

## Phase 1: generic bone layout (after the legs merge)

- **T1.1 [P] `CreatureBoneLayout` from legacy fields.** `Kit/CreatureBoneLayout.cs`; `CreatureSpecies.BoneCount/LegBone/WingBone/EyeBone` delegate to a cached layout. Tests `CreatureBoneLayoutTests`: legacy formulas equal the registry for all assets and factories; hybrid wyvern + arthropod hind leg; contiguity; RED wings-before-legs. [E] goldens, CreatureWinged*, CreatureRendererTests. User: nothing changes.
- **T1.2 [P] Octopus through the registry** (after the in-flight octopus task commits; else defer to Phase 3). OctopusMeshTests + hash tests unchanged; layout = 201.

## Phase 2: data model

- **T2.1 [P] Part/module base types and attributes** (`Kit/CreaturePart.cs`, `CreatureModule.cs`, `KitAttributes.cs`, `PartSocket.cs`). Test `KitAttributes_EveryPublicFieldHasParam`.
- **T2.2 [P] Data-only part classes for everything that exists** (SpineBody, SoftBody, Leg2Bone, ArthropodLeg, Wing, Tentacle, RigidCone, Eyes, Repeat; modules Walk, Slither, Climb, Fly, Wander, ClimbExcursion, FlightExcursion, Ambush, Skin, Chitin, Membrane, Cloak, Chromatophore). Test `SpineProfile_Interpolates`.
- **T2.3 [P] `CompiledSpecies` + compose** (mirror/Repeat expansion, gait patterns, wing-arm roles, id refs, layout, Validate). Tests `Compose_Mirror_LThenR`, `Compose_Repeat_SpreadsJointsAndTapers`, `Gait_Diagonal_Tripod_Tetrapod_MatchShippedGroups` (RED with Alternate on the tarantula), `Wing_ArmRefUnknown_Fails`.
- **T2.4 [P] `LegacySpeciesAdapter`** (kitVersion 0 → CompiledSpecies; runtime reads `sp.Compiled`; same LegSpec objects). Tests: goldens + `Adapter_Compiled_EqualsLegacyFields`. [E] full Creature group + Perf A/B in one session.
- **T2.5 [P] SerializeReference fields + kitVersion 1.** Tests `Kit_NoMissingTypes`, `Kit_YamlKeysAreKnownFields` (RED typo), `Converted_Monitor_EqualsLegacy` (fixture KitMonitor.asset, 600 ticks golden-identical). [E] import, Inspector, live respawn. User: open KitMonitor.asset.
- **T2.6 [P] Catalogue generator** (`Editor/CreatureKitCatalogue.cs` + shared `Kit/CatalogueWriter.cs` → `Config/Creatures/CATALOGUE.md`, `catalogue.json`). Tests `Catalogue_IsFresh`, `Catalogue_ListsEveryPartAndUsedBy`. [E] run menu, commit.

## Phase 3: runtime composition

- **T3.1 [P] `PartMeshEmitter` + per-part `EmitMesh`** (builder primitives + Horn behind the emitter; WingedMeshBuilder → WingPart.EmitMesh). Test `Mesh_Bytes_EqualLegacy` per asset (RED: emit order). [E] mesh/winged/renderer tests. User: every enclosure looks identical.
- **T3.2 [P] `IPartRuntime` stages in `CreatureSim`** (eyes → EyesPart; flight → ILocomotionMode). Tests: goldens walking + flying, Kit_NoGC with a stub runtime, `Stages_CalledOncePerSubStep`. [E] perf A/B.
- **T3.3 [P] One renderer path** (mesh/bind poses/bounds from CompiledSpecies; `SpawnOctopus` → `Spawn`). Tests: renderer spine bit-identical, octopus renderer tests, bounds.
- **T3.4 [P] `ModularBrain` + `BrainFactory`** (legacy → same brain types). Tests `BrainFactory_Legacy_SameTypes`, `ModularBrain_Hysteresis_MinHold`, containment.
- **T3.5 [P→E] Lab roster + habitats** (`CreatureLabRoster.asset`; CreatureLab + Rebuild Creature Lab read it; `Habitat.For`). Tests `Lab_Placement_NeighboursNeverOverlap` with every entry, `Roster_ContainsEveryNonTestSpecies` (warn), `Habitat_Resolves`. [E] rebuild lab, commit scene with the user's go-ahead. User: walk the lab.

## Phase 4: look layers

- **T4.1 [P→E] Part-layer table** (`_PartLayers`, `.linear` once in C#, shader switches on shading model). Tests `PartLayers_LegacyMapping_Identity`, `CreatureShader_EditorRuntimeCompile_NoErrors` [E], pixel guard `Shader_Layers_LegacyIdsUnchanged` (1/255) [E]. User: monitor/wyvern colours, spider sheen and bands unchanged.

## Phase 5: new components and the exotic animals in the lab

Each animal: recipe asset → generic kit green in the harness → `[PartTests]` for new parts → roster entry → [E] tests + lab rebuild → user hand-off.
- **T5.1 [P] FinStrip part** (`FinStrip_MaxBend_NoFlips`, `FinStrip_HeightScalesWithSize`).
- **T5.2 [P] Flapper part + Flee behaviour** (`Flapper_BeatFrequency_FollowsUndulation`, `Flee_MovesAway_StaysContained`).
- **T5.3 [P→E] FinnedSandEel + lab.** User: fins ripple with the body, no creases on the tightest S-bend, pectorals flutter in phase, it flees and stays inside.
- **T5.4 [P] Folded-wing flag** (`Wing.ground = Fold`; tests `FoldedWing_NeverPlants`, `FoldedWing_PoseStable_NoMembraneFlips`, wyvern goldens).
- **T5.5 [P→E] Hexadrake + lab (aviary).** User: walks on four with wings folded, crest unbroken, clean launch unfold, lands on a post, horns steady.
- **T5.6 [P] Antenna part** (`Antenna_TipLag_Bounded`, `Antenna_Settles_NoJitter`).
- **T5.7 [P→E] GiantCentipede v1 + lab** (Alternate + liftDelay; per-species perfBudgetMs). User: legs ripple as a wave, none through the body in tight turns, antennae sway, climbs the Baobab.
- **T5.8 [P] Phase gait scheduler (Wave)** (`Wave_DutyFactor_Holds`, `Wave_SupportPolygon_NeverEmpty`); switch the centipede to Wave.
- **T5.9 [P] Socket-rooted Tentacle on a spine body + Ambush adapter** (after the octopus roles/swinging plan). Tests `RootedTentacle_RootFollowsJoint`, `Stretch_Bounds`, octopus tests unchanged.
- **T5.10 [P→E] TentacleCrab + lab.** User: eight legs scuttle, tentacles grab Baobab bark without tremble, eye stalks bob, claws held up.
- **T5.11 [P] Convert the shipped assets** (after decision 4 and the octopus plan): one per task, golden-equal; then remove legacy fields and the adapter.

## Parallelism and Editor queue

Phase 0 fully parallel now. T1.1, T2.1–T2.3, T2.6 parallel in wt/kit. T5.1/T5.2/T5.4/T5.6 parallel worktrees after Phase 3. Editor queue (one agent at a time): T0.2 → T2.4/T2.5 → T3.1–T3.5 → T4.1 → one visit per animal (T5.3, T5.5, T5.7, T5.10), each ending with the user hand-off note.

**Done when:** every shipped species passes the generic kit and the goldens; the catalogue is fresh; the four exotic animals stand in their own lab enclosures, approved by the user; the `creature-kit` skill holds the workflow.
