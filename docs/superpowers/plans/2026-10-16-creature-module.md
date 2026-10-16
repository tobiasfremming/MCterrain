# Creature Module + Creature Lab Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Procedurally animated, data-driven creatures (v1: a desert monitor lizard) that walk on the density-field terrain, rendered with one GPU-skinned instanced draw per species and a procedural shader. They live in a Creature Lab scene on dunes, with one enclosure per species.

**Architecture:**
- A species is a ScriptableObject.
- A pure-C# `CreatureSim` runs the 3D version of the Manim lizard: chain with cone bend limits, ground-aligned frames, gait-grouped stepping legs and two-bone IK. It writes bone matrices.
- `CreatureMeshBuilder` makes one rest-pose mesh per species. Its vertices carry 2 bone indices and weights.
- `CreatureRenderer` uploads bones to a `GraphicsBuffer` and issues one `Graphics.RenderMeshPrimitives` per species. `Creature.shader` skins in the vertex stage and shades procedurally.
- `CreatureWorld` ticks everything. `CreatureEnclosure` and `CreatureLab` lay out the lab.

**Tech Stack:** Unity 6000.2.6f2, URP 17, D3D11, C# (no Burst/Mathematics), HLSL, NUnit EditMode tests (`TerrainGen.Tests`).

**Spec:** `docs/superpowers/specs/2026-10-16-creature-module-design.md` (parent repo). Read it first; this plan argues from it.

## Global Constraints

- All code and assets go in the submodule `Assets/TerrainGen`, on a new submodule branch **`feat/creatures` cut from `feat/game-integration`**. The parent repo gets only: the scene `Assets/Scenes/CreatureLab.unity`, the submodule pointer bump, the spec and this plan. The parent works on its own branch `feat/creatures` cut from `main`.
- Runtime code goes in the `TerrainGen.Runtime` assembly (`Assets/TerrainGen/Scripts/`), in the global namespace like the surrounding code, under `Scripts/Creatures/`. Tests go in `Assets/TerrainGen/Tests/EditMode/`, namespace `TerrainGen.Tests`.
- No new packages. No `Task.Run` or threadpool. The simulation runs on the main thread.
- Ground comes from the density field, never colliders. Positive density = solid; outward normal = −gradient. Up = `PlanetGravity.UpAt(p)` (injected as `Func<Vector3,Vector3>` so tests can pass their own).
- No GC allocation per frame in `CreatureWorld.Update` or `LateUpdate`, or in the renderer. No per-frame CPU mesh rebuilds.
- Shaders: follow `Shaders/Grass.shader` (`#pragma target 4.5`, `StructuredBuffer` + `SV_InstanceID`, Lighting.hlsl with `_MAIN_LIGHT_SHADOWS _MAIN_LIGHT_SHADOWS_CASCADE _MAIN_LIGHT_SHADOWS_SCREEN` + `_SHADOWS_SOFT` + fog, ShadowCaster with `ApplyShadowBias` and `_CASTING_PUNCTUAL_LIGHT_SHADOW`, DepthOnly).
  - Loop bounds must be uniform.
  - Never leave a StructuredBuffer unbound (bind 1-element placeholders).
  - C# and HLSL structs match field-for-field.
- Don't modify `Config/WorldConfig.asset`. The lab is a flat world (`useGlobe: 0`); no globe scene.
- The lab's world config lives in **`Config/Creatures/`**, not `Config/Test/`. `BiomeTestScenes.Rebuild` makes a scene for every WorldConfig in `Config/Test`.
- Performance targets (measure with Stopwatch; report a before/after table):
  - ≤ 0.1 ms simulation per creature per frame
  - 100 lizards ≤ 3 ms total
  - 1 draw per species plus shadow and depth passes
  - mesh build < 5 ms
- Offline compile gate (no Editor): `python .superpowers/sdd/2026-09-16-terrain-game-integration/compile.py`, from the parent root. Exit 0 = pass. It compiles runtime, Editor and Tests.
- Editor visits follow `.claude/skills/marchingcubes-workflow/SKILL.md`:
  1. Verify that `mcpforunity://instances` lists `MarchingCubes@…` on 6000.2.6f2 (port 8040).
  2. `refresh_unity`, then `read_console`.
  3. Tests with `run_tests` mode `EditMode`, filter `TerrainGen.Tests.Creature`.
  4. Play mode needs `Application.runInBackground = true`.
  5. Screenshots with `manage_camera screenshot`. Look at them.

  Shaders can't be compiled offline. Check `ShaderUtil.ShaderHasError` in the Editor.
- **Test cadence:** EditMode tests need the Editor.
  - "Run test, expect FAIL" for a new type = the offline compile fails with CS0246/CS0117 naming it.
  - "Run test, expect PASS" = offline compile exit 0, **then** `run_tests` in the Editor.
  - If the Editor is unreachable, record the pending test names in the task report and run them at the next Editor visit, before the following task starts. Never mark a task done with unrun tests.

## Conventions every task uses

- **Frame convention:** a rotation's local **+Z = forward** (toward the head), **+Y = up**, **+X = right** = `Vector3.Cross(up, forward)`. Build rotations with `Quaternion.LookRotation(forward, up)`.
- **Bone order** for a species with N spine joints and L legs (`CreatureSpecies` exposes these indices):
  - `0..N-1`: spine bones. Bone i has its origin at joint i and the joint's rotation.
  - `N + 3·leg + 0`: upper limb. Origin at the shoulder, +Z toward the elbow, +Y = pole direction made perpendicular to the bone.
  - `N + 3·leg + 1`: lower limb. Origin at the elbow, +Z toward the foot, same +Y rule.
  - `N + 3·leg + 2`: foot. Origin at the foot point, +Z = attach-joint forward projected onto the ground plane, +Y = ground normal.
  - `N + 3L + 0 / +1`: left and right eye. Origin at the eye centre, rotation = head joint (index 1) rotation.
- **Bone matrices** are `Matrix4x4.TRS(origin, rotation, Vector3.one * sizeScale)` in world space ("bone world").
- **Rest pose** = a fresh `CreatureSim` built on `FlatGroundProbe` (y = 0, up = +Y) at the origin, facing +Z, with sizeScale 1 and not ticked. The mesh is authored in that rest space. Its bind poses are the inverses of the rest bone-world matrices.
- **Skin matrix** = `boneWorld × bindPose`, computed by the renderer.

