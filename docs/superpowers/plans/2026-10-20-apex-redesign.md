# Apex Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Delete the old Apex and build a new one from seven new reusable kit parts so it looks like the reference image, walks on its folded wings, flies with a travelling bob and keeps its tail alive.

**Architecture:** Every anatomical part is a new generic `CreatureKit` part type (data + `EmitMesh` + optional `IPartRuntime`) running on the shared systems (CreatureSim chain, CreatureLegs, CreatureFlight/CreatureWings/AirChain). One chain body (`FlowBody : ISpineChainBody`) carries head, neck, trunk and tail; the head, wing, leg, throat flap, pits and tail overlay ride it. The species asset comes from a Python generator using `kityaml`.

**Tech Stack:** Unity 6000.2.6f2 C# (runtime asm `TerrainGen.Runtime`), NUnit EditMode tests, offline harness `Assets/TerrainGen/Tools~/CreatureHarness` driven by `.claude/skills/creature-kit/scripts/creature_kit.py`, Python 3 generators.

**Spec:** `docs/superpowers/specs/2026-10-20-apex-redesign-design.md` (rev. 2). **Open the reference image and its crops in `docs/superpowers/specs/assets/` at the start of every task that draws geometry** (Tasks 3–9).

## Global Constraints

- Kit rules (`.claude/skills/creature-kit/SKILL.md`, `references/new-component.md`): namespace `CreatureKit`, `[Serializable]`, `[Part(...)]` with `Summary/System/Bones/UseWhen`, `[Param(unit, meaning, ...)]` on **every** public field; `MeshOrder` 100; `Validate` returns null or the first problem naming `id`; arrays cloned in `CopyArrays`.
- Author at scale 1 in metres; lengths × s (`PartCtx.Size.L`), times × √s (`.T`); Hz ÷ √s.
- Zero GC in `Step` / `WriteBones` / `EncapsulateBounds` / `DrawDebug`; allocate only in `CreateRuntime` / `EmitMesh`; main thread.
- Never edit `CreatureSim`, `CreatureLegs`, mesh builders or the renderer for this species. A shared-system change is an opt-in data flag, off by default, every shipped species bit-identical (goldens untouched).
- No new global material id: new colours are named kinds (`PartLayers.NamedKinds` or `[Part(MaterialKinds = ...)]`, `m.Slot("kind")`).
- New source files go under `Assets/TerrainGen/Scripts/Creatures/Kit/` (each with a Unity `.meta`, `creature_kit.py`/`kityaml.write_script_meta`); tests under `Assets/TerrainGen/Tests/EditMode/`.
- Each part test class has a RED proof per invariant (a deliberately broken input that makes the check fail).
- Colours (sRGB): dorsal `#4A1E33`, belly/throat `#D9CDB8`, wing fan + tail `#1F6B66`, stripes `#163F45`, crests `#3FC0B0`, pits/claws near-black.
- The user judges looks in Unity; offline renders only as a placement/silhouette sanity check.
- Commits end with `Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>`. Parent repo has unrelated uncommitted work: commit only the paths you touched (`git commit -- <paths>`).

## Review Focus

1. **Size jitter (0.9× / 1.1× individuals)**: every part's geometry and motion must scale; pin with a 0.9/1.1 assertion in each runtime part's tests (Tasks 6, 8, 9) and the kit `Size` check (Task 10).
2. **Turning hard while walking** (tightest circle): the raised neck, throat flap and tail loop must not invert or pass through the trunk; covered by kit `MaxBend` plus the "flap never inside the neck" test under a turn (Task 6) and the tail kink test (Task 9).
3. **Launch and touchdown transitions** (the blend between blade pose and spread wing): the riskiest pose for the thick wing; the FleshWing test sweeps the shared launch/touchdown blends (Task 8), PoseSweep covers it at species level (Task 10).
4. **The Inspector knob the user will try first: wing rear attach moved to the hips**: must still build and fold cleanly; pinned in Task 8 (`FleshWing_RearAttachAtHips_NoInvertedTriangles`).
5. **Strength sliders at 0** (TailFlourish ground/air strength, Dewlap swing): 0 must give the plain chain pose exactly; pinned in Tasks 6 and 9.

---

## File map

| File | Responsibility | Task |
|---|---|---|
| `Tests/EditMode/CreatureFlowFixtures.cs` | test helper: build a kit species in code; sims; skinned-mesh inversion counter | 2 |
| `Scripts/Creatures/Kit/FlowBody.cs` | `FlowBody` part: chain data + section channels + its mesh | 3 |
| `Scripts/Creatures/Kit/CrestBeakHead.cs` | `CrestBeakHead` part + `CrestBeakHeadRuntime` (jaw) | 4 |
| `Scripts/Creatures/Kit/PitRow.cs` | `PitRow` part (mesh only) | 5 |
| `Scripts/Creatures/Kit/Dewlap.cs` | `Dewlap` part + `DewlapRuntime` | 6 |
| `Scripts/Creatures/Kit/DrakeLeg.cs` | `DrakeLeg` limb part (two-bone `LegSpec`) + mesh | 7 |
| `Scripts/Creatures/Kit/FleshWing.cs`, `FleshWingMesh.cs` | `FleshWing : WingPart` + `FleshWingRuntime`; mesh in its own file | 8 |
| `Scripts/Creatures/Kit/TailFlourish.cs` | `TailFlourish` part + `TailFlourishRuntime` (Late overlay) | 9 |
| `Tools~/SpeciesGen/Apex.py`, `Config/Creatures/Apex.asset(.meta)` | the species | 10 |
| `Tests/EditMode/Creature<Part>Tests.cs` (one per part), `CreatureApexTests.cs` (new) | tests | 3–10 |

