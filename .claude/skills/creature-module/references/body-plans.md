# Body plans and in-progress creatures

**Everything in this file is IN PROGRESS on its own branch, not on `feat/creatures`.**
Status as of 2026-10-18. Before calling an API named here, check the branch
(`git -C Assets/TerrainGen show <branch>:<path>`) and the ledger tail
(`.superpowers/sdd/2026-10-16-creature-module/progress.md`); the agents may have moved on.

| feature | branch | where | state |
|---|---|---|---|
| tree octopus + ICreatureBody + cloak | `feat/creature-octopus` | main tree `Assets/TerrainGen` | Editor phase: jitter + cloak flicker + 4× size; WIP uncommitted |
| winged serpent | `feat/creature-wyvern` | `unity_stuff/wt/wyvern/Assets/TerrainGen` | offline Phase A + B done, Editor queued after octopus |
| arthropod legs + spiders | `feat/creature-legs` | `unity_stuff/wt/legs/Assets/TerrainGen` | offline P0–P2 done, Editor queued after wyvern |

When designing something new, reuse these seams instead of inventing parallel ones:
`ISurfaceProbe` for any contact, `ICreatureBody` for any non-spine body,
`EnclosureArea` for containment, `LegBoneLayout` for bone indices, data in
`CreatureSpecies`, the part-id registry (`new-species.md`).

## ICreatureBody (octopus branch)

```csharp
public interface ICreatureBody {
    CreatureSpecies Species { get; }  float SizeScale { get; }
    void WriteBoneWorld(Matrix4x4[] dst, int offset);
    void EncapsulateBounds(ref Vector3 lo, ref Vector3 hi);   // renderer adds reach × SizeScale
    void Tick(float dt);              // self-ticking bodies (octopus); spine sims are ticked by the world
    bool DynamicLook { get; }         // true: instance buffer re-uploaded each frame
    void UpdateLook(ref CreatureInstance inst);
}
```

- `SpineBody` adapts a `CreatureSim` (the sim is untouched). Its bounds are the
  joints + feet; with arthropod legs it must also include the knees (`LegPoints`).
- `CreatureRenderer` draws any plan; the spine path is bit-identical (a test compares).
- `CreatureWorld.AddBody/RemoveBody/Bodies`, `SpawnOctopus`, `octopusMaterial`.
- `CreatureInstance` grows 16 → **32 B** (cloak, chroma, flash, cloudPhase), for all
  species. `Instance_StructIs*Bytes` pins C#/HLSL parity.
- `CreatureSpecies.bodyPlan {Spine, Cephalopod}` + `cephalopod` (CephalopodSpec).

## Tree octopus (`feat/creature-octopus`)

Spec `2026-10-17-tree-octopus-design.md`; reports `octopus-a-report.md`, `octopus-b-report.md`.

User decisions: contact only via `ISurfaceProbe` on real geometry (the L-system
skeleton, `BranchHints`, is for **perception and planning only**, confirmed by a
probe); each arm is an independent chain with its own state machine; the body is a
squishy soft body driven by the chains (**visibly** squishy: stretch 12–20 %,
visible jiggle, tests pin min AND max); prey = player + a small lab creature, hold
1.5 s, no damage; a grove of overlapping trees; **4× the earlier lab size via
`TreeOctopus.scale`** with per-individual variation (0.9/1.1 test); the octopus
assigns **arm roles** (Grip on route, Feel, Hang, Groom, Strike, Hold, Tuck) with
hysteresis and the arms execute them; it **wants to swing** between branches
(brachiation as preferred locomotion and idle). Roles + swinging have a plan at
`docs/superpowers/plans/2026-10-18-octopus-arm-roles-swinging.md` (T0–T12: an
`ArmCoordinator` with role hysteresis, agent executors incl. Groom, an OnGUI role
readout, `SwingPhase`, grip groups + apex release, pumping, swing routes, idle play;
no ballistic flight). It starts after the jitter/cloak/4× fixes.

Pieces (`Scripts/Creatures/Octopus/`): `TentacleChain` (24 particles, Verlet +
XPBD-lite, stretch [0.85, 1.35], 28° bend cone, tethers, twist ≤ 20°/segment),
`SoftLattice` + `OctopusBody` (14-particle shape matching over 5 clusters, det-1
volume, hull volume constraint, whole-body sleep), `TentacleAgent` (Feel → Reach →
Grip → Anchored → Release; Strike, Hold) + `ArmBlackboard` (support margin: 2
anchors hanging, 1 on a surface), `WrapMarch` (helix snapped to real bark; spread on
thick trunks), `BranchHints`/`PlantSkeletons`, `OctopusBrain` (rest, explore, stalk,
ambush, strike, hold, retreat, fallen), `OctopusPreyAdapters`, `OctopusController`
(query budget 40/frame, contact planes, distance LOD), `OctopusCreature`
(ICreatureBody), `OctopusLab`, `OctopusMeshBuilder` (201 bones; web uses 4-bone
skinning via uv3), `CreatureOctopus.shader` (wet skin, chromatophores, suckers;
`CREATURE_FOUR_BONES` + cofactor normals only under that define, so the monitor's
skin path is unchanged).