## Review Focus

1. **Extreme bends.** A tight wander turn at the bend limit. Expect no body self-intersection crease and no leg tube passing through the body. Pinned by `MeshBuilder_MaxBend_NoInvertedTriangles` (Task 5) and the Task 9 screenshot at a sharp turn.
2. **A steep dune face (~30°) under one side of the body.** Feet on the downhill side must still reach the ground: clamp reach, never float more than 2 cm. The body must not sink in. Pinned by `Legs_OnSlope_FeetWithinTolerance` (Task 3).
3. **dt spikes: a hitch frame (dt = 0.25 s) or a paused Editor.** No explosion, NaN or teleport. Pinned by `Sim_LargeDt_StaysFinite_AndChainIntact` (Task 2).
4. **Ground probe misses**: the narrow window misses after a terrain edit (digging) or on chunk-free ground. Fall back to the wide scan; if that misses too, hold the last ground. No NaN, no falling. Pinned by `FieldProbe_WindowMiss_FallsBack_ThenHolds` (Task 1).
5. **The creature spawned on a spot where the enclosure clamp and target disagree** (target outside the safe radius). Containment must still hold. Pinned by `Containment_TargetOutside_HeadStaysInside` (Task 4).

---

### Task 1: Branches, species data, ground probes

**Files:**
- Create: `Scripts/Creatures/CreatureSpecies.cs`, `Scripts/Creatures/GroundProbes.cs`
- Test: `Tests/EditMode/CreatureSpeciesTests.cs`, `Tests/EditMode/CreatureGroundProbeTests.cs`

(All paths are relative to `Assets/TerrainGen/` unless they start with `Assets/` or `docs/`.)

**Interfaces:**
- Produces:
  ```csharp
  public enum CreaturePattern { None = 0, Bands = 1, Spots = 2, Stripes = 3, BandedSpots = 4 }

  [Serializable] public struct SpineJoint {
      public float halfWidth, halfHeight;   // ellipse semi-axes, metres
      public float clearance;               // joint centre height above ground, metres
      public float bendLimitDeg;            // cone half-angle vs previous segment
      public bool rigid;                    // bend limit 0
  }
  [Serializable] public class LegSpec {
      public int attachJoint; public int side;              // side: -1 left, +1 right
      public Vector3 shoulderOffset;                         // attach-joint local frame; x is mirrored by side
      public Vector3 restOffset;                             // foot rest point, attach-joint local frame, x mirrored by side (y ignored: projected to ground)
      public float upperLength, lowerLength, upperRadius, lowerRadius;
      public Vector3 pole;                                   // attach-joint local, x mirrored by side
      public float stepThreshold, stepDuration, stepLift, overshoot;
      public int gaitGroup;
      public float footLength; public int toeCount;
  }
  [Serializable] public struct CreatureLook {
      public Color dorsal, flank, belly, pattern;
      public CreaturePattern patternType;
      public float patternScale, patternContrast, patternSoftness, spotScale;
      public float smoothness, rimStrength, subsurface;
      public float sizeJitter, hueJitter, valueJitter;       // per-individual ranges
  }
  [CreateAssetMenu(menuName = "Marching Cubes/Creature Species")]
  public class CreatureSpecies : ScriptableObject {
      public float spacing; public SpineJoint[] joints;
      public float headCapLength, tailTipLength;
      public LegSpec[] legs;
      public float speed, turnRateDeg, accel, turnSlowdown;
      public float undulationDeg, undulationHz;
      public int subSteps = 2;
      public int eyeJoint = 1; public Vector3 eyeOffset; public float eyeRadius;  // eyeOffset x mirrored
      public int ringSegments = 16, ringsPerSegment = 3;
      public CreatureLook look;
      public int JointCount { get; }        // joints.Length
      public int BoneCount { get; }         // N + 3L + 2
      public int LegBone(int leg, int part);// N + 3*leg + part
      public int EyeBone(int eye);          // N + 3L + eye
      public float BodyLength { get; }      // headCapLength + spacing*(N-1) + tailTipLength
      public float MaxLateralReach { get; } // max(max halfWidth, max over legs |shoulderOffset.x| + upper + lower)
      public string Validate();             // null when valid, else first problem
  }

  public interface IGroundProbe {
      bool Probe(Vector3 near, Vector3 up, float window, out Vector3 point, out Vector3 normal);
  }
  public sealed class FlatGroundProbe : IGroundProbe { public FlatGroundProbe(float height = 0f); }
  public sealed class FieldGroundProbe : IGroundProbe {
      public FieldGroundProbe(DensityField field);
      public int SampleCount;   // cumulative field samples, for perf stats
  }
  ```
- `FieldGroundProbe.Probe`:
  1. Sample at `near ± up·window`.
  2. If air is above and solid below, bisect 12 times; normal = −`Gradient(p, 0.05f, 0f)`.normalized.
  3. Otherwise fall back to `TerrainQuery.TryFindGround(field, near, up, 8f, 16f, …)`.
  4. Return false only if both miss.

- [ ] **Step 1: Branches.**
  - In `Assets/TerrainGen`: `git checkout feat/game-integration && git checkout -b feat/creatures`.
  - In the parent: `git checkout -b feat/creatures`, then commit the spec and this plan (`docs/superpowers/specs/2026-10-16-creature-module-design.md`, `docs/superpowers/plans/2026-10-16-creature-module.md`). Leave the other pre-existing modified files (`.claude/settings.json`, `.mcp.json`, `CLAUDE.md`) unstaged.

