# Winged serpent: design

Status: design, 2026-10-17. Builds on the creature module spec, climbing (ISurfaceProbe, per-joint Up) and the tree octopus (part ids 4–6, CreatureInstance growth). Branch: submodule `feat/creature-wyvern`. Prototype: session scratchpad `wyvern_proto/` (proto.py, measure.py).

User brief: "a snakelike winged lizard. no forearms, because of wings of course, and it uses the same principle as the feet on the lizard for flying, only that the comfort zone is vertical. When the wing flaps downwards, the shoulders go up, and the chain follows."

## 1. A wingbeat is a step

| Leg (CreatureLegs) | Wing (CreatureWings) |
|---|---|
| foot = end of the 2-bone chain | wrist = end of humerus + forearm; fingers hang off it |
| rest point projected to ground | `restTip` in the girdle frame (spread, small dihedral), not projected |
| comfort disc `stepThreshold` | vertical comfort band `[rest − comfortDown, rest + comfortUp]` along girdle up |
| stance: foot planted, body moves over it | downstroke: wrist "planted" in air, driven down → shoulder rises |
| step trigger: foot leaves zone behind | wrist leaves the band at the bottom |
| swing to rest + overshoot | upstroke to band top + `overshootUp`, part-folded, feathered |
| gait groups alternate | both wings in one group → synchronous beats |
| Froude timing √scale | beat period × √scale (2.6 Hz at scale 1, 1.3 Hz at 4) |

Air plant (per wing, per sub-step h, implicit, mass-independent): κ = kGrip·A(fold, feather)·max(|v|, vGripMin); g = κh/(1+κh); v ← v − g·((v + ṙ_wrist)·n)·n. g = 1 is a planted foot (shoulder rises exactly by the stroke); g < 1 slips. Plus gravity, parasitic drag, glide lift, induced drag.
Prototype: level flight holds altitude ±0.07 m at 4.9 m/s, 2.6 Hz; girdle bob 11 cm p-p, mid-body 6 cm (lags ~½ beat), tail 3 cm; climb demand → bigger/faster strokes; glide emerges with grip ×2; chain lengths exact, bends ≤ 1.9°.

## 2. Anatomy and data

32 joints at 0.08 m (≈2.8 m at scale 1), slim snake build, monitor head with crest; girdle at joint 5, small hips at 14, long tail (optional vane). No forelegs: the wing arm is a `LegSpec` on the ground and driven by `WingSpec` in the air. 3 finger bones (wyvern), membrane finger 1 → 3 → flank joints 5–11. Small hind legs for landing/perching/walking.
New data (additive; null/0 = none): `WingSpec` (leg index, restTip, comfortUp/Down, strokePlaneDeg, pronationDeg, overshootUp, upstrokeDuration, upstrokeFold, finger lengths/spreads, fingerMinGapDeg, membrane joints, area, scallop), `FlightSpec` (speeds, kGrip, vGripMin, kLift, kDrag, maxBankDeg, rollGain, alphas, launchSpeed, flareDistance, air undulation, tailSag, headStabilise, minAltitude, cruiseAltitudeFrac), look: membrane colour, translucency, vein contrast.
Bones: Joint + 3·Leg + 6·Wing + 2 = 58 (3.7 KB). EyeBone moves only when WingCount > 0 (monitor layout bit-identical).

## 3. Simulation

