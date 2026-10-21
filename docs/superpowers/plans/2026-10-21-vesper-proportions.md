# Vesper Proportions (rev 2) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give Vesper the reference's humpbacked build (high hips, hump peak, flat neck to a shorter head, long tail, long
metatarsus, knuckles forward and out, longer strides), shortening head and neck by closer joints via a new opt-in
per-joint spine spacing.

**Architecture:** Task 1 adds per-segment spine lengths to the shared chain: a FlowBody profile channel compiles to
`CreatureSpecies.segmentLengths`, and every consumer on Vesper's path reads segment lengths through one helper instead of
`sp.spacing`; empty = today's uniform chain, bit-identical. Task 2 retunes `Vesper.py` onto it and the Vesper tests.

**Tech Stack:** Unity 6000.2.6f2 C#, offline harness `Tools~/CreatureHarness` via
`.claude/skills/creature-kit/scripts/creature_kit.py`, `Tools~/SpeciesGen/Vesper.py` (kityaml).

**Spec:** `docs/superpowers/specs/2026-10-21-vesper-proportions-design.md` (parent repo). Earlier: `2026-10-21-vesper-skeleton-design.md`.

## Global Constraints

- Shared changes opt-in, off by default; every shipped species bit-identical (CreatureFlightGoldenTests, LegacyLegsGoldenTests, kit goldens).
- Zero GC per frame; main thread; a RED proof per new invariant (test fails with the change reverted / the flag off).
- Sizes scale by Froude: lengths x s, times x sqrt s. Numbers in Vesper.py are scale 1 metres; SCALE stays 4.
- Work in worktree `C:/Users/tobia/Documents/unity_stuff/wt/vesper`, branch `feat/vesper`; harness commands take `--tg C:/Users/tobia/Documents/unity_stuff/wt/vesper/Assets/TerrainGen`.
- Run test classes one at a time (machine memory). Unity is the user's open Editor: do not drive it; offline only.
- The user judges the look; deliver code + correctness tests + a look checklist.

## Review Focus

1. A uniform species (every shipped one) must take exactly the old code path — not "the same lengths through new arithmetic" that differs in the last float bit. Task 1 Step 1 goldens.
2. The bind/rest (`CreatureSim.RestRun`, `restAtSpacing`, `CreatureRestPose.BindSim`, AirChain stance pitch, CreatureWings rest) with varying segments: the stood-up rest must match the walking stance, no stretched segment. Task 1 test `VaryingSpacing_RestMatchesStance`.
3. Flight's own segment loops (CreatureFlight lines ~817/843/909/1261/1281, AirChain `seg`) silently left uniform: the neck would stretch to 0.1 in the air. Task 1 test `VaryingSpacing_FlightKeepsSegmentLengths`.
4. Joint index <-> arc length (`FlowBody.UAtJoint`, `KitRender` tailStart, `CreatureLegs` span/pad, attachment `at(joint)`) assuming `spacing * k`. Task 1 test `VaryingSpacing_ArcAtJoint`.
5. A part that cannot honour varying spacing (octopus, mesh parts reading `spacing`) composed with it: Validate must refuse with a message. Task 1 test `VaryingSpacing_UnsupportedPartRefused`.

---

### Task 1: Per-joint spine spacing (shared, opt-in)

**Files:**
- Modify: `Scripts/Creatures/CreatureSpecies.cs` (field + helpers), `Scripts/Creatures/Kit/FlowBody.cs` (profile channel, BuildJoints/compile, UAtJoint, Validate), `Scripts/Creatures/Kit/CompiledSpecies.cs:347`, `Scripts/Creatures/CreatureSim.cs` (176, 387, 874, RestRun), `Scripts/Creatures/Flight/AirChain.cs`, `Scripts/Creatures/Flight/CreatureFlight.cs`, `Scripts/Creatures/Flight/CreatureWings.cs`, `Scripts/Creatures/CreatureLegs.cs`, `Scripts/Creatures/Kit/KitRender.cs`, `Scripts/Creatures/CreatureRestPose.cs`, and any other consumer on a FlowBody + Leg2Bone/DrakeLeg/DigitWing/Eyes species' path that the implementer finds reading `spacing` as a segment length.
- Test: `Tests/EditMode/CreatureSegmentSpacingTests.cs` (new)

**Interfaces:**
- Produces: `public float[] segmentLengths;` on `CreatureSpecies` (scale-1 metres, length `joints.Length - 1`; null or empty = uniform `spacing`).
  `public float SegmentLength(int i)` (segment between joint i and i+1, scale 1) and `public float ArcToJoint(int k)` (scale-1 arc from joint 0 to joint k) on `CreatureSpecies`; `public bool UniformSpacing` (true when segmentLengths is null/empty).