- [ ] **Step 2: Write the failing tests.**
  - `CreatureSpeciesTests`:
    - `Validate_RejectsLegAttachOutOfRange` (attachJoint = N → message mentions "attachJoint")
    - `Validate_RejectsZeroSpacing`
    - `Validate_AcceptsLegless` (legs = empty, N = 10 → null)
    - `BoneIndices_Layout` (N = 10, L = 4 → `LegBone(2,1) == 17`, `EyeBone(1) == 23`, `BoneCount == 24`)
    - `MaxLateralReach_UsesLegs` (halfWidth 0.08, a leg with shoulderOffset.x 0.05 and lengths 0.11 + 0.10 → 0.26 ± 1e-5)

    Build species with `ScriptableObject.CreateInstance` and destroy them with `Object.DestroyImmediate` in TearDown.
  - `CreatureGroundProbeTests`, using `PlaneField` / `SphereField` / `TwoLayerField` from `TestFields.cs`:
    - `FieldProbe_Plane_FindsHeight` (height 3, near (0,3.2,0), window 1 → y = 3 ± 1e-3, normal ≈ up within 1e-3)
    - `FieldProbe_Sphere_NormalIsRadial` (r 100, near (0,0,100.3)·dir at 30° → |p| = 100 ± 1e-2, dot(normal, dir) > 0.999)
    - `FieldProbe_WindowMiss_FallsBack_ThenHolds`: plane height 0, near y = 5, window 0.5 → true via fallback, y ≈ 0. Then near y = 50 → false, out params finite.
    - `FieldProbe_TwoLayer_PicksNearestBelowNear` (near (0,1,0), window 2 → y ≈ 0, not the roof at 30)
    - `FlatProbe_ReturnsHeight`

- [ ] **Step 3: Run the offline compile.** Expect FAIL with CS0246 `CreatureSpecies` / `FieldGroundProbe`.
- [ ] **Step 4: Implement both files** to the interfaces above.
- [ ] **Step 5: Compile → exit 0. Editor: run `TerrainGen.Tests.Creature*` → all pass.**
- [ ] **Step 6: Commit** (submodule): `feat(creatures): species data and ground probes`.

---

### Task 2: CreatureSim spine: head, chain, ground, frames, undulation, bounds hook

**Files:**
- Create: `Scripts/Creatures/CreatureSim.cs`, `Scripts/Creatures/EnclosureArea.cs`
- Test: `Tests/EditMode/CreatureSimSpineTests.cs`, `Tests/EditMode/CreatureTestSpecies.cs` (a test helper that builds the species used by the tests)

**Interfaces:**
- Consumes: Task 1 types.
- Produces:
  ```csharp
  public struct EnclosureArea {
      public Vector3 center, up; public float radius, safeRadius;
      public static EnclosureArea For(Vector3 center, Vector3 up, float radius, CreatureSpecies sp, float sizeScale, float margin = 0.2f);
          // safeRadius = radius - sizeScale * (sp.MaxLateralReach + margin); clamped >= 0
      public float PlanarDistance(Vector3 p);       // distance from center in the plane ⟂ up
      public Vector3 ClampToSafe(Vector3 p);        // planar clamp to safeRadius, keeps the up-component
      public Vector3 RandomSafePoint(ref uint rng); // uniform in the safe disc (xorshift32 state)
  }
  public sealed class CreatureSim {
      public CreatureSim(CreatureSpecies sp, IGroundProbe ground, Func<Vector3, Vector3> upAt,
                         Vector3 position, Vector3 forward, float sizeScale = 1f, int seed = 0);
      public readonly CreatureSpecies Species; public readonly float SizeScale;
      public readonly Vector3[] Joints; public readonly Quaternion[] Rotations;   // per spine joint
      public readonly Vector3[] GroundNormals;                                    // smoothed, per joint
      public EnclosureArea? Bounds;                                               // when set, head is clamped to safe disc
      public float Speed { get; }   // current head speed m/s
      public float Time { get; }
      public void Tick(float dt, Vector3 target);   // splits into Species.subSteps; dt clamped to 0.1 s per call
      public void WriteBoneWorld(Matrix4x4[] dst, int offset);  // all BoneCount bones (legs/eyes filled from Task 3; until then legs write identity at the shoulder)
  }
  ```
- Construction places joints straight behind `position` along −`forward` at `spacing·sizeScale` and grounds them. Legs are initialised planted at their rest points (Task 3).

**Algorithm per sub-step (pins what the tests check):**
1. Head steering:
   - Desired direction = target − head, projected onto the plane ⟂ up(head). Rotate it about up by `undulationDeg·sin(2π·undulationHz·t)`.
   - Turn the heading toward it by at most `turnRateDeg·dt`.
   - Speed approaches `min(speed, 2.5·dist)·(1 − turnSlowdown·|turnAngle|/π)` at `accel` m/s².
   - Move the head along the heading. If `Bounds` is set, apply `ClampToSafe`.
2. Chain, for i = 1..N−1:
   - dir = normalize(J[i] − J[i−1]), limited by `Vector3.RotateTowards(prevBack, dir, limitRad, 0)`, where prevBack is the previous segment's backward direction (−heading for i = 1) and the limit is 0 if rigid.
   - J[i] = J[i−1] + dir·spacing·sizeScale.
3. Ground: for each joint, probe near the joint's previous ground point with window `0.5 m·sizeScale`. Smooth the height offset and normal with `1 − exp(−dt/0.06)`. Set J[i] = ground + up·clearance·sizeScale. If the probe returns false, hold the previous ground.
4. Frames: forward_i = normalize(J[i−1] − J[i]) (head: heading). up_i = smoothed normal made perpendicular to forward_i. `Rotations[i] = LookRotation(forward_i, up_i)`.

- [ ] **Step 1: Write the failing tests** (`CreatureTestSpecies.Lizardish()`: N = 20, spacing 0.06, halfWidth 0.06, clearance 0.1, bend 20°, joint 1 rigid, 4 legs as the Task 7 lizard, speed 0.9, turn 160°/s):
  - `Chain_SegmentLengthsExact`: after 300 ticks of 1/60 s chasing a circling target on `PlaneField`, every |J[i] − J[i−1]| = spacing ± 2e-3. This holds because the test species has constant clearance on a flat plane; grounding then moves no joint relative to its neighbours.
  - `Chain_BendWithinLimit`: angle between consecutive segment directions ≤ 20° + 0.5°. The rigid joint ≤ 0.5°.
  - `Joints_SitAtClearance_OnPlane`: y = height + 0.1 ± 2e-3.
  - `Frames_Orthonormal_AndUpAlignedToGround`: on `SphereField`, `Rotations[i]·up` dotted with the radial direction > 0.98.
  - `Undulation_ProducesLateralSway`: with undulationDeg 30 and Hz 1, walking toward a far target, the head's lateral offset from the straight line has peak-to-peak > 0.05 m. With undulationDeg 0 it stays < 0.005 m.
  - `Sim_LargeDt_StaysFinite_AndChainIntact`: Tick(0.25) ×5, then Tick(0). All finite; the segment invariant holds.
  - `Bounds_ClampHead` (unit-level): with `Bounds` set radius 3, target 20 m away, after 600 ticks the head's `PlanarDistance` ≤ safeRadius + 1e-3.
