# Multi-segment legs, daddy-longlegs spider, tarantula, beetle legs redone: design

Status: design, 2026-10-17. Prototype: session scratchpad `spider_design/synergy_ik.py`, `leg_swing.png` (side views of five swing frames: pholcid leg I, tarantula leg IV, beetle leg II).

## 0. Why

The DesertBeetle reuses the lizard's two soft tubes + pole: no segments, no visible joints, lizard foot pads. The data cannot express coxa → femur → tibia → tarsus.

## 1. Goals / anti-goals

Goals: N segments per leg as data (2 legacy up to 7); per-joint hinge, limits, rest bend; arthropod silhouette (steep femur to a high knee, tibia/metatarsus arc down, tarsus flat); knee-lifting steps; a pholcid (daddy-longlegs-like) spider, a tarantula, the beetle redone as an insect; one data model for hair-thin 13× legs and thick ~1.1× legs, no per-species code; zero GC, deterministic, main thread.
Anti-goals: the lizard path changes by not a single bit (golden test); no physics joints/clips; no per-species branches; no leg-leg collision solver (yaw sectors in data prevent crossing); no webs; no whirling defence yet.

## 2. Data model: LegSpec v2 (backward compatible)

`LegSpec.segments` (LegSegment[]): null/empty = legacy 2-bone limb, unchanged. LegSegment: length, radiusStart/End, restBendDeg, min/maxBendDeg, flexWeight κ (reach synergy), liftWeight σ (swing knee-lift synergy), axisTiltDeg, knuckle, bandStart/End, bristles.
Per leg: contactAngleDeg, kneeLiftDeg, elevMin/MaxDeg, kneeJoint, feeler (pedipalp: posed, never plants, out of gait/throttle/grip/sway), liftDelay (metachronal stagger). Existing fields reinterpreted: forward/backSwingLimitDeg = coxa yaw limits (R16); kneeRangeDeg/kneeFlexDeg = s range; restOffset, shoulderOffset, stepThreshold, stepDuration, stepLift, overshoot, gaitGroup unchanged. Helpers IsArthropod, TotalLength, SegmentCount.
Species: gaitBob {amplitude, hz, damping}; eyeCluster[]; appendages[] (chelicerae/fangs, mesh only). Look: bandColor, sheen, sheenColor, bristleColor.
Bones: LegBone(l,k) = JointCount + legStart[l] + k (prefix sum; legacy = 3l + k), one static LegBoneLayout (wyvern's WingBoneLayout must call it).
Validate: ≥ 3 segments, lengths > 0, min ≤ rest ≤ max, some κ ≠ 0, monotone reach run contains rest ± stepThreshold, feelers out of gait checks, wings may not use arthropod legs.

## 3. IK: synergy ("shape template") IK

Rejected: FABRIK with hinge projection (jitter/flip near limits, history-dependent, drifts off the shape), CCD (distal-first curl, many sweeps), damped least squares (needs a null-space shape term, 5–10 iterations, too costly on Mono), sampled pose space (misses the target, feet slide).
Chosen: joint bends b_i(s, β) = rest_i + s·κ_i + β·σ_i. s solved for reach (safeguarded Newton in a bracket, ≈3 iterations; de/ds from one FK pass), β driven by the swing (knee lift), yaw and pitch closed-form, tarsus placed at the contact angle. Stateless → deterministic, no popping; the authored silhouette holds at every reach; limits = one interval on s. Stability: reach r(s) strictly monotone on the usable s interval (limits ∩ knee range ∩ monotone run, checked at β = 0 and β = kneeLift on a 256-sample grid).
Prototype: reach error ≤ 1.2e-7 m, 0 limit violations, 0 flips, bit-equal after a different history, ≈3 Newton iterations, for pholcid I, tarantula IV and beetle II. An unclipped non-monotone run flipped (0.56 m joint jump), which is why the run is clipped.
Integration: per-leg branch on IsArthropod in SolveIK; legacy calls TwoBoneIK as today. JointAngles → swing = |yaw|, knee = |s| (R12 triggers/throttle unchanged). reachLen/minReach per leg (legacy: identical expression). Climbing seams (Up(l), FootProbe, GripHolds, footSource) unchanged. LegState unchanged; joint points in a flat LegPoints array.

## 4. Stepping and gait

Alternating tetrapods (L1 R2 L3 R4 / R1 L2 R3 L4) through the existing scheduler; liftDelay staggers legs rear-to-front within a group. Comfort zone as fractions of reachLen (rest ≈0.65 radial, threshold ≈0.25, overshoot ≈0.12), non-overlapping coxa yaw sectors. Knee-high swing: small foot lift, β = kneeLift·sin(πt) raises the femur (knee +15–20 % of femur). Suspended body with a gaitBob spring kicked at each group lift-off (pholcid 1.8 Hz ζ 0.25 bouncy; tarantula 1.2 Hz ζ 0.7 heavy). Feelers tap slowly, never probed.

## 5. Mesh and skinning

Rigid capsule segments, one bone per vertex (coxa root ring blends with the attach joint); joint bulbs (knuckle ≥ 1.15 × adjacent radius) cover sockets at all bends → no MaxBend inversions by construction. legSides per species (pholcid 5, beetle 8, tarantula 10). Knee bands with duplicated edge rings (one part id per triangle; part 4 BAND). Tarsus claws (no lizard pad). Tarantula bristles: ~2 500 mesh tri-pyramids (~10k verts), part 5 BRISTLE, plus a velvet sheen lobe in CreatureLighting; shells and fins rejected. Body from the existing spine profile (cephalothorax, pedicel, abdomen); eye clusters and chelicerae from data.
Bones: pholcid 71, tarantula 76 (monitor 40).

## 6. Species (scale 1)

DaddyLongLegs (pholcid): 4-joint body ≈0.09 m; 8 legs × 7 segments, I 1.19 / II 0.95 / III 0.72 / IV 0.92 m (≈2.4 m span), radii 6 → 1.5 mm, dark knee bands; 4-segment palps; 8 eyes; pale translucent beige-grey; speed 0.5, stepDuration 0.32, liftDelay 0.12, kneeLift 20°, bob 1.8 Hz / ζ 0.25.
Tarantula: 6-joint body ≈0.38 m (cephalothorax 0.16, abdomen 0.2); legs 0.36–0.45 m × 7 segments, radii 22 → 9 mm (span ≈2.3× body); 6-segment palps; chelicerae + curved fangs; ocular tubercle; near-black velvet, bristles, optional orange bands; speed 0.15, stepDuration 0.45, liftDelay 0.18, kneeLift 10°, sway 10° / roll 6°, bob 1.2 Hz / ζ 0.7.
DesertBeetle v2: legs only — coxa 0.02, femur 0.095, tibia 0.11, tarsus 0.06 (tarsomere beads + 2 claws), contact 30°, kneeLift 12°.

## 7. Tests

Guards: LegacyLegs_BitIdentical_Golden (FNV-1a over bone matrices for 600 ticks + mesh hash: DesertMonitor, TestHexapod, Lizardish, DesertSnake; captured before any change), BoneLayout_PrefixSums, legacy JointAngles parity, beetle tests use TotalLength.
IK: Reach_Exact, Unreachable_ClampsAlongDirection, Joints_WithinLimits, NoFlip_ContinuousPath, Stateless_Deterministic, MonotoneRun_RejectsBadTemplate, Pholcid_KneePeak, TarsusContact_OnSlope, Solve_NoAlloc.
Spider: IsAsAuthored, TetrapodGait_NeverOverlaps, EveryLegSteps, FeetPlanted_DoNotMove, SwingLiftsKnee, BodyBobs, AdjacentLegsNeverCross, PalpsNeverPlant, TightTurn_JointRangesStayBounded, BuildsAndWanders_Contained, MaxBend_NoInvertedTriangles, ArthropodMesh_OneBonePerVertex, _SinglePartPerTriangle, _BulbCoversJoint_AtLimits, Renderer_Bounds_ContainEverySkinnedVertex.
Tarantula: IsAsAuthored, TetrapodGait, FeetPlanted, SlowCruise, HeavySway, PalpsNeverPlant, Contained, MaxBend, BristleBudget.
Beetle: all existing DesertBeetle_* + DesertBeetle_InsectLegs.
Perf: Perf_OneSpider_Under0_1ms (est. 0.06–0.08 ms), Perf_20Spiders_Under2ms, Perf_100Lizards unchanged (A/B same session).

## 8. Editor verification

Pholcid: side (knee peaks), top-down mid-step, close-up (bands, bulbs, eyes, palps), dune slope, by the Baobab, 4-frame knee-lift strip, 10 m / 20 m aliasing check. Tarantula: side, close-up (fangs, palps, bristles, sheen), top-down, slope. Beetle: before/after at the species-beetle-* viewpoints. Two new lab enclosures.

## 9. Phases and merge risks

P0 (offline now): golden hashes captured in a pure-C# harness. P1 (offline now, worktree wt/legs from feat/creature-climbing): LegSegment, ArthropodLegIK, ArthropodLegMesh, ArthropodIKTests. P2 (after climbing lands): integration into LegSpec/Validate, LegBoneLayout, CreatureLegs, CreatureSim, MeshBuilder, DebugView, MaxLateralReach; golden green. P3 (Editor): assets, shader part ids + sheen, lab enclosures, shots. P4 (later): climbing spiders, whirling defence, thin-leg minimum pixel width.
Merge risks: climbing edits the same CreatureLegs methods (P2 starts from climbing's final commit); wyvern's WingBoneLayout hard-codes 3·legs and wings stay legacy (Validate); octopus SpineBody bounds must include LegPoints; shader part ids and uv3 skinning go after the octopus merge.

## 10. Risks

2-D synergy family (uneven ground under one leg → extra steps, not slides); κ authoring is unintuitive (Validate + prototype tuning aid + cookbook defaults); hair-thin legs alias at distance (P4 min pixel width); tight-turn crossing (test + data); MaxLateralReach shrinks the pholcid safe disc; bristle triangles in shadow/depth passes (budget test; fallback sheen only).

## 11. User decisions

User decisions, 2026-10-17:
1. Daddy longlegs: giant, scale 1 (9 cm body, ~2.4 m span).
2. Tarantula hair: SHEEN ONLY (no mesh bristles; drop the bristle part id, BristleBudget test and bristle data).
3. Tarantula palette: near-black velvet with muted orange knee bands (red-knee look).
4. Spiders climb as a follow-up after this work, not in it.