- Produces: FlowBody profile key channel `spacing` (metres; 0 = the body's `spacing`), interpolated by the profile's monotone cubic per segment midpoint; when every key is 0 nothing is emitted (segmentLengths stays empty). kityaml/`Vesper.py` writes it as `'spacing'` in `key()`.

- [ ] **Step 1: Write the failing tests** in `CreatureSegmentSpacingTests`:
  - `UniformSpecies_SegmentLengthsEmpty` — every shipped species asset compiles with empty `segmentLengths` (golden guard; plus run CreatureFlightGoldenTests and LegacyLegsGoldenTests unchanged).
  - `VaryingSpacing_Compiles` — a FlowBody with keys spacing 0.05 at t=0 and 0.1 at t=1: `segmentLengths[0]` ≈ 0.05 (±0.005), last ≈ 0.1, monotone, neighbour ratio ≤ 1.25.
  - `VaryingSpacing_ArcAtJoint` — `ArcToJoint(k)` equals the sum of segments; FlowBody `UAtJoint(k)` uses it; KitRender tailStart and attachment world positions sit on that arc.
  - `VaryingSpacing_SimKeepsSegmentLengths` — walk 10 s: every segment's world length within 2 % of `SegmentLength(i) * scale`.
  - `VaryingSpacing_RestMatchesStance` — the bound rest's segment lengths within 1 % and its joint heights within 2 % of the clearances.
  - `VaryingSpacing_FlightKeepsSegmentLengths` — launch, fly 10 s, land: segment lengths within 3 % throughout (air drape included).
  - `VaryingSpacing_UnsupportedPartRefused` — a varying FlowBody species composed with a part that only supports uniform spacing fails Validate with a message naming the part.
- [ ] **Step 2: Run** `python creature_kit.py test CreatureSegmentSpacingTests --tg <wt>` — expected: compile errors / FAIL.
- [ ] **Step 3: Implement** the field, helpers and channel; replace `sp.spacing` as segment length with `SegmentLength(i)` / `ArcToJoint(k)` at each consumer, keeping the literal old expression on the `UniformSpacing` path (bit-identity). `CreatureSim.RestRun(sp, k, spacing, f)` takes the segment's own length.
- [ ] **Step 4: Run** the new class, then one at a time: CreatureFlightGoldenTests, LegacyLegsGoldenTests, CreatureFlowBodyTests, CreatureVesperTests, CreatureCommandBrainTests, CreatureKitTests (`check Vesper` and `check Apex`) — expected all PASS (Vesper unchanged: its spacing is still uniform until Task 2). RED proof: revert one consumer (e.g. AirChain) and show `VaryingSpacing_FlightKeepsSegmentLengths` fails.
- [ ] **Step 5: Commit** `feat(creatures): opt-in per-joint spine spacing (FlowBody spacing channel -> CreatureSpecies.segmentLengths)`; `unity-compile` clean first.

### Task 2: Vesper's humpbacked build, long strides

**Files:**
- Modify: `Tools~/SpeciesGen/Vesper.py` → regenerate `Config/Creatures/Vesper.asset`; `Tests/EditMode/CreatureVesperTests.cs` (+ `CreatureCommandBrainTests.cs` / `CreatureVesperLabTests.cs` only if a constant must move, each with a stated reason); `Scripts/Creatures/VesperLabLayout.cs` only if the rock heights no longer suit the taller animal.
- Test: `Tests/EditMode/CreatureVesperTests.cs`

**Interfaces:**
- Consumes: Task 1's profile `spacing` channel, `CreatureSpecies.SegmentLength/ArcToJoint`.

- [ ] **Step 1: Write the failing tests** in `CreatureVesperTests` (scale-1 numbers × SCALE in assertions):
  - `Vesper_Profile_Humpbacked` — standing after 3 s on flat ground: the highest spine joint lies in the trunk between shoulder and hips; hips joint ≥ 0.75; shoulder joint ≥ 0.8; every neck/head joint within 0.08 of the shoulder's height (near flat) and below the hump; tail tip ≤ 0.15.
  - `Vesper_HeadNeck_CloserJoints` — head joints 0–3 segments ≈ 0.05, neck segments ≈ 0.06, trunk/tail 0.1 (±10 %); joint count head 4 / neck 7 unchanged; head+neck arc ≤ 0.65.
  - `Vesper_Tail_Long` — tail arc ≥ 2.0.
  - `Vesper_Knuckles_ForwardAndOut` — walking 10 s, each planted wrist on average ≥ 0.35 ahead of the shoulder joint along the heading and ≥ 0.3 to the side of the spine.
  - `Vesper_HindLeg_LongMetatarsus` — hock (ankle) height above the foot contact ≥ 0.27 while planted.
  - `Vesper_Strides_Longer` — mean stride length (planted-to-planted foot distance) of arms and legs each ≥ 1.8 × the current values (measure the current ones first and write them into the test comment).
- [ ] **Step 2: Run** `test CreatureVesperTests` — expected FAIL on the new tests.
- [ ] **Step 3: Retune `Vesper.py`** to the spec's table and heights: N = 38 (head 4, neck 7, trunk 6, tail 21); HEAD/neck/trunk/tail `spacing` keys 0.05/0.06/0.1/0.1 (smooth ramp); profile clearances tail tip ~0.08, hips 0.80, hump ~0.92 just behind the shoulders, shoulders 0.85, head ~0.88; DrakeLeg upper 0.28, lower 0.32, ankleHeight 0.30, attach/restOffset so the foot plants under the hip; Leg2Bone upper 0.25, lower ~0.8, restOffset ≈ (0.25, 0, +0.45), pole up and back; FINGER_FOLD / groundLiftDeg rescanned so `Vesper_FoldedWingsStaySeparate` holds (record the scan in the comment as the existing one does); stepThreshold/stepDuration/stepLift raised on both limbs for the stride test; SHOULDER/HIPS/TAIL_ROOT/membrane joints/eye joint re-indexed. Regenerate the asset.
- [ ] **Step 4: Run** one class at a time: CreatureVesperTests, CreatureCommandBrainTests, CreatureVesperLabTests, CreatureDigitWingTests, CreatureSegmentSpacingTests; `check Vesper` (kit checks: Layout, Gait, Size, Gc, Perf, Lab, Wander). Fix by retuning Vesper.py or flight constants (each with a reason); a shared-code change needs an opt-in flag. All PASS (Mono-margin note: keep ≥ 20 % margin on thresholds).
- [ ] **Step 5: Commit** `feat(vesper): humpbacked build - high hips, hump, flat neck, closer head/neck joints, long tail, long metatarsus, knuckles forward, longer strides`; then write the look checklist for the user into the task report (what to watch in VesperLab: profile from the side, knuckles ahead of the chest, strides, folded finger blades, flight bob).