- [ ] **Step 2: Compile.** Expect FAIL (`CreatureSim` missing).
- [ ] **Step 3: Implement** `EnclosureArea` and the `CreatureSim` spine to the algorithm above. Use no allocations in `Tick`: preallocate everything in the constructor.
- [ ] **Step 4: Compile 0; Editor tests pass.**
- [ ] **Step 5: Commit** `feat(creatures): spine simulation`.

---

### Task 3: Legs: rest points, gait groups, stepping, two-bone IK, bone output

**Files:**
- Create: `Scripts/Creatures/TwoBoneIK.cs`, `Scripts/Creatures/CreatureLegs.cs` (internal leg-state logic called from `CreatureSim`)
- Modify: `Scripts/Creatures/CreatureSim.cs` (call the legs each sub-step; complete `WriteBoneWorld`)
- Test: `Tests/EditMode/CreatureIKTests.cs`, `Tests/EditMode/CreatureLegTests.cs`

**Interfaces:**
- Produces:
  ```csharp
  public static class TwoBoneIK {
      // Returns the elbow. `foot` = target if reachable, else the clamped reach point along shoulder->target.
      public static Vector3 Solve(Vector3 shoulder, Vector3 target, float l1, float l2, Vector3 pole, out Vector3 foot);
  }
  public struct LegState {
      public Vector3 shoulder, elbow, foot, footNormal, stepFrom, stepTo;
      public bool stepping; public float stepT;
  }
  // on CreatureSim:
  public readonly LegState[] Legs;
  public int StepsTaken;     // cumulative, for tests/stats
  ```
- Leg rules per sub-step:
  - **Rest point:** attach-joint frame × mirrored `restOffset`, scaled, then probed to the ground (window 0.5·scale).
  - **Eligible to step** if:
    - `|foot − rest| > stepThreshold·scale`, or
    - Speed < 0.05 and `|foot − rest| > 0.3·threshold`. This is the idle tidy-up.
  - **Start a step** only if no leg of a *different* gaitGroup is stepping. If the leg's group was the last to step and another group has an eligible leg, wait.
  - **Step:**
    - Goal = rest + attach-forward·overshoot·scale, probed once at step start into `stepTo`/`footNormal`.
    - `stepT += dt/stepDuration`. foot = Lerp(stepFrom, stepTo, smoothstep(stepT)) + up·stepLift·scale·sin(π·stepT).
    - The step ends at stepT ≥ 1.
  - **Planted feet never move.**
  - **IK:**
    - shoulder = attach frame × mirrored shoulderOffset.
    - Pole in world = attach rotation × mirrored pole.
    - elbow = `TwoBoneIK.Solve`, with lengths scaled.
  - **Bones:** written per the Conventions.

- [ ] **Step 1: Write the failing tests.**
  - `CreatureIKTests`:
    - `Reachable_ExactLengths` (shoulder 0, target (0.15,−0.1,0.05), l1 0.11, l2 0.10 → |elbow| = 0.11 ± 1e-4, |foot − elbow| = 0.10 ± 1e-4, foot = target ± 1e-4)
    - `Unreachable_ClampsAlongDirection` (target at 0.5 → foot at 0.21 − ≤1e-3 along the direction)
    - `ElbowOnPoleSide` (dot(elbow − midpoint(shoulder, foot), pole⊥) > 0 for poles ±X, ±Z)
    - `Degenerate_TargetAtShoulder_Finite`
  - `CreatureLegTests`, using lizard-ish legs, a straight 10 s walk on a plane at 1/60:
    - `Gait_NeverTwoGroupsSteppingAtOnce` (check each tick)
    - `Gait_EveryLegSteps` (each leg ≥ 5 steps)
    - `PlantedFeet_DoNotMove` (for each leg, across ticks where stepping is false at both ends, the foot delta < 1e-5)
    - `Legs_OnSlope_FeetWithinTolerance`: a plane tilted 30° about the walking direction. Use a local `TiltedPlaneField` added to `TestFields.cs`: `Sample = −dot(p, n)` with n the tilted normal. Every planted foot's distance to the surface < 0.02.
    - `LegLengths_NeverExceeded` (|elbow − shoulder| = l1 ± 1e-3 and |foot − elbow| ≤ l2 + 1e-3)
    - `Idle_FeetSettleUnderBody`: after walking, then target = head for 3 s, every foot within 0.3·threshold + 0.01 of its rest point.
- [ ] **Step 2: Compile → FAIL.**
- [ ] **Step 3: Implement** `TwoBoneIK.Solve` (law of cosines, as in `video_manim/lizard.py` `Leg.ik`, with the bend plane spanned by shoulder→target and the pole). Implement the leg rules in `CreatureLegs`, and the remaining `WriteBoneWorld` bones.
- [ ] **Step 4: Compile 0; Editor tests pass** (including the Task 2 tests still).
- [ ] **Step 5: Commit** `feat(creatures): legs, gait and IK`.

---

### Task 4: Brain, wander, containment

**Files:**
- Create: `Scripts/Creatures/WanderBrain.cs`
- Test: `Tests/EditMode/CreatureContainmentTests.cs`

**Interfaces:**
- Produces:
  ```csharp
  public interface ICreatureBrain { Vector3 Target(CreatureSim sim, float dt); }
  public sealed class WanderBrain : ICreatureBrain {
      public WanderBrain(EnclosureArea area, int seed, float pauseMin = 0.5f, float pauseMax = 3f, float arriveRadius = 0.4f);
  }
  ```