Known problems the Editor agent is fixing (user-reported 2026-10-18): constant jitter
from lapsing contact planes (~40 mm sink and spring back), cloak flicker (needs
hysteresis, minimum hold, rate-limited ramp), Mono active cost 1.1–1.8 ms (≈ 4× the
0.35 ms budget), resting body never sleeps, too small in the oak foliage.

Engine finding: the Editor's `UnityEngine.CoreModule.dll` is built with optimisations
disabled, so every `Vector3`/`Quaternion`/`Mathf` operator is a real call. Hot loops
use scalar floats and `System.MathF` (body tick 1.32 → 0.13 ms in .NET).

## The cloak (generic, ships with the octopus)

The user loved the accidental shader-cache bug: body gone, shadow and SSAO remain.
`CreatureCloak.hlsl` dissolves by per-instance `cloak` in the Forward pass(es) only;
ShadowCaster, DepthOnly and DepthNormals ignore it. Trigger from the brain. The
monitor's threat trigger is a later small task; a shimmer variant is deferred.

## Winged serpent (`feat/creature-wyvern`)

Spec `2026-10-17-winged-serpent-design.md`; report `wyvern-a-report.md`. A snake-like
wyvern, **no forearms**: the wing arm is a legacy `LegSpec` on the ground and is
driven by `WingSpec` in the air. **A wingbeat is a step** with a *vertical* comfort
band: the downstroke is the stance (wrist "planted" in air, shoulder rises, the chain
follows), the band bottom triggers the upstroke, both wings in one gait group.
User decisions: wing-walk + small hind legs, 3-finger membrane to the flank,
visible bob (~10 cm p-p), aviary 14 m × 10 m, scale 1.

- Data: `wings[]` (WingSpec), `flight` (FlightSpec), look `membrane*`.
  `WingBoneLayout`: spine, legs, 6 per wing (3 fingers + 3 ribs), then eyes; identical
  to the plain layout without wings. **Must call `LegBoneLayout`** after the legs merge.
- Flight modes (`Flight/CreatureFlight.cs`): Ground → Launch → Air ⇄ Glide → Flare →
  Touchdown → Ground/Perched, plus Drape (unsupported joints hang). `CreatureSim.SubStep`
  branches early into flight; the old body is `GroundSubStep`, unchanged (walking
  hashes identical). Hooks `BeforeLegs`, `Drape`; `Supported[]`, `ResetGround`,
  `CreatureLegs.Replant()`.
- `FlightModel` (implicit air plant, Froude-scaled, PD + integral altitude), `AirChain`
  (3D pull chain, neck along a Bézier: FABRIK zigzagged), `CreatureWings`
  (`PoseOnArm` for wing-walk), `FlightBrain` (Rest, Wander, Face, Patrol, Soar,
  Landing; predictive wall turn-back), `AviaryDressing`, `WingedMeshBuilder`
  (membrane part 8, 0 flips over 712,800 poses), `CreatureMembrane.hlsl`.
- Measured offline: 2.67 Hz, 4.89 m/s, altitude 5.00 m for a 5 m goal, bob
  0.111/0.063/0.028 m; air tick ~4 µs (.NET). Risks: shader uncompiled, perch
  touchdown slide ≤ 1.5 m, narrow-branch turns, half-fold look.

## Arthropod legs (`feat/creature-legs`)

Spec `2026-10-17-multi-segment-legs-spider-design.md`. Data and tuning are in
`new-species.md` ("Arthropod legs"). Code: `LegSegment.cs`, `ArthropodLegIK.cs`
(synergy IK), `ArthropodLegMesh.cs` (rigid capsule segments, knuckle bulbs, one bone
per vertex, band part 9), `LegBoneLayout` in `CreatureSpecies.cs` (`LegBones`,
`LegStart`; `sp.LegBone(leg, part)`, `sp.EyeBone(e)`), integration in
`CreatureLegs`/`CreatureSim`/`CreatureMeshBuilder`/DebugView/renderer bounds, a velvet
sheen lobe in the shader. Tests: `ArthropodIKTests`, `CreatureSpiderTests`,
`LegacyLegsGoldenTests` (goldens captured in the harness; the Unity constants need one
Editor run because Mono's `Mathf` differs). Perf ~18–19 µs per spider (.NET); bounds
`Perf_OneSpider ≤ 0.1 ms`, `20 spiders ≤ 2 ms`.

## Merge notes between these branches

- Shared files: `CreatureSpecies.cs`, `Creature.shader`, `CreatureLook`,
  `CreatureRenderer.cs`, `CreatureSim.cs`, `CreatureLab.cs`: keep every edit additive
  and expect textual conflicts (octopus vs legs on shader/look).
- After each merge into `feat/creatures`, rebase the others (`git rebase --onto`) and
  re-run the walking golden/hash tests.
- Fixes on `feat/creatures` (e.g. the quaternion renormalise 4637176) reach the
  branches by cherry-pick or rebase; audit the branch's own TRS calls too.