Modes: Ground → Launch → Air ⇄ Glide → Flare → Touchdown → Ground/Perched; per-joint airWeight blends the ground path (today's code) with the air path, then RestoreLengths.
FlightModel (pure): girdle point with v, heading, bank, AoA; controller from climb and thrust demand → stroke amplitude, downstroke rate, pronation; glide when demand < 0.05. Banking via left/right amplitude asymmetry (roll torque, dihedral damping); coordinated turns ψ̇ = g·tanφ/v.
CreatureWings: LegState-shaped; stance drives the wrist down the stroke plane; upstroke Bezier through restTip; TwoBoneIK; fingers fold/spread with an order invariant; 3 membrane ribs slerped between finger 3 and the flank, scaled along their axis (normals stay exact).
Air chain: 3D pull chain from the girdle back (3D bend cone, exact lengths, tail sag, flying-snake air undulation); neck two-anchor FABRIK to a low-passed head target (head stabilised); banked up parallel-transported into climbing's Up[].
Ground: wings folded; wing-walk (wrists as front feet) with CreatureLegs unchanged. Legs tucked in air.
Launch (~0.45 s × timeScale): crouch, vault, first upstroke + downstroke, airWeight ramps head→tail. Landing: glide slope to flareDistance, flare (high AoA, braking strokes), hind feet reach probed points, touchdown eases, wings fold. Perch drape: unsupported joints hang (tail over a branch).

## 4. Brain (FlightBrain)

Perched (4–15 s) → optional ground wander → Launch → Climb to 0.4–0.8 maxHeight → Patrol (3D waypoints) or Soar (glide circles that fit the safe disc, a few beats when low) → ChoosePerch (rock tops via ground probes; branch tops via ISurfaceProbe.Cast, n·up > 0.7, room checked) → Approach → Flare → Touchdown. Forward Cast every 0.1 s for avoidance.

## 5. Containment

Aviary cylinder (enclosure radius + maxHeight + minAltitude); girdle clamped, chain trails inside; soft turn-back by turn radius; spawn check cruise ≤ √(g·tan(maxBank)·R/2); altitude probe each sub-step.

## 6. Mesh and rendering

Body/legs by the existing builder; finger tubes + thumb claw; double-sided membrane (part id 7), 4 zones × 6×8 grid (~1k verts/wing), 2-ray skinning (≤ 40° apart → scallop, no collapse), trailing-edge scallop. Bind pose = spread glide pose. ~9k verts, one instanced draw, membrane casts shadows. Shader: back-lit transmission tinted by membrane colour, veins, darker trailing rim (~10 ALU, membrane pixels only). Look: dusky olive-bronze dorsal with bands, cream belly, warm ochre translucent membrane. Bounds include span and finger tips.

## 7. Performance

Air ≤ 0.05 ms per flyer (est. 0.02–0.03), ground ≤ 0.06 ms, 20 flyers ≤ 1 ms, 0 GC (positive control), build < 5 ms.

## 8. Tests

Phase A (pure): Flight_PlantedTip_LiftsShoulder, Flight_GripFraction, Flight_HoldsAltitude, Flight_ClimbDemand_RaisesRateAndAmplitude, Flight_Glide_NoStrokes, Flight_BankTurn_Coordinated, Flight_Froude, Wing_StepAtBandBottom, Wing_WristInBand, Wing_Synchronous, Wing_FingerOrder_NoInversion, AirChain_LengthsExact, AirChain_BendCone3D, AirChain_FollowsShoulderBob, AirChain_HeadStabilised, Mesh_Serpent_Builds, Mesh_WingSweep_NoInvertedTris, Mesh_MembraneNormals_ScaledRibs, Bones_Layout_MonitorUnchanged.
Phase B: Mode_NoWings_BitIdentical, Launch_FromGround_Airborne, Land_Flat_FeetPlanted, Land_RockTop, Land_Branch_RealMesh, Perch_Drape_TailHangs, FlyingBrain_Cycles_120s, Containment_Aviary_120s, Containment_TurnRadiusFits, Renderer_Bounds_ContainWings, Perf_FlyerAir/Ground/20Flyers, Flyer_NoAlloc, shader checks.

## 9. Editor verification

Side view mid-downstroke vs top of upstroke (shoulders, tail wave), banked turn from front, glide circle from below (back-lit membrane), launch, flare + touchdown, perched on rock/Baobab, wing-walking, F3 (comfort bands, wrist anchors, forces, airWeight). Read back ms per mode, beat Hz, altitude, bounds. Full suite.

## 10. Phases

[A now, new files only] 1. FlightModel + CreatureWings + tests; 2. AirChain + tests; 3. WingSpec/FlightSpec, bone layout, asset, mesh builder, Mesh_* tests, static screenshots.
[A after octopus shader] 4. Membrane part in the creature shader.
[B after climbing] 5. CreatureSim modes + airWeight + leg tuck/hand-off, launch/land; 6. FlightBrain + aviary + containment; 7. perching/drape on real geometry; 8. perf + look + Editor verification.

## 11. Risks

Coupled controller tuning; no hover (tail swings forward at low speed); air↔ground pops; folded membrane z-fight; shared-file churn with climbing/octopus; aviary needs radius ≥ 12–14 m; Mono cost unmeasured; bob amplitude is a taste call.

## 12. User decisions

User decisions, 2026-10-17 (all recommended defaults):
1. Ground gait: wing-walk (wrists with thumb claws as front feet, wings folded) + small hind legs; CreatureLegs as-is.
2. Wing: 3-finger wyvern membrane to the flank.
3. Bob: stylised and visible (~10 cm p-p at scale 1, readable tail wave).
4. New aviary enclosure, radius 14 m × height 10 m with trees and rock perches; serpent at scale 1.