- Behaviour:
  - **Pick a target.** Take `RandomSafePoint` candidates, up to 8 tries, and keep the first whose bearing from the current heading is between 25° and 120°. If none qualifies, take the last candidate.
  - **Walk** to the target until the head is within `arriveRadius`.
  - **Pause** for U(pauseMin, pauseMax). During the pause the target is the head position.
  - **Look around** in 30% of pauses: for 0.6 s mid-pause, the target is head + 0.3 m at ±50° from the heading.

- [ ] **Step 1: Write the failing tests** (lizard-ish species, `PlaneField` and a `SphereField` r = 500 variant; area radius 8; `sim.Bounds = area`):
  - `Containment_LongWander_AllJointsAndFeetInside`: 20 simulated minutes at 1/30 s, seeds 1–5. Every joint's and every foot's `PlanarDistance` ≤ radius, checked every tick.
  - `Containment_TargetOutside_HeadStaysInside`: the brain is replaced by a target 30 m away for 60 s. Every joint stays inside.
  - `Wander_IsDeterministicPerSeed` (two runs with seed 3 → identical head positions after 2 min)
  - `Wander_CoversEnclosure`: after 10 min, the head has visited ≥ 6 of 8 angular sectors of the safe disc.
- [ ] **Step 2: Compile → FAIL.**
- [ ] **Step 3: Implement `WanderBrain`.** If containment fails on the tail, the fix is in `EnclosureArea.For` margin or `MaxLateralReach`, not a per-joint clamp. The spec's guarantee comes from the head path.
- [ ] **Step 4: Compile 0; Editor tests pass.**
- [ ] **Step 5: Commit** `feat(creatures): wander brain and containment`.

---

### Task 5: Rest pose and CreatureMeshBuilder

**Files:**
- Create: `Scripts/Creatures/CreatureRestPose.cs`, `Scripts/Creatures/CreatureMeshBuilder.cs`
- Test: `Tests/EditMode/CreatureMeshTests.cs`

**Interfaces:**
- Produces:
  ```csharp
  public static class CreatureRestPose {
      public static Matrix4x4[] BoneWorld(CreatureSpecies sp);  // rest sim per Conventions
      public static Matrix4x4[] BindPoses(CreatureSpecies sp);  // inverses of BoneWorld
  }
  public static class CreatureMeshBuilder {
      public const int PartBody = 0, PartLeg = 1, PartFoot = 2, PartEye = 3;
      public static Mesh Build(CreatureSpecies sp);
  }
  ```
- **Vertex layout:**
  - position and normal in rest space
  - `uv0` (Vector2) = (arc length along the part in metres, angle/2π)
  - `uv1` (Vector2) = (part id, dorsal coordinate −1 belly … +1 spine ridge)
  - `uv2` (Vector4) = (bone0, bone1, w0, w1), with w0 + w1 = 1

  Use `mesh.indexFormat = UInt32` if verts > 65535. Mesh bounds = rest bounds.
- **Body:**
  - `ringsPerSegment` rings per spine segment. Ring centre and frame come from Catmull-Rom over the rest joints; the semi-axes come from Catmull-Rom over halfWidth and halfHeight.
  - `ringSegments` vertices per ring.
  - Normal = the ellipse normal tilted by the taper slope (d radius / d arc length).
  - Head cap: `headCapLength` with 4 rings, elliptical profile to the snout tip. Tail tip: `tailTipLength` cone to a point.
  - Weights: the two bracketing spine joints by fraction along the segment, smoothstepped.
- **Legs:**
  - Each limb is a tapered tube (8 segments, 5 rings) from upperRadius to lowerRadius.
  - The last and first 20% of the upper and lower bones blend 50/50 at the knee.
  - The upper tube's first ring is skinned to the attach spine bone, so the shoulder stays buried in the body. It extends 0.6·upperRadius into the body (a shoulder blob).
  - Foot: a flattened ellipsoid pad of `footLength` plus `toeCount` tapered toe nubs fanned ±40°, rigid to the foot bone.
- **Eyes:** UV spheres (8×6) at the mirrored `eyeOffset`, radius `eyeRadius`, rigid to the eye bones.

- [ ] **Step 1: Write the failing tests:**
  - `Build_Lizardish_WeightsSumToOne_IndicesInRange`
  - `Build_NoDegenerateTriangles` (area > 1e-10)
  - `Build_NormalsOutward` (for body verts, dot(normal, vert − ring centre) > 0)
  - `Build_Legless_HasNoLegParts` (snake-like N = 40, L = 0)
  - `Build_Hexapod_Builds`
  - `RestPose_BindTimesWorldIsIdentity` (‖BoneWorld[i]·BindPoses[i] − I‖∞ < 1e-4)
  - `MeshBuilder_MaxBend_NoInvertedTriangles`: skin the rest mesh on the CPU with bone worlds from a sim whose chain is bent to the limit everywhere (target circling at minimum radius for 5 s). Every triangle's skinned normal must satisfy dot > 0 with its rest normal rotated by its bone0 rotation.
  - `Build_Time_Under5ms` (Stopwatch, median of 5 builds)
- [ ] **Step 2: Compile → FAIL.**
- [ ] **Step 3: Implement both classes.**
- [ ] **Step 4: Compile 0; Editor tests pass.**
- [ ] **Step 5: Commit** `feat(creatures): rest pose and skinned mesh builder`.

---

### Task 6: CreatureRenderer + Creature.shader

**Files:**
- Create:
  - `Scripts/Creatures/CreatureRenderer.cs`
  - `Shaders/Creature.shader`
  - `Shaders/Creature/CreatureSkin.hlsl` (bone blend + the `CreatureDisplace` hook)
  - `Shaders/Creature/CreaturePattern.hlsl`
  - `Shaders/Creature/CreatureLighting.hlsl`
- Test: `Tests/EditMode/CreatureRendererTests.cs`