Paths below are relative to `Assets/TerrainGen/` unless they start with `docs/` or `.claude/`.

---

### Task 1: Branch, worktree, delete the old Apex

**Files:**
- Delete: `Config/Creatures/Apex.asset(.meta)`, `Tools~/SpeciesGen/Apex.py`, `Scripts/Creatures/Kit/SailWing.cs(.meta)`, `SerpentNeck.cs(.meta)`, `CasqueHead.cs(.meta)`, `Tests/EditMode/CreatureApexTests.cs(.meta)`
- Modify: `Config/Creatures/CreatureLabRoster.asset` (remove the entry with guid `453d7169b1fd4174b6bea3812c74346c`), comments naming SailWing/CasqueHead/SerpentNeck in `Scripts/Creatures/Flight/WingSpec.cs` and `Scripts/Creatures/Kit/BeakHead.cs` (reword to "a subtype"), `Config/Creatures/CATALOGUE.md` + `catalogue.json` (regenerate)
- Modify (parent repo): `.claude/skills/creature-kit/SKILL.md` (the `render Apex` / `trace Apex` examples → `Pterodactyl` for now; Task 11 points them back), `references/testing.md` (old-Apex findings reworded without the name, lessons kept)

- [ ] **Step 1:** Create submodule branch `feat/apex-v3` off `feat/creature-integration` in a worktree outside `Assets/` (creature-module workflow; superpowers:using-git-worktrees). Record the harness baseline: `python .claude/skills/creature-kit/scripts/creature_kit.py test --tg <worktree>/Assets/TerrainGen` → note pass/skip/known counts.
- [ ] **Step 2:** Delete the files above and edit the roster/comments. Grep proves nothing is left: `grep -rn "SailWing\|SerpentNeck\|CasqueHead\|CreatureApexTests" Scripts Tests Tools~/SpeciesGen Config` → no hits (CATALOGUE after regeneration).
- [ ] **Step 3:** `creature_kit.py catalogue --write`, then the full harness suite. Expected: same counts as the baseline minus the deleted Apex tests and the Apex fixtures of `CreatureKitTests`; 0 failed. `CreatureKitLabTests.Habitat_Resolves` still passes (its `"Apex"` row is only looked up for listed species — if it fails, remove the row and re-add it in Task 10).
- [ ] **Step 4:** `creature_kit.py unity-compile` → 0 errors.
- [ ] **Step 5:** Commit (submodule): `chore(creatures): delete the old Apex (asset, generator, SailWing, SerpentNeck, CasqueHead, tests, roster entry)`. Commit the skill-doc edits in the parent repo with paths only.

---

### Task 2: Test fixtures for kit parts built in code

**Files:**
- Create: `Tests/EditMode/CreatureFlowFixtures.cs`

