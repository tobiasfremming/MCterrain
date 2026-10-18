# Creature Kit: composable, agent-authored animals (design)

Status: design from a spike, 2026-10-18. Prototype (plain C#, `dotnet run -- recipes out`): session scratchpad `creature_kit_spike/` (Kit/Attributes.cs, Parts.cs, Modules.cs, Species.cs, BoneLayout.cs, Catalogue.cs, Recipe.cs; recipes/*.json for 5 existing + 4 exotic species; out/report.txt, catalogue.md (455 lines), catalogue.json, *.asset.yaml).

**Goal (user):** make it really easy for agents to create new, exotic animals from reusable components (legs, wings, fins, tentacles, behaviours, textures). Check what exists and what can be reused first; add a new component type only when nothing fits. Prototype animals go into the Creature Lab.
**Primary author:** an AI agent working in text (YAML/JSON).
**Non-negotiables:** looks first, speed second; every size-dependent value derives from `sizeScale` (lengths ×s, times ×√s); zero GC per frame; main thread; climbing contact from real geometry only; legacy species bit-identical (golden hashes); the user does the visual check (R32).

## 1. Inventory (2026-10-18)

| piece | where | today | coupling that blocks composition |
|---|---|---|---|
| Spine body | `CreatureSim` (644 lines) | merged | flight created in the sim ctor (`sp.CanFly`); climbing built in; eyes hard-coded in `WriteBoneWorld` |
| Soft body | `Octopus/OctopusBody`, `SoftLattice` | integration | separate `bodyPlan`; own bone layout; own spawn path |
| Two-bone leg | `CreatureLegs` + `TwoBoneIK`, `LegSpec` | merged | one system holds every leg; each limb model is an `if` inside it |
| Arthropod leg | `ArthropodLegIK/Model`, `ArthropodLegMesh`, `LegSegment` | legs branch (merging) | lives inside `LegSpec` (segments non-empty); `feeler` only here |
| Wing + flight | `Flight/*`, `WingSpec`/`FlightSpec` | integration | wing names its arm by index; `WingedMeshBuilder` wraps the builder; rest pose branches on `WingCount` |
| Tentacle | `TentacleChain`, `TentacleAgent`, `WrapMarch`, `ArmBlackboard` | integration | only via `CephalopodSpec.arm`; contact budget in `OctopusController` |
| Rigid cones | `BodyAppendage` + `ArthropodLegMesh.Horn` | legs branch | mesh only; fine |
| Eye cluster, gait bob | `EyeSpot[]`, `GaitBob` | legs branch | top-level fields |
| Climbing | `CreatureClimb`, `ClimbSpec`, surface probes | merged | data-driven already (good model) |
| Brains | Wander, Climbing, Flight, Octopus | mixed | chosen in code (`CreatureLab.BrainFor`); `ICreatureBrain` returns only a target |
| Mesh | `CreatureMeshBuilder`, `WingedMeshBuilder`, `OctopusMeshBuilder`, `CreatureMeshLists` | mixed | three builders, picked by plan/wings |
| Shading | `Creature.shader`, `CreatureOctopus.shader`, hlsl includes | mixed | part-id-specific branches; look fields piled into `CreatureLook`; textual merge conflicts |
| Bone layouts | `WingBoneLayout`, `LegBoneLayout`, `OctopusBody.*Bone` | 3 hand-written | conflict when branches merge |
| Species data | `CreatureSpecies` SO, 9 assets (4012 YAML lines) | mixed | god object; per-joint arrays typed out; L/R legs duplicated |
| Labs | `CreatureLab`, `OctopusLab`, `kSpeciesPaths`, `AviaryDressing`, `EnclosurePlant` | mixed | bespoke lab code per creature type |
| Tests | 44 EditMode files, factories, `GcAllocs`, goldens, Perf assembly | mixed | per-species tests hand-copied; no fixture over every asset |
| Offline harness | per-session scratch folders + gen scripts | scratch only | recreated by every agent |

Seams to keep: `ICreatureBody`, `ISurfaceProbe`, `EnclosureArea`, the sizeScale/Froude rule, the 32-byte `CreatureInstance`, the "0 = default" data style.

## 2. Target architecture

A species = body plan + **parts** (what it is: body, limbs, wings, chains, fins, rigid cones, eyes) + **modules** (what it does: locomotion, behaviours; how it looks: look layers) + scale.

### 2.1 Data and serialization

`[SerializeReference] List<CreaturePart> parts` and `List<CreatureModule> modules` on `CreatureSpecies`, plus `int kitVersion` (0 = legacy fields). Authoring sugar (`mirror: 1`, `Repeat {count, fromJoint, toJoint, lastScale, template}`) stays in the asset and is expanded at load into a `[NonSerialized] CompiledSpecies` (invalidated in `OnValidate`); the asset is the only source of truth. Centipede: ~50 hand-written lines vs 3450 expanded.
Why SerializeReference: one file per species; type written by class name (no script GUIDs); polymorphic lists; `[MovedFrom]` renames; Inspector + live respawn keep working. Risk: missing types after renames → kit test asserts none. Rejected: SO sub-assets (fileIDs, orphans), plain JSON + registries (no Inspector, no polymorphism in JsonUtility). JSON survives as the generated catalogue format and harness input.

### 2.2 Bone layout registry

`CreatureBoneLayout` per compiled species: each part declares `BoneCount(ctx)` and gets a contiguous range; callers use `layout.Bone(part, k)`. Block order — spine: Body, Limb, Wing, Sense, then Chain, Fin, Rigid(own bone); soft: Chain, Body, Sense, Rigid. Legacy blocks first in legacy order. Prototype proved: DesertMonitor 40, WingedSerpent 58 (= WingBoneLayout), Tarantula 75 (= LegBoneLayout), TreeOctopus 201 (= OctopusBody), legs + wyvern merged (wings after summed leg bones), TentacleCrab 114, Centipede 332.

### 2.3 Contracts

```csharp
[Serializable] public abstract class CreaturePart {
  public string id; public PartSocket at; public bool mirror;   // at = {joint, side, offset, slot}
  public abstract PartKind Kind { get; }                        // Body|Limb|Wing|Chain|Fin|Rigid|Sense
  public virtual int BoneCount(in SpeciesCtx c) => 0;
  public virtual string Validate(in SpeciesCtx c) => null;
  public virtual void EmitMesh(PartMeshEmitter m, in PartCtx c) { }
  public virtual IPartRuntime CreateRuntime(in PartCtx c) => null;   // the only place allowed to allocate
}
public interface IPartRuntime {
  PartStage Stage { get; }   // AfterChain | AfterGround | AfterLimbs | Late
  void Step(in StepCtx c, float dt); void WriteBones(Matrix4x4[] dst, int offset);
  void EncapsulateBounds(ref Vector3 lo, ref Vector3 hi); void DrawDebug(ICreatureDebugDraw d);
}
public interface ILimbModel { float Reach { get; } void Solve(...); void WriteBones(...); }
public interface ILocomotionMode { int Priority { get; } bool SubStep(CreatureSim s, float dt, Vector3 target); }
public interface IBehaviour { float Utility(in BrainCtx c); void Enter(in BrainCtx c); BrainOutput Tick(in BrainCtx c, float dt); }
public struct BrainOutput { public Vector3 target; public LocoRequest mode; public float cloak; }
```

- Systems, not one virtual call per bone: limbs stay in `CreatureLegs`, dispatched at construction into typed `ILimbModel` arrays (Perf_100Lizards sits at its bound). Chains/fins/antennae use `IPartRuntime`. Locomotion modes in priority order; Walk runs when none claims the step; Climb stays a Walk modifier.
- Brain = `ModularBrain` (highest-utility behaviour, minimum hold + switch margin). Existing brains become behaviours (Wander, ClimbExcursion, FlightExcursion, Ambush). Legacy assets get exactly today's `BrainFor`.
- Look layers: per-species `_PartLayers[16]` table; the shader switches on shading models (Skin, Chitin, Membrane, Eye, Claw), not part ids, so a new part usually needs no shader edit. Colours decoded with `.linear` once in C#. The 4-bone octopus shader stays a separate family.
- Size: `PartCtx.Size {L = s, T = √s}`; every `[Param]` carries a `Unit` (Metres ×s, Seconds/MetresPerSecond ×√s, Hz/DegPerSecond ÷√s).
- Lab habitat from modules: Fly → aviary; Climb → enclosure with a climbable plant; Ambush/Soft → tree grove; otherwise plain. `Config/Creatures/CreatureLabRoster.asset` replaces `kSpeciesPaths` and per-type `if`s. Adding to the roster is the last step of the new-animal workflow.

### 2.4 Existing creatures on the kit

| species | parts | modules | migration |
|---|---|---|---|
| DesertMonitor | SpineBody(26), Leg2Bone front/rear ×mirror, Eyes | Walk(Diagonal), Climb, Wander, ClimbExcursion, Skin | legacy adapter; optional golden-equal conversion |
| DesertSnake | SpineBody(32), Eyes | Walk, Slither, Wander, Skin | none |
| DesertBeetle v2 | SpineBody, Repeat(3, ArthropodLeg)×mirror, Eyes | Walk(Tripod) | none |
| DaddyLongLegs / Tarantula | SpineBody(7), Repeat(4, ArthropodLeg 7 seg)×mirror, palp (Feeler)×mirror, RigidCone chelicera, Eyes + cluster | Walk(Tetrapod, bob), Wander, Skin, Chitin | GaitBob/EyeSpot/BodyAppendage → parts/module fields |
| WingedSerpent | SpineBody(32), Leg2Bone arm + hind ×mirror, Wing(arm) ×mirror, Eyes | Walk, Fly, FlightExcursion, Skin, Membrane | `wings[].leg` index → `arm` id |
| TreeOctopus | Soft: Repeat(8, Tentacle), SoftBody, Eyes, RigidCone siphon | Ambush, Cloak, Chromatophore, Skin | adapter wraps CephalopodSpec; no internals refactor until the arm-roles/swinging plan lands |

### 2.5 Exotic test animals

| animal | parts | needs new |
|---|---|---|
| FinnedSandEel | SpineBody 48, FinStrip dorsal + anal, Flapper pectoral ×mirror, Eyes; Walk + Slither, Wander, Flee, Membrane, Cloak | FinStrip (mesh only), Flapper (1–3 bones, beat from undulation phase), Flee — cheapest first proof |
| Hexadrake (six-limbed winged lizard) | SpineBody 30, wing-arm + front + rear legs ×mirror, Wing(ground: Fold), FinStrip crest, RigidCone horns, Eyes | one generic flag `Wing.ground = Fold` + FinStrip |
| GiantCentipede (30 leg pairs) | SpineBody 64, Repeat(30, ArthropodLeg 4 seg)×mirror, Antenna + cerci, forcipules, Eyes; 332 bones | Antenna (spring chain); phase gait scheduler for Wave (v1 uses Alternate + liftDelay); perf est. 0.47 ms Mono (needs a cheap-leg tier or a showcase budget) |
| TentacleCrab | SpineBody 4, Repeat(4, ArthropodLeg)×mirror, claw ×mirror, Repeat(2, Tentacle 16)×mirror, Antenna eye stalks, Eyes | socket-rooted Tentacle on a spine body, shared chain contact budget, Ambush adapter for spine bodies, Antenna; optional sideways walk — largest, last |

Cost model calibrated on measured baselines; estimates: eel 53 µs, Hexadrake 65 µs, crab 0.45 ms, centipede 0.47 ms.

## 3. Agent authoring workflow

a. **Catalogue first:** `Config/Creatures/CATALOGUE.md` + `catalogue.json`, generated by reflection over `[Part]/[Module]/[Param]` (status/branch, bones, material layers, use-when, used-by, every parameter with unit, size rule, meaning, range, example; species table; part-id registry, next free 10). Menu, batch `-executeMethod` or offline harness. `Catalogue_IsFresh` fails when stale.
b. **Compose:** `creature_kit.py new <Name> --from <Species>`; edit the SerializeReference YAML (parts, modules, mirror/Repeat). Unknown keys are errors. `CompiledSpecies` expands sugar, assigns gait groups from `Walk.pattern` (Diagonal, Tripod, Tetrapod, Alternate, Wave), wing-arm roles, layout.
c. **Generic test kit for every species** (`CreatureKitTests`, `[TestFixtureSource]` over all species): Validate null; no missing types; contiguous layout matching the mesh; mesh < 5 ms; 0 inverted triangles over the MaxBend sweep; bounds contain every skinned vertex; 5-min wander contained (2 seeds); gait invariants; size 0.9×/1.1× ratios within 1 %; GC = 0 with positive control; tick ≤ `perfBudgetMs`; lab placement + habitat. Per-type invariants via `[PartTests(typeof(X))]`.
d. **Checked-in offline harness:** `Assets/TerrainGen/Tools~/CreatureHarness/` (net8, real sources vs stubs or the real CoreModule DLL, mini NUnit runner); `creature_kit.py check|test|render` (render = PIL contact sheet for shape sanity only).
e. **New component recipe** with templates: check the catalogue first; data class with `[Part]`/`[Param]`; BoneCount, Validate, EmitMesh via `PartMeshEmitter` primitives (Tube, Ring, Ellipsoid, Horn, MembraneStrip), runtime if it moves, DrawDebug; pick a shading model (new one = next part id + pixel guard); `[PartTests]` RED first; add to an example species, regenerate the catalogue, harness, Unity once. Never edit core files for one species.
f. **User check (R32):** the animal in its own lab enclosure, with a hand-off note per part; 0.9×/1.1× individuals side by side.

Skill `creature-kit`: SKILL.md (loop: catalogue → copy → compose → check → lab roster → Unity once → hand-off; rules), references (authoring, new-component, testing, lab), scripts/creature_kit.py, templates. `creature-module` keeps the internals.

## 4. Proof (prototype)

All 9 recipes compose, validate and lay out; 5 legacy layout equivalences pass; gait patterns reproduce shipped groups; catalogue generator writes used-by; YAML writer shows the agent-facing text (`out/Hexadrake.asset.yaml`); size table follows the unit rules.

## 5. Migration (summary; see the plan)

Phase 0 (now, new files only): harness, generic kit fixture over legacy fields, skill skeleton. Phase 1 (after the legs merge): bone layout registry; goldens unchanged. Phase 2: part/module types, SerializeReference lists, CompiledSpecies + LegacySpeciesAdapter, catalogue. Phase 3: part runtimes, mesh emitters, one renderer path, ModularBrain, lab roster/habitats. Phase 4: look-layer table. Phase 5: new parts and the exotic animals, each in its own lab enclosure. Octopus internals untouched until its roles/swinging plan finishes.
Risks: Perf_100Lizards at its bound (typed limb arrays, same-session A/B); textual conflicts with open branches (kit in new files under `Scripts/Creatures/Kit/`); Mono vs .NET goldens; Unity rewrites SerializeReference YAML on save (`creature_kit.py fmt` normalises); centipede/crab cost; shader layer table needs an Editor fix round.
Perf impact: legacy ±0; new hooks ~1–2 interface calls per part per sub-step; renderer unchanged (one draw per species).

## 6. User decisions

(Recorded once answered.)
User decisions, 2026-10-18:
1. Source of truth: the species asset with mirror/Repeat sugar, expanded at load.
2. Performance: no fixed showcase budget decided; the user will flag perf issues. Preferred direction: find ways to optimise greatly WITHOUT costing looks (e.g. Burst/jobs for the sims, off-screen/distance simulation LOD, shared per-pair IK, cheaper non-visible work) rather than visibly cheaper animals.
3. Water: the finned eel is a sand eel (slithers on sand, fins ripple); no swimming.
4. Migration: keep the legacy adapter now; convert the shipped species later (after the octopus roles work), one per task with golden-equal tests, then delete the legacy fields.