**Interfaces:**
- Consumes: `CreatureMeshBuilder.Build`, `CreatureRestPose.BindPoses`, `CreatureSim.WriteBoneWorld`.
- Produces:
  ```csharp
  [StructLayout(LayoutKind.Sequential)]
  public struct CreatureInstance { public float seed, hueShift, valueShift, sizeScale; }   // 16 bytes; HLSL struct CreatureInstance { float seed, hueShift, valueShift, sizeScale; }
  public sealed class CreatureRenderer : IDisposable {
      public CreatureRenderer(CreatureSpecies sp, Material material);
      public void Add(CreatureSim sim, CreatureInstance inst);
      public bool Remove(CreatureSim sim);
      public int Count { get; }
      public void Render();          // call once per frame from LateUpdate
      public Mesh Mesh { get; }
      public void Dispose();
  }
  ```
- **`Render`:**
  - For each sim: `WriteBoneWorld` into a reusable `Matrix4x4[]`, then multiply by the bind poses into `_skin` (a `Matrix4x4[]` sized to Count·BoneCount).
  - `GraphicsBuffer.SetData`. Grow by doubling on Add; never allocate in Render.
  - `worldBounds` = union of the sims' joint bounds, expanded by the reach.
  - One `Graphics.RenderMeshPrimitives(rp, Mesh, 0, Count)`, with `rp.matProps` carrying `_Bones`, `_Instances`, `_BonesPerCreature`, plus the look values: `_Dorsal`, `_Flank`, `_Belly`, `_PatternColor`, `_PatternType`, `_PatternParams` = (scale, contrast, softness, spotScale), `_SurfaceParams` = (smoothness, rim, subsurface, 0).
  - Shadows: `ShadowCastingMode.On`, `receiveShadows = true`.
- **Shader `MarchingCubes/Creature`:**
  - Vertex:
    - Instance i = SV_InstanceID. Bones from `_Bones[i·_BonesPerCreature + b]`.
    - Linear-blend the position and normal.
    - Call `CreatureDisplace(inout float3 posWS, float3 nrmWS, float2 uv0, float2 uv1, CreatureInstance inst)`, which is a no-op in v1.
  - Fragment:
    - **Pattern.** Base colour = lerp(belly → flank → dorsal) by the dorsal coordinate. Then `CreaturePattern(uv0, uv1, inst.seed, _PatternType, _PatternParams)`, a mask from value noise in uv0 space with uniform loops only. Then a hue/value jitter per instance.
    - **Lighting.** Wrapped Lambert (wrap 0.3), main light with `MainLightRealtimeShadow`, SH ambient, GGX specular from smoothness, rim, and a warm subsurface tint near the terminator. Then fog.
    - **Eyes** (part id 3): black, smoothness 0.9.
  - Passes: Forward, ShadowCaster, DepthOnly, as in Grass.shader.
- **Material asset:** `Config/Creatures/Creature.mat`, `enableInstancing` not required (procedural draw).

- [ ] **Step 1: Write the failing tests:**
  - `Renderer_GrowsWithoutLosingSims` (add 3, remove 1, add 40 → Count 42)
  - `Renderer_SkinMatricesAreIdentityAtRest` (a sim at rest pose → every `_skin` entry ≈ I within 1e-4; expose `internal Matrix4x4[] SkinForTest`, with `InternalsVisibleTo("TerrainGen.Tests")` in an `AssemblyInfo.cs` in Scripts/Creatures)
  - `Instance_StructIs16Bytes` (`Marshal.SizeOf<CreatureInstance>() == 16`)
- [ ] **Step 2: Compile → FAIL.**
- [ ] **Step 3: Implement the renderer and shader files.**
- [ ] **Step 4: Compile 0; Editor tests pass.** Then **Editor shader gate:**
  - `ShaderUtil.ShaderHasError(Shader.Find("MarchingCubes/Creature")) == false`, and the console is clean.
  - Spike scene check, not committed: a temp scene with a plane, 2 sims with different `hueShift` drawn by one renderer. Take a screenshot. Both visible, distinct colours, casting shadows. This confirms SV_InstanceID = 0..n−1 on D3D11.
  - If they draw identically or only one shows, switch to `Graphics.RenderMeshIndirect` with `IndirectDrawIndexedArgs` and re-check.
- [ ] **Step 5: Commit** `feat(creatures): instanced skinned renderer and creature shader`.

---

### Task 7: The desert monitor asset + CreatureWorld

**Files:**
- Create: `Scripts/Creatures/CreatureWorld.cs`, `Config/Creatures/DesertMonitor.asset`
- Test: `Tests/EditMode/CreatureWorldTests.cs`

**Interfaces:**
- Produces:
  ```csharp
  public sealed class CreatureWorld : MonoBehaviour {
      public Material creatureMaterial;
      public static CreatureWorld Instance { get; }
      public CreatureSim Spawn(CreatureSpecies sp, Vector3 position, Vector3 forward, ICreatureBrain brain, EnclosureArea? bounds, int seed);
      public IGroundProbe Ground { get; }  // FieldGroundProbe(MCChunkManager.Instance.PhysicsField) at runtime; settable for tests: public void SetGround(IGroundProbe g, Func<Vector3,Vector3> upAt)
      public IReadOnlyList<CreatureSim> Sims { get; }
      public double LastSimMs { get; }     // Stopwatch around Update's tick loop
  }
  ```
  - `Update`: `target = brain.Target(sim, dt)`, then `sim.Tick(dt, target)`.
  - `LateUpdate`: every renderer's `Render()`. There is one renderer per species, created on first spawn.
  - Per-individual `CreatureInstance` comes from the seed through the look's jitter ranges. sizeScale = 1 ± sizeJitter.
  - `OnDestroy` disposes the renderers.