**Interfaces:**
- Produces (namespace `TerrainGen.Tests`, `internal static class FlowKit`):
  - `CreatureSpecies Build(string name, float scale, IEnumerable<CreaturePart> parts, IEnumerable<CreatureModule> modules)` — a `CreatureSpecies` ScriptableObject with `kitVersion = 1`, returns `sp.Compiled.Runtime`; throws `AssertionException` with `Compiled.Error` if compose fails.
  - `CreatureSim Sim(CreatureSpecies sp, float sizeScale, int seed = 1)` — on `FlatGroundProbe`, up = `Vector3.up` (as `CreaturePteroWingTests.Sim`).
  - `Matrix4x4[] Bones(CreatureSim sim)` — the bone worlds the renderer would use this frame (same call path as the renderer's CPU skin).
  - `int InvertedTriangles(CreatureSpecies sp, CreatureSim sim, out string where)` — skin the species mesh with the sim's current bones and count triangles whose normal flips against the bind (reuse the logic in `CreaturePteroWingTests` / `KitPoseSweep`; do not duplicate it if a callable helper exists).
  - `Vector3[] SkinnedVertices(CreatureSpecies sp, CreatureSim sim, int part = -1)` — posed vertex positions, optionally only those whose uv1.x part id == `part`.
  - `void Run(CreatureSim sim, float seconds, Vector3 target)` — ticks at 1/60 s toward `target`.
  - `Mesh Mesh(CreatureSpecies sp)` → `CreatureKitAssets.BuildMesh(sp)`.

- [ ] **Step 1: Write `FlowKit_BuildsAKitSpecies` in the same file's test class `CreatureFlowFixturesTests`:** build a species with a plain `SpineBody` (profile 2 keys, 8 joints), two mirrored `Leg2Bone`s and `Walk`; assert `Validate()` null, `Sim` ticks 60 frames, `InvertedTriangles == 0`.
- [ ] **Step 2:** Run: `creature_kit.py test CreatureFlowFixturesTests` → FAIL (types missing).
- [ ] **Step 3:** Implement `FlowKit`.
- [ ] **Step 4:** Run again → PASS.
- [ ] **Step 5:** Commit `test(kit): FlowKit fixtures - kit species built in code, sims, skinned inversions`.

---

### Task 3: `FlowBody` — one chain from head to tail with a shaped section

**Files:**
- Create: `Scripts/Creatures/Kit/FlowBody.cs`, `Tests/EditMode/CreatureFlowBodyTests.cs`

**Interfaces:**
- Consumes: `FlowKit` (Task 2); `ISpineChainBody` (`Kit/KitAirborne.cs`); `PartMeshEmitter.SpineAt(u)`, `Vertex`, `Tri`, `Blend`.
- Produces:
  - `[Part("FlowBody", PartKind.Body, MaterialLayers = new[]{0})] public sealed class FlowBody : CreaturePart, ISpineChainBody`
  - `public struct FlowKey { t, halfWidth, halfHeight, clearance, bendLimitDeg, hump, keel, flank, blade }` — `hump`, `keel`, `flank` in metres; `blade` 0..1 (0 = the oval, 1 = the full ribbon).
  - Fields: `spacing`, `headCapLength`, `tailTipLength`, `jointCount`, `FlowKey[] profile`, `rigidHeadJoints` (-1 auto as SpineBody), `humpSharpness` (exponent, default 8), `keelSharpness` (default 6), `bladeExponent` (superellipse n at blade 1, default 4), `ringSegments` (default 24), `ringsPerSegment` (default 3).
  - `public float Section(float u, float phi, out Vector2 offset)` — the section's radius offset in the joint frame at body fraction `u` (0 head .. 1 tail tip) and angle `phi` (−π/2 belly, +π/2 back): the superellipse of (halfWidth, halfHeight) with exponent `lerp(2, bladeExponent, blade)` and height stretched so the blade's height/width = `halfHeight/halfWidth`, plus `hump·max(0,sinφ)^humpSharpness` up, `keel·max(0,−sinφ)^keelSharpness` down, `flank·cos²φ` sideways. Shared by the mesh and the tests.
  - Colour fields (`MaterialKinds = new[]{"tailfan", "dorsalstripe"}`): `tailColourFrom` (body fraction where the surface turns to the `tailfan` kind, teal with darker lengthwise stripes; ≥ 1 = off), `dorsalStripeTo` (body fraction up to which a narrow `dorsalstripe` band runs along the top of the neck from the head; 0 = off), `dorsalStripeWidthDeg 30`.
  - `public float FrontRingU` — the body fraction where the drawn surface starts (the head part covers what is ahead of it); `headCapLength` closes the surface with a small pole there.

- [ ] **Step 1: Write the failing tests** (`CreatureFlowBodyTests`, a fixture species: FlowBody 24 joints, spacing 0.1, profile with a neck (narrow, rising clearance), a chest key with `hump 0.06, keel 0.08`, a tail from t=0.55 with `blade 1`, hW 0.03 / hH 0.12; two Leg2Bone legs; Walk):
  - `FlowBody_Composes_AsTheChain`: `sp.JointCount == 24`, `sp.ringSegments == 0` (SpineBody mesh off), `Validate` null.
  - `FlowBody_Hump_IsSharpPeak`: at the chest key, `Section` along φ: the top point is the highest; the angle where the hump term drops to half is < 25° from the top.
  - `FlowBody_Keel_JutsBelowTheOval`: lowest point at the chest ≥ halfHeight + 0.9·keel below the joint.
  - `FlowBody_Tail_IsARibbon`: on the rest mesh, the section through the tail's middle joint has height/width ≥ 3; top and bottom edges rounded (no vertex angle < 60° in the section loop).
  - `FlowBody_NoInvertedTriangles_TightCircle`: `KitChecks.MaxBendProblem(sp) == null`.
  - `FlowBody_Normals_PointOut`: every rest vertex normal · (vertex − its spine point) > 0.
  - REDs: `Red_Hump_Broad` (humpSharpness 2 → half-angle test fails), `Red_Tail_Round` (blade 0 → ratio < 3).
- [ ] **Step 2:** `creature_kit.py test CreatureFlowBodyTests` → FAIL (no FlowBody).
- [ ] **Step 3:** Implement `FlowBody` in `FlowBody.cs`. Chain data exactly as `SpineBody` (`BuildJoints` by monotone cubic over the profile — call SpineBody's interpolation through a shared static if one can be extracted without changing its arithmetic; otherwise copy it, noting it). Mesh: rings from `FrontRingU` to the tail tip, `ringsPerSegment` per segment, each ring from `Section`, skinned `Blend` between the two nearest joint bones as `BodyMesh` does; dorsal channel = sinφ; normals by finite differences (`PartMeshEmitter.DiffStep`); tail tip a pole.
- [ ] **Step 4:** Run → PASS; then `creature_kit.py test CreatureKitTests` (shipped species unchanged, 0 new failures).
- [ ] **Step 5:** Commit `feat(kit): FlowBody - one chain head to tail, superellipse section with sharp hump, keel, flank and tail ribbon`.

---

### Task 4: `CrestBeakHead` — the beaked serpent head (the showpiece)

**Files:**
- Create: `Scripts/Creatures/Kit/CrestBeakHead.cs`, `Tests/EditMode/CreatureCrestBeakHeadTests.cs`

**Interfaces:**
- Consumes: `SculptShape`, `SculptMesher` (`Kit/Sculpt.cs`, `Kit/SculptMesher.cs`: Ellipsoid, RoundCone, Box, Plane; Union/Subtract/Intersect with blend; cached by shape hash); `FlowKit`; `FlowBody.FrontRingU`.
- Produces:
  - `[Part("CrestBeakHead", PartKind.Rigid, Bones = "1 (the jaw)", MaterialKinds = new[]{"crest"})] public sealed class CrestBeakHead : CreaturePart` — rigid to `at.joint` (the body's head joint, 0).
  - Fields: `skullLength 0.30`, `skullWidth 0.075`, `skullDepth 0.085`, `beakLength 0.16`, `beakHookDeg 8`, `browRidge 0.3`, `crests` (array of `CrestDef { along (0 beak root..1 tip), height, length, curlDeg (backward), thickness }`, default two: rear `{0.45, 0.07, 0.10, 110, 0.012}`, front `{0.85, 0.045, 0.06, 95, 0.009}`), `grooves 9`, `grooveDepth 0.004`, `jawFraction 0.42` (jaw share of the head's depth), `gapeDeg 28`, `callEverySeconds` (min 6, max 14), `callSeconds 0.8`, `cell` (mesher cell, default 0.006).
  - `public IReadOnlyList<SculptShape> SkullSolid(), JawSolid(), CrestSolid(int k)` (head frame, scale 1).
  - `public sealed class CrestBeakHeadRuntime : IPartRuntime` (stage Late): `float Gape` (degrees, 0 closed); writes the jaw bone about the hinge; the eye bones onto the head as `BeakHeadRuntime` does today.
- Look: crest vertices `m.Slot("crest")` (bright teal row), skull dorsal/belly shading from the vertex height in the head frame (dark top, pale underside), grooves recessed along the mouth line.

- [ ] **Step 1: Write the failing tests** (fixture: Task 3's species + `CrestBeakHead` at joint 0 + `Eyes`):
  - `Head_Solids_AreClosed`: every emitted head piece is a closed manifold (each edge used by exactly two triangles).
  - `Head_Crests_StandAboveTheBeakLine_AndCurlBack`: in the side silhouette (head frame), each crest's top is above the upper beak line by ≥ 0.8·its `height`; the crest tip is behind its base (z_tip < z_base).
  - `Head_Crests_RearIsLarger`: rear crest height > front crest height.
  - `Head_Flows_IntoTheNeck`: the side-silhouette outline from the body's front ring to the skull has no step > 0.15·skullDepth (sample the top and bottom outlines at 20 stations across the join).
  - `Head_Jaw_ClosedAtRest_OpensOnCall`: at t=0 `Gape == 0`; within `callEverySeconds.max + callSeconds` (Froude) `Gape` reaches ≥ 0.9·`gapeDeg` and returns to 0.
  - `Head_JawRange_NoInvertedTriangles`: `FlowKit.InvertedTriangles == 0` at gape 0, ½, full.
  - `Head_MeshTime_UnderBudget`: the species mesh builds < 5 ms (best of 3, second build hits the cache).
  - REDs: `Red_Crests_Flat` (curlDeg 0 → curl-back fails), `Red_Head_Step` (skullDepth ×2 → the step test fails).
- [ ] **Step 2:** Run → FAIL.
- [ ] **Step 3:** Implement. Skull: a long ellipsoid blended (smooth union) into a RoundCone beak, slightly flattened (`squash`), brow ridges as small ellipsoids subtracted for eye sockets; the back of the skull extends 0.5·skullLength behind joint 0 so it overlaps the body's front rings. Crests: each `CrestDef` is one curved blade on the midline (the image shows them on top of the beak, one behind the other) = 4–6 RoundCones along a backward arc of `curlDeg`, smooth-unioned, flattened to `thickness`. Grooves: `grooves` thin Box subtractions along the mouth line. Jaw: its own solid, rigid to the jaw bone.
- [ ] **Step 4:** Run → PASS.
- [ ] **Step 5:** Commit `feat(kit): CrestBeakHead - SDF serpent skull, pointed beak, curling beak crests, mouth lamellae, jaw on calls`.

---

### Task 5: `PitRow` — breathing holes

**Files:**
- Create: `Scripts/Creatures/Kit/PitRow.cs`, `Tests/EditMode/CreaturePitRowTests.cs`

**Interfaces:**
- Consumes: `FlowBody.Section`, `PartMeshEmitter.SpineAt`.
- Produces: `[Part("PitRow", PartKind.Rigid, MaterialKinds = new[]{"pit"})] public sealed class PitRow : CreaturePart` (mirror-able; mesh only, no bones). Fields: `fromU`, `toU` (body fraction), `angleDeg` (around the section, −90 belly … +90 back; default −35), `count 6`, `radius 0.012`, `depth 0.6` (× radius), `rim 0.35` (× radius, pale raised lip). Each pit is a recessed cup plus a rim torus on the body surface, skinned like the surface under it.

- [ ] **Step 1: Failing tests:** `Pits_SitOnTheSurface` (every rim vertex within 0.15·radius of the body surface from `Section`), `Pits_Count` (6 cups each side with mirror), `Pits_Bend_NoInvertedTriangles` (`MaxBendProblem` null), RED `Red_Pits_Float` (`angleDeg` with a wrong surface radius → surface test fails).
- [ ] **Step 2:** Run → FAIL. **Step 3:** Implement. **Step 4:** Run → PASS.
- [ ] **Step 5:** Commit `feat(kit): PitRow - spiracle / nostril pits with soft rims on a chain body`.

---

### Task 6: `Dewlap` — the throat sail on its own chain

**Files:**
- Create: `Scripts/Creatures/Kit/Dewlap.cs`, `Tests/EditMode/CreatureDewlapTests.cs`

**Interfaces:**
- Consumes: body joints (`sim.Joints`, `sim.Rotations`), `AngleChain` (`Kit/AngleChain.cs`: `Step(root, dt, omega, zeta, maxBend)`, `Angle(i)`, `Bend(i)`), `FlowBody.Section`.
- Produces:
  - `[Part("Dewlap", PartKind.Chain, Bones = "= stations x links", MaterialKinds = new[]{"dewlap"})] public sealed class Dewlap : CreaturePart`. Fields: `fromJoint`, `toJoint` (body joints it hangs from, jaw end first), `stations 5`, `links 3`, `depth` (FlowKey-like profile: `float[] depthAt` per station, metres; Apex: deepest at the front-middle), `edgeStraightness 0.8` (0 curved belly, 1 straight lower edge), `rim 0.012` (rounded rim radius), `thickness 0.008`, `swingHz 1.6`, `swingDamping 0.35`, `maxSwingDeg 25`, `gravityDeg 6`.
  - `public sealed class DewlapRuntime : IPartRuntime` (stage `AfterLimbs`): per station two `AngleChain`s (fore-aft, sideways) driven by the station joint's acceleration in its own frame; `float Swing(int station)` (degrees, for tests); never lets a link point above the station's lateral plane (keeps it under the neck).
- Mesh: a sheet with `thickness`, rounded rim tube along the lower edge, pale (`m.Slot("dewlap")`), faint lengthwise creases; root column skinned to the body joints, each row blended between station bones.

- [ ] **Step 1: Failing tests** (fixture: Task 3 species + Dewlap on the neck joints):
  - `Dewlap_HangsBelowTheNeck`: every dewlap vertex lies below its station joint's lateral plane and outside the body surface by > 0 (`FlowBody.Section`) — rest, walking 10 s, tight circle 10 s.
  - `Dewlap_Swings_AfterANeckMove`: after a 90° turn the swing peaks ≥ 5° and lags the neck's yaw rate peak by ≥ 0.1 s (Froude); settles to < 0.5° within 3 s at rest.
  - `Dewlap_NoJitter_AtRest`: frame-to-frame swing change < 0.01° after settling.
  - `Dewlap_Froude`: 0.9× and 1.1× give the same swing curve in Froude time within 2 %.
  - `Dewlap_ZeroSwing_IsRestPose`: `swingHz` irrelevant when `maxSwingDeg 0`: bones equal the rest bones carried by the joints (bit-equal).
  - `Dewlap_NoGC`: 0 bytes per tick after warm-up (`GcAllocs.Count`).
  - REDs: `Red_Dewlap_Stiff` (maxSwingDeg 0 → swing test fails), `Red_Dewlap_Above` (gravityDeg −40, plane clamp removed via a test-only flag → below-the-neck fails).
- [ ] **Step 2:** Run → FAIL. **Step 3:** Implement. **Step 4:** Run → PASS.
- [ ] **Step 5:** Commit `feat(kit): Dewlap - a throat sail on its own swinging chain with a soft rim`.

---

### Task 7: `DrakeLeg` — the dragon hind leg

**Files:**
- Create: `Scripts/Creatures/Kit/DrakeLeg.cs`, `Tests/EditMode/CreatureDrakeLegTests.cs`

**Interfaces:**
- Consumes: `LimbPart` (`Kit/Parts.cs`: `BaseSpec()`, `ToLegSpec()`), the `LegSpec` two-bone fields.
- Produces: `[Part("DrakeLeg", PartKind.Limb, Bones = "3", MaterialLayers = new[]{1, 2})] public sealed class DrakeLeg : LimbPart` with `upperLength`, `lowerLength`, `upperRadius`, `lowerRadius`, `pole`, `ankleHeight` (the hock), `toes 3`, `hallux` flag, `talonLength`, `talonCurveDeg`, `haunch` (× upperRadius). `ToLegSpec()` fills the two-bone fields (as `Leg2Bone.ToLegSpec`, `digitigrade = false`) so `CreatureLegs` walks it unchanged. Its own `EmitMesh` (the vertebrate Leg2Bone mesh must not also draw it: if `PartMeshes` draws legs by spec index for every limb, gate that on the part type, not on a new field).

- [ ] **Step 1: Failing tests:** `DrakeLeg_WalksLikeATwoBoneLeg` (kit `GaitProblem` null on a fixture walker), `DrakeLeg_TalonsOnTheGround` (planted: lowest talon tip within 1 cm × s of the ground), `DrakeLeg_MaxBend_NoInvertedTriangles`, `DrakeLeg_DrawnOnce` (no Leg2Bone limb vertices for this leg in the mesh), RED `Red_DrakeLeg_Floating` (ankleHeight negative → talons test fails).
- [ ] **Step 2:** Run → FAIL. **Step 3:** Implement (haunch blended into the body like the vertebrate limb; ball knee; slim shin; raised hock; long metatarsus; toes with knuckles and dark curved talons, claw layer). **Step 4:** Run → PASS.
- [ ] **Step 5:** Commit `feat(kit): DrakeLeg - slim dragon hind leg on the two-bone gait`.

---

### Task 8: `FleshWing` — the soft folding wing (largest task)

**Files:**
- Create: `Scripts/Creatures/Kit/FleshWing.cs` (part + runtime), `Scripts/Creatures/Kit/FleshWingMesh.cs` (partial: mesh), `Tests/EditMode/CreatureFleshWingTests.cs`
- Possibly modify (opt-in flag only, off by default): `Scripts/Creatures/Flight/CreatureWings.cs` if the flank attach reads `SpineBody`-only data (it reads `sp.joints`; expected to work with FlowBody unchanged — check first).

**Interfaces:**
- Consumes: `WingPart` (`arm`, `spec`, `FlightBones`), `WingSpec` (fingers 4–5, `groundTallStance`, `groundLiftDeg`, `fanRearRollsWithFan`, `thumbPlant`, `groundWristLift`, `flankPatches`, `membraneFrontJoint`, `membraneRearJoint`), `WingBoneLayout`, `CreatureWings.SetPose(w, spread, fold)` / `Pose()` / `WriteBones`, `ISpreadWingsRest`, `AngleChain`.
- Produces:
  - `[Part("FleshWing", PartKind.Wing, MaterialKinds = new[]{"wingfan", "wingstripe"})] public sealed class FleshWing : WingPart`. Fields: `rootThickness 0.07`, `tipThickness 0.012`, `edgeRound 0.5` (rim roundness), `armBulk 0.06` (fleshy arm radius at the shoulder), `rootSwell 0.03`, `stripes 9`, `stripeDepth 0.003`, `padRadius 0.06` (the blunt ground club at the wrist), `spanSegments 3`, `bindFold` (0..0.8, as the shared system allows), chain: `spanHz 1.4`, `spanDamping 0.45`, `spanMaxDeg 12`, `chordHz 1.8`, `chordDamping 0.5`, `featherDeg 10`, `billowDeg 2`, mesh `columns`, `rows`.
  - `BoneCount = FlightBones + spec.FingerCount * (spanSegments - 1)`.
  - `public float ThicknessAt(float span01, float chord01)` — the shared thickness law (mesh + tests): `lerp(rootThickness, tipThickness, span01^0.8) * (1 - chord01^2 * 0.7)`, never below `tipThickness * 0.5`.
  - `public sealed class FleshWingRuntime : IPartRuntime, ISpreadWingsRest` (stage Late): span chain per finger (segment bones ride the flight's finger bone), chord chain across the rays (trailing edge feathers on the beat, billows gliding); `float SpanBend(int finger, int seg)`, `float ChordAngle(int ray)` for tests.
- Mesh: two skins (dorsal, ventral) offset ±½·`ThicknessAt` along each zone's normal, joined by a rounded rim (edgeRound) at the leading edge, trailing edge and tip; fleshy arm loft inside the leading edge (maroon → teal by `m.Slot`); stripes as colour + shallow ridges along the rays; the wrist pad a soft ellipsoid at the wrist; root zone blended into the flank via the shared flank patches. Two-bone skinning as the shared membrane (between neighbouring rays; per span segment).

- [ ] **Step 1: Failing tests** (fixture: Task 3 species with a wing arm `Leg2Bone` at the shoulder joint, mirrored `FleshWing` 5 fingers, `DrakeLeg` hind legs, `Walk` + `Fly` + `FlightExcursion`; wing numbers from the old system's ranges: fold 150–166°, `groundTallStance 1`, `groundLiftDeg ~70`, `thumbPlant 1`, `fanRearRollsWithFan 1`, `flankPatches 6`, `membraneRearJoint` ≈ shoulder + 0.6·(hips − shoulder)):
  - `FleshWing_IsThick_NotAPlane`: on the spread rest mesh at mid-span, dorsal-to-ventral distance ≥ 0.06 × local chord; no edge where the two skins meet with zero thickness (rim radius > 0.4·tipThickness everywhere).
  - `FleshWing_FoldedBlade_StandsAboveTheBack`: walking 10 s, every frame: each blade tip (the highest folded wing vertex) is above the body's highest dorsal point by ≥ 0.5 × hump height and behind the shoulder joint.
  - `FleshWing_FoldedBlade_IsBroad`: folded, the blade's width at its middle ≥ 0.12 × its length.
  - `FleshWing_StandsOnThePad`: the drawn wrist pad's lowest point drifts < 1 % of the arm length while planted (`KitChecks.DrawnFeetProblem`).
  - `FleshWing_FoldSweep_NoInvertedTriangles`: fold 0 → 1 in 20 steps, and the shared launch and touchdown blends (run a fixture launch and landing): `InvertedTriangles == 0` throughout.
  - `FleshWing_RearAttachAtHips_NoInvertedTriangles`: same sweep with `membraneRearJoint` = the hip joint.
  - `FleshWing_Chain_TipLagsRoot`: in steady beating, the outer span segment's angle peaks after the root's by ≥ 0.05 beat; trailing ray lags the leading.
  - `FleshWing_NoGC`, `FleshWing_Froude` (0.9× / 1.1× chain curves equal in Froude time within 2 %).
  - REDs: `Red_FleshWing_Flat` (rootThickness = tipThickness = 0.0005 → thick test fails), `Red_FleshWing_Low` (groundLiftDeg 0 → blade-above-back fails).
- [ ] **Step 2:** Run → FAIL.
- [ ] **Step 3: Implement the part and the spread mesh**; make `FleshWing_IsThick_NotAPlane` pass.
- [ ] **Step 4: Fold and ground pose.** Scan the fold numbers (fold angles, `groundLiftDeg`, `bindFold`, pole) with a scratch `HarnessExtra` test calling `KitChecks.MaxBendProblem` and the fold sweep over a grid; take the middle of a passing region (lesson recorded in new-component.md). Make the blade, pad and fold-sweep tests pass.
- [ ] **Step 5: Runtime chains**; make the chain, GC and Froude tests pass.
- [ ] **Step 6:** Full harness suite: shipped species unchanged (goldens, `CreatureKitTests`).
- [ ] **Step 7:** Commit `feat(kit): FleshWing - a soft, thick folding wing walked on a blunt pad, span and chord chains`.

---

### Task 9: `TailFlourish` — the living tail

**Files:**
- Create: `Scripts/Creatures/Kit/TailFlourish.cs`, `Tests/EditMode/CreatureTailFlourishTests.cs`

**Interfaces:**
- Consumes: `sim.Flight` (`AirWeight[joint]`, `Mode`), `sim.Joints`, the body's bone indices (`c.Species.Layout.Start(bodyIndex) + joint`), `sim.Seed`.
- Produces: `[Part("TailFlourish", PartKind.Chain, Bones = "0 (re-poses the body's tail bones)")] public sealed class TailFlourish : CreaturePart` — must be the **last** part (Validate, as Tuck). Fields: `fromJoint` (tail root), `airRollDeg 70` (tip roll amplitude), `airCurlDeg 9` (per-joint curl amplitude), `airHz 0.35`, `waveLength 0.6` (tail lengths), `groundLoopDeg 7` (per-joint upward curl building the loop), `groundDriftDeg 2`, `groundHz 0.12`, `easeSeconds 0.6`.
- `public sealed class TailFlourishRuntime : IPartRuntime` (stage Late): FK from `fromJoint`: each tail bone's direction = the sim's direction rotated by the accumulated curl, roll about its own axis; per-joint added bend clamped to that joint's `bendLimitDeg`; the **sim's joints are not written** (pose over the sim); `EncapsulateBounds` adds the posed tail points; `float TipRollDeg`, `Vector3 PosedJoint(int j)` for tests.

- [ ] **Step 1: Failing tests** (fixture: Task 8's flying species + TailFlourish last):
  - `Tail_FlightUntouched`: 30 s flight with and without the part: girdle position and `FlightModel` state bit-identical every frame; walking 30 s: every sim joint and foot bit-identical.
  - `Tail_Air_TwistsAndCurls`: in sustained flight the tip roll spans ≥ 60° and the curl travels (the phase at the tip lags the root by ≥ 0.25 cycle).
  - `Tail_Ground_Loops`: standing 10 s, the posed tail's highest point is above the hip joint by ≥ 0.3 × tail length, and no posed tail point beyond the first two tail joints is within 2 cm × s of the ground.
  - `Tail_Strengths_Zero_IsTheChain`: all amplitudes 0 → tail bones bit-equal to the plain sim's.
  - `Tail_NoKink`: per-joint added bend ≤ the joint's `bendLimitDeg`; `InvertedTriangles == 0` over 60 s ground + air.
  - `Tail_InsideBounds` (`KitChecks.BoundsProblem` null), `Tail_NoGC`, `Tail_Froude`.
  - REDs: `Red_Tail_WritesSim` (a test-only flag that also writes `sim.Joints` → FlightUntouched fails), `Red_Tail_Limp` (amplitudes 0 → twist test fails).
- [ ] **Step 2:** Run → FAIL. **Step 3:** Implement. **Step 4:** Run → PASS.
- [ ] **Step 5:** Commit `feat(kit): TailFlourish - a living tail (ground loop, air roll and curl) posed over the sim`.

---

### Task 10: The Apex species

**Files:**
- Create: `Tools~/SpeciesGen/Apex.py`, `Config/Creatures/Apex.asset` + `.meta` (new GUID), `Tests/EditMode/CreatureApexTests.cs`
- Modify: `Config/Creatures/CreatureLabRoster.asset` (append the new GUID, aviary, last), `Tests/EditMode/CreatureKitLabTests.cs` (keep/restore `{ "Apex", Habitat.Aviary }`), `Config/Creatures/CATALOGUE.md` + `catalogue.json`

**Interfaces:**
- Consumes: every part of Tasks 3–9; modules `Walk`, `Fly`, `QuadLaunch`, `Wander`, `FlightExcursion` (`SkyHunt` with `handBack 1` only if it keeps every check green); looks `Skin`, `Membrane`, `Layers` rows by kind (`crest`, `pit`, `dewlap`, `wingfan`, `wingstripe`, `tailfan`, `dorsalstripe`); `kityaml.Species`, `add_part`, `add_module`, `save` (writes `.meta` with a fresh guid).
- Produces: `Config/Creatures/Apex.asset`; `CreatureApexTests` helpers `internal static CreatureSpecies Apex()`.

- [ ] **Step 1: Write `Tools~/SpeciesGen/Apex.py`** from scratch (no copy of the deleted generator). Parts in order: `FlowBody body` (head joint 0, rigid head 2, a neck of ~8 fine joints rising so the head is highest, chest with `hump`/`keel`, trunk, a tail ≥ 45 % of the body length with `blade 1`), `Leg2Bone arm` (mirrored, the wing arm at the shoulder joint), `DrakeLeg hind` (mirrored, at the hip), `FleshWing wing` (mirrored, `arm: arm`), `Eyes`, `CrestBeakHead head` (joint 0), `Dewlap throat`, `PitRow spiracles` (mirrored, front third of the neck, high on the underside), `TailFlourish tail` (last). Scale ≈ 4 (fits `FlightBrain.FitsAviary`). Colours from Global Constraints. Run `python Apex.py <TG>`; `creature_kit.py species` → loads, no unknown keys.
- [ ] **Step 2: Write `CreatureApexTests`** (failing until tuned):
  - `Apex_ComposesFromItsOwnParts`: exactly one each of FlowBody, CrestBeakHead, Dewlap, TailFlourish, two FleshWing, two DrakeLeg, two PitRow; **no** `PteroWing`, `LongNeck`, `BeakHead`, `SpineBody`, `Wing`.
  - `Apex_Stance_MatchesTheReference` (walking 20 s, every 0.5 s): head joint is the highest body joint; neck rise angle (chest → head) ≥ 35°; blade tips above the hump by ≥ 0.5 × hump height and behind the shoulder; pads ahead of the hind feet.
  - `Apex_Bob_TravelsDownTheBody` (steady cruise, ≥ 5 beats): girdle vertical peak-to-peak ≥ 0.03 × body length × s; mid-tail peak lags the girdle's by ≥ 0.15 beat; head peak-to-peak ≤ ⅓ × girdle's.
  - `Apex_FlyAndLand`: from the ground under its own brain in the aviary, within 120 s it reaches launch, beat, glide, flare, touchdown and wing-walk again (`PosePhases` channel).
  - RED `Red_Apex_FlatBob` (Fly `kLift` 0.75, `airLevel` 0.8 → bob test fails).
- [ ] **Step 3: Tune the numbers in `Apex.py` only** until `CreatureApexTests` passes (bob: low `kLift`, `airLevel` ~0; AirTwist bob terms only if needed). Then `creature_kit.py check Apex` → all 14 checks green, **no `kKnown` entry**.
- [ ] **Step 4: Lab.** Roster entry (aviary), `creature_kit.py test CreatureKitLabTests` green; `creature_kit.py catalogue --write`; `Catalogue_IsFresh` green.
- [ ] **Step 5: Gates.** Full harness suite green (baseline counts + new tests), `creature_kit.py unity-compile`, `compile_check.py`.
- [ ] **Step 6:** Commit `feat(creatures): Apex - FlowBody, CrestBeakHead, FleshWing, Dewlap, PitRow, DrakeLeg, TailFlourish; lab aviary`.

---

### Task 11: Silhouette sanity check, Unity run, hand-off

**Files:**
- Modify (parent repo): `.claude/skills/creature-kit/SKILL.md` (examples back to `Apex`; status line naming the seven new parts), `references/authoring.md` (a short "Apex parts" recipe: FlowBody + FleshWing + Dewlap + CrestBeakHead + TailFlourish + PitRow + DrakeLeg, with the Inspector knobs)

- [ ] **Step 1:** `creature_kit.py render Apex --phase wing-walk,glide,beat --out <scratch>`; put the side view next to `docs/superpowers/specs/assets/2026-10-20-apex-reference.png`. Check gross reads only: blades rise above the back to the tips behind it, neck raised with head highest, throat sail under the neck, hump and keel present, tail looping up. Fix placement bugs in `Apex.py` (tests must stay green); no taste iteration.
- [ ] **Step 2:** Unity (verify `mcpforunity://instances` says `MarchingCubes@…` on 6000.2.6f2 first): run `TerrainGen.Tests.CreatureKitTests`, then each new part test class and `CreatureApexTests` (one class per `run_tests` job). All green. Marching Cubes > Rebuild Creature Lab (do not stage `CreatureLab.unity` without the user's go-ahead).
- [ ] **Step 3:** Update the skill docs (above); commit in the parent repo with paths only.
- [ ] **Step 4:** Hand-off note to the user: the aviary's location, play-mode setup, what to look at per part (blade height and softness, hump, keel, the flowing neck into the head, throat sail swing, beak crests, breathing holes, tail loop standing and twist flying, the bob travelling down the body) with the knob for each, and the 0.9× / 1.1× individuals side by side.