- **DesertMonitor.asset, starting values** (tuned in Task 9):
  - spacing 0.06, 26 joints, length ≈ 1.56 m.
  - (halfWidth, halfHeight) per joint:
    - 0: .022/.018, 1: .032/.026 (rigid), 2: .040/.032 (rigid), 3: .036/.030
    - 4: .034/.030, 5: .036/.032, 6: .050/.040, 7: .062/.046, 8: .072/.052, 9: .080/.056
    - 10: .085/.058, 11: .084/.057, 12: .078/.054, 13: .066/.050, 14: .052/.044, 15: .044/.038
    - 16: .038/.033, 17: .033/.029, 18: .028/.025, 19: .024/.021, 20: .020/.018, 21: .017/.015
    - 22: .014/.012, 23: .011/.010, 24: .008/.007, 25: .005/.005
  - Clearance = halfHeight + lift: lift 0.06 for joints 0–13, falling linearly to 0 at joint 18, then 0.
  - Bend limit 20° (tail joints 14+: 25°).
  - headCapLength 0.05, tailTipLength 0.04.
  - **Legs.** Front legs at joint 7, rear legs at joint 13.
    - shoulderOffset (0.05, −0.01, 0), mirrored by side.
    - restOffset: front (0.20, 0, 0.06), rear (0.20, 0, −0.02).
    - Lengths: upper 0.11, lower 0.10. Radii: upper 0.022, lower 0.015.
    - Pole: front (0.3, 0.6, −1), rear (0.3, 0.6, 1).
    - stepThreshold 0.11, stepDuration 0.16, stepLift 0.04, overshoot 0.06.
    - Gait groups: FL + RR = 0, FR + RL = 1.
    - footLength 0.045, toeCount 5.
  - **Locomotion:** speed 0.9, turnRateDeg 160, accel 3, turnSlowdown 0.5, undulationDeg 6, undulationHz 1.4.
  - **Eyes:** eyeJoint 1, eyeOffset (0.024, 0.014, 0.008), radius 0.007.
  - **Look:**
    - Colours: dorsal #C9A46A, flank #B9844E, belly #E8D9B5, pattern #4A3322.
    - BandedSpots: scale 9, contrast 0.8, softness 0.25, spotScale 0.35.
    - Surface: smoothness 0.35, rim 0.25, subsurface 0.3.
    - Jitter: size 0.08, hue 0.03, value 0.06.

- [ ] **Step 1: Write the failing tests:**
  - `World_SpawnTickRender_NoAllocAfterWarmup`: an EditMode test with `SetGround(new FlatGroundProbe(), _ => Vector3.up)` and 3 sims. Call Update/LateUpdate through reflection, warm up for 10 frames, then the `GC.GetAllocatedBytesForCurrentThread()` delta over 60 frames must be 0.
  - `DesertMonitor_Validates` (load via `AssetDatabase.LoadAssetAtPath` → `Validate() == null`)
  - `DesertMonitor_Is1_5mLong` (BodyLength 1.5–1.65)
- [ ] **Step 2: Compile → FAIL.**
- [ ] **Step 3: Implement `CreatureWorld`.** Author the asset; editing its YAML is acceptable, but prefer creating it through `CreateAssetMenu` in the Editor.
- [ ] **Step 4: Compile 0; Editor tests pass.**
- [ ] **Step 5: Commit** `feat(creatures): creature world and desert monitor`.

---

### Task 8: Enclosure, Creature Lab component, lab config and scene

**Files:**
- Create:
  - `Scripts/Creatures/CreatureEnclosure.cs`
  - `Scripts/Creatures/CreatureLab.cs`
  - `Editor/CreatureLabScene.cs`
  - `Config/Creatures/CreatureLabWorldConfig.asset` (copy of `Config/Test/DesertWorldConfig.asset`, same `defaultDensity` = DesertWorld, `useGlobe: 0`, **`enablePlants: 0`**)
  - `Config/Creatures/EnclosureBorder.mat` (URP/Lit, #B89A72, smoothness 0.15)
  - parent: `Assets/Scenes/CreatureLab.unity`
- Test: `Tests/EditMode/CreatureEnclosureTests.cs`

**Interfaces:**
- Produces:
  ```csharp
  public sealed class CreatureEnclosure : MonoBehaviour {
      public float radius = 8f, curbHeight = 0.12f, curbWidth = 0.3f; public int segments = 128;
      public Material borderMaterial;
      public EnclosureArea AreaFor(CreatureSpecies sp, float sizeScale);
      public static Mesh BuildCurb(IGroundProbe ground, Vector3 center, Vector3 up, float radius, float height, float width, int segments);
  }
  public sealed class CreatureLab : MonoBehaviour {
      public CreatureSpecies[] species; public float spacing = 25f, arcRadius = 30f; public int seed = 7;
      public float searchRadius = 15f;   // flat-spot search around each arc slot
  }
  ```
- **`BuildCurb`:** a closed ring strip, with each vertex probed to the ground. The cross-section is a rounded trapezoid (bottom width w, top 0.6w, height h). It sinks 3 cm into the sand so slopes show no gap.
- **`CreatureLab.Start`** waits until `MCChunkManager.Instance` and the ground probe succeed at the player's position, polling each frame up to 10 s. Then, for species k:
  1. Arc slot = player spawn + rotate(forward, (k − (n−1)/2)·spacing/arcRadius rad)·arcRadius.
  2. Pick the flattest of 16 probed candidates within `searchRadius`. Flatness = the minimum over 8 rim probes of dot(normal, up).
  3. Place a `CreatureEnclosure` with radius = max(8, 5·BodyLength·sizeScale) and build its curb.
  4. Spawn one creature at the centre with a `WanderBrain(area, seed + k)` and `Bounds = area`.
- **`CreatureLabScene`:** menu `Marching Cubes/Rebuild Creature Lab`.
  - Same copy approach as `BiomeTestScenes`: requires SampleScene active; copies the roots `Directional Light`, `Global Volume`, `Player`, `TargetTransform`, `Terrain`, `TerrainGrass` (not `PlantScatter`). Refactor the shared copy/remap code out of `BiomeTestScenes` into an internal helper rather than duplicating it.
  - Sets `worldConfig` to `Config/Creatures/CreatureLabWorldConfig`.
  - Adds a `Creatures` root with `CreatureWorld` (material `Creature.mat`) and `CreatureLab` (species = [DesertMonitor], border material).
  - Saves `Assets/Scenes/CreatureLab.unity`.

- [ ] **Step 1: Write the failing tests:**
  - `Curb_FollowsGround` (`FlatGroundProbe(2)` → every vertex y in [2 − 0.03 − 1e-4, 2 + 0.12 + 1e-4])
  - `Curb_IsClosedRing` (first and last ring cross-sections share vertices or are within 1e-5)
  - `Area_RadiusScalesWithSpecies` (`AreaFor` with sizeScale 1.1 → safeRadius = radius − 1.1·(MaxLateralReach + 0.2))
  - `Lab_ArcSlots_Spaced` (expose `internal static Vector3 ArcSlot(Vector3 origin, Vector3 fwd, int k, int n, float spacing, float arcRadius)`; adjacent slots 25 ± 0.5 m apart)
  - `LabConfig_PlantsOff_FlatWorld` (load the asset: `enablePlants == false`, `useGlobe == false`, `defaultDensity` == DesertWorld)
- [ ] **Step 2: Compile → FAIL.**
- [ ] **Step 3: Implement all files.** Run the menu in the Editor (via `execute_code` calling the static `CreatureLabScene.Rebuild()`). Then run `BiomeTestScenes.Rebuild()` once and confirm its report lists only the 8 biome scenes, and that `Assets/Scenes/Biomes/` gained no CreatureLab scene.
- [ ] **Step 4: Compile 0; Editor tests pass. Play the lab:**
  - The lizard wanders inside a visible curb ring on dunes.
  - Screenshot from the player's spawn. The player can walk in and out.
- [ ] **Step 5: Commit** in the submodule: `feat(creatures): enclosures and creature lab`. In the parent, commit the scene and bump the submodule pointer: `feat: creature lab scene`.

---

### Task 9: Debug view, look polish, perf verification

**Files:**
- Create: `Scripts/Creatures/CreatureDebugView.cs`
- Modify: `Config/Creatures/DesertMonitor.asset` and the shader files (tuning only)
- Test: `Tests/EditMode/CreaturePerfTests.cs`

**Interfaces:**
- Produces: a `CreatureDebugView : MonoBehaviour` on the `Creatures` root.
  - `F3` toggles it (legacy `Input.GetKeyDown`, as in `SimplePlayerController`).
  - Draws with `GL.LINES` in `OnRenderObject`, using a cached `Hidden/Internal-Colored` material:
    - the chain (grey), with the head in orange #FFB347
    - joint ellipses in the joint frames (blue #5AA9E6)
    - rest points (small crosses)
    - shoulder–elbow–foot lines (green #6FBF7C)
    - the enclosure safe disc
  - These are the video's colours. No allocations.

- [ ] **Step 1: Write the failing perf tests** (EditMode, `FieldGroundProbe` on a `DuneHeightfield` loaded from `Config/DuneField.asset`, so the real per-sample cost is measured):
  - `Perf_OneLizard_Under0_1ms` (median per-frame Tick over 300 frames after 60 warm-up frames)
  - `Perf_100Lizards_Under3ms`
  - Log `FieldGroundProbe.SampleCount` per frame.

  If either fails, change the ground strategy as the spec allows, in this order:
  1. Probe spine joints once per frame instead of every sub-step.
  2. Probe every 2nd joint and interpolate the others.
  3. A per-sim 2-entry height cache keyed on a 0.25 m cell.

  Re-run the tests and record the before/after table in the task report. `Legs_OnSlope_FeetWithinTolerance` and `Joints_SitAtClearance_OnPlane` must still pass.
- [ ] **Step 2: Implement `CreatureDebugView`; compile 0.**
- [ ] **Step 3: Look pass in play mode in the lab.** Take screenshots at these framings:
  1. 3 m side view
  2. 1.5 m close-up of head and front leg
  3. top-down mid-turn at the bend limit
  4. on a dune slope
  5. F3 on

  Judge each against the spec's anti-goals: no sausage segmentation, no facets, no creases, no foot slide, no float or sink, no leg pop-through. Also judge against the desert monitor description. Tune the asset and shader constants, not the code paths, until all five pass. Keep the screenshots out of `Assets/` (delete them after).
- [ ] **Step 4: Read stats back in play mode:** `CreatureWorld.LastSimMs`, draw count from the Frame Debugger or `UnityStats`, and `GC.GetAllocatedBytesForCurrentThread` delta over 120 frames. Record them against the targets.
- [ ] **Step 5: Commit** `feat(creatures): debug view, monitor look pass, perf`. Bump the parent pointer.

---

### Task 10: Extensibility proof: snake and hexapod

**Files:**
- Create: `Config/Creatures/TestSnake.asset`, `Config/Creatures/TestHexapod.asset`
- Test: `Tests/EditMode/CreatureExtensibilityTests.cs`
- **No changes allowed** to `CreatureSim.cs`, `CreatureLegs.cs`, `CreatureMeshBuilder.cs`, `CreatureRenderer.cs` or the shaders. If one is needed, stop and report it. That is a design bug, not a task fix.

**Assets:**
- **Snake:**
  - spacing 0.05, 40 joints. halfWidth ramps from 0.02 at the head to 0.035 mid-body to 0.004 at the tail; halfHeight = 0.8·halfWidth. clearance = halfHeight.
  - Bend limit 30°, no legs.
  - undulationDeg 35, undulationHz 0.8, speed 0.6.
- **Hexapod:**
  - spacing 0.05, 8 joints. Legs at joints 2, 4 and 6, both sides.
  - Lengths: upper 0.12, lower 0.14. Gait groups as tripods: L2 + R4 + L6 = 0, R2 + L4 + R6 = 1.
  - Pole up (0, 1, 0).

- [ ] **Step 1: Write the tests:**
  - `Snake_BuildsAndWanders_Contained` (mesh builds; 5 min wander in an 8 m area; all joints inside)
  - `Snake_Undulates` (lateral peak-to-peak > 0.15 m on a straight approach)
  - `Hexapod_TripodGait_NeverOverlaps`
  - `Hexapod_EveryLegSteps`
  - `Hexapod_FeetPlanted_DoNotMove`
- [ ] **Step 2: Author the assets; compile 0; Editor tests pass.**
- [ ] **Step 3: Editor check:**
  - Temporarily add both to the lab's species list in play mode (not saved).
  - Confirm three enclosures appear and all three creatures render and move. Take a screenshot.
  - Remove them again, so the saved lab stays lizard-only.
- [ ] **Step 4: Commit** `test(creatures): snake and hexapod extensibility proof`. Bump the parent pointer. Then run the whole `TerrainGen.Tests` + `TerrainGen.LSystem.Tests` EditMode suite and record the pass count. The baseline is 95 plus all the new tests.
