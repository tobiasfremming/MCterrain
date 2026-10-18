# Climbing (merged on `feat/creatures`, 9607482)

Spec: `docs/superpowers/specs/2026-10-17-creature-climbing-design.md` (user
decisions at the end). Reports: ledger folder `climb-report.md`.

## Binding user constraints

- Feet and body touch the object's **real render geometry**: a plant's LOD0 bark
  submesh at the instance TRS, via pooled MeshColliders. **No capsules, SDFs,
  fitted cylinders or proxy shapes** (FloraObstacles capsules are excluded too).
- Generic: anything with real colliders in the user's SpaceGame is climbable with no
  per-object authoring (`PhysicsScene` + `LayerMask`).
- Steep **terrain** is climbable too (dug walls, cliffs), through the same tilted-up path.
- Climbable plants = species with `obstacleRadius > 0`, bark submesh only.
- The monitor stays at scale 4; the lab Baobab `plantScale` is 2.0.

## The climb rules (from the Editor phase, R30, R31)

1. **Terrain only as a wall**: under a joint steeper than 50° (`kTerrainWallDeg`;
   dunes stay below ~35°) **and** a relief ≥ ½ body length (`kReliefBodies`). Smaller
   relief (a 2 m pit under a 6.5 m monitor) is walked exactly as R25 tuned it. The
   wall check is one stateless field sample; the gate reads the cache through the
   read-only `CachedGroundProbe.Peek` (probing for the gate shifted later answers).
2. **Max surface angle 140°** from gravity's up (`ClimbSpec.MaxSurfaceAngle`): a
   bulbous trunk base (Baobab faces 103–137°) is climbed, a branch or slab underside
   (150–180°) is not; past it the creature is `Blocked` and brakes.
3. **Goals only on closed bark.** The Baobab trunk is an **open tube** at its foot;
   monitors walked into the hollow. Goals are rejected where the trunk's foot is not
   closed. A descent can still blunder into it (open item).
4. **Real-mesh contact only.** `PhysicsSurfaceProbe` casts with back faces on: a
   front face is the answer; a back face means "inside" and the answer is the exit
   above (never drop through a branch, never lift onto one from below). Normals are
   the mesh's interpolated vertex normals.
5. **Pitch limiter and climbing gait only while climbing.** Walking is bit-identical
   to the pre-climbing code (hash tests); the limiter on the walking path caused the
   R30 regression (385 flips in an overhang pit).
6. **Switch off on level ground**: every joint's up within 0.5° of gravity for 1.5 s.
   The anticipation fan and 25–50° dune faces once kept it on forever.
7. Trunk keep-out (R28) and joint-range braking are **off while climbing**: both
   stalled or folded the body at transitions. Joint ranges still trigger steps.

## Pieces

| file | role |
|---|---|
| `SurfaceProbes.cs` | `SurfaceHit` (`source` 0 = terrain, `NoSource`), `ISurfaceProbe : IGroundProbe` (Probe with a per-query `slot`, Cast, AnySurfaceNear), `CompositeSurfaceProbe` (terrain + surfaces, nearest wins, 2 % tie band, source hysteresis), `SurfaceMath` |
| `PhysicsSurfaceProbe.cs` | ray probe on a PhysicsScene + mask; per-slot triangle cache (Möller–Trumbore, re-checked every 16 uses or on registry change), `Backfaces()` scope |
| `SurfaceMeshCache.cs` | `Get(mesh)`, `BarkOnly(lod0)` (LOD0 vertices/normals, submesh 0 tris); one `Physics.BakeMesh` per source mesh |
| `CreatureSurfaces.cs` | registry: `CreateLocal` (local physics scene in play mode, MarchingCubes), `ForScene(scene, mask, bounded)` (SpaceGame, edit-mode tests), proxies, `Version`, `FindClimbables`, `Current` |
| `ClimbableFlora.cs` | every 0.25 s pools bark colliders for `PlantScatter.GetClimbables` near climbers; ≤ 1 cook per frame. Pool is 0 in CreatureLab (no PlantScatter there) |
| `CreatureSurfaceMesh.cs` | component making any render-only object climbable with its own mesh |
| `EnclosurePlant.cs` | lab trees register their LOD0 bark |
| `CreatureClimb.cs` | up field, head trail, anticipation fan, Blocked, steepness factors, pitch limiter, terrain-wall gate |
| `ClimbingBrain.cs` | Wander → Approach (p 0.35 after a pause) → Climb → Rest 4–10 s → Descend head-first → Wander; stuck 4 s → descend; Blocked → re-pick; height cap |

`CreatureWorld`: `groundSource {Auto, Physics}`, `surfaceMask`, a composite ground
per climbing species, `queriesHitBackfaces` on around `TickAll` (main thread only),
ClimbableFlora added automatically, registry created in `Awake`.

## The up field (per joint, `CreatureSim.Up[]`)

Per-joint surface normal, Gaussian-smoothed along the chain (`upSmoothJoints`), climb
weight `w = smoothstep(25°, 50°)` of its angle to gravity, target `slerp(g, n, w)`,
rate-limited by `upRateDeg / TimeScale`. A **head trail** makes each joint follow
the up the head had at that arc length (without it the body never turned onto the
wall). Anticipation is a 4-cast proximity-weighted fan (a single forward cast rocked
the head every frame). The heading is parallel-transported, not projected. Frame up
= `slerp(GroundNormals, Up, w)`; `upAt` stays gravity's up. Other state:
`ClimbWeight[]`, `Source[]`, `Blocked`, `ClimbAllowed` (false while wandering:
plants are walked around, terrain walls still climbed), `Steepness(j)`.

Climbing frames are only near-orthonormal after the slerps; `CreatureSim.Basis`
renormalises the quaternion when it drifts (see `gotchas.md`).

## ClimbSpec (`species.climb`, all 0 = default)

| field | default | note |
|---|---|---|
| `canClimb` | false | DesertMonitor true |
| `maxSurfaceAngleDeg` | 140 | the design said 100 |
| `maxHeightBodyLengths` | 1.5 | lab caps further at 0.45 × plant height |
| `speedFactor` / `descentSpeedFactor` | 0.5 / 0.4 | on vertical surfaces |
| `clearanceFactor`, `strideFactor`, `stepTimeFactor`, `liftFactor` | 0.65, 0.6, 1.2, 0.6 | lerped by steepness smoothstep(30°, 80°) |
| `upRateDeg` | 270 | Froude-scaled |
| `upSmoothJoints` | 3 | |
| `pitchLimitDeg` | 25 | the limiter holds the body to 30–33°; tests assert 3D ≤ 45°, pitch ≤ limit + 8° |
| `minWidthFactor` | 1.5 | goal needs a surface this many body widths across |

Grip rule at steepness > 0.5: a step starts only if ≥ 1 foot per girdle and ≥ half of
all feet stay planted. A rest probe miss on a cylinder casts toward the attach point
(feet hug the trunk).

## Perf (Editor, DesertWorld)

| | ms |
|---|---|
| 100 walking monitors, plain cache | 3.98–3.99 (at the R23 bound) |
| same on the climbing ground, nothing near | 4.21–4.37 (test bound 1.15× plain) |
| 1 monitor climbing the real Baobab | median 0.173, p90 0.209 (was 0.62 before the fast paths) |
| per climbing frame | 16 raycasts, 32 surface probes, 64–69 % triangle-cache hits, 21 field samples |

## Tests

`CreatureClimbTests` (25), `TerrainGen.Tests.Perf.CreatureClimbPerfTests`
(`Perf_Walking100_Unchanged`, `Perf_ClimbingMonitor`), plus
`Hole_Overhanging_ClimbingGround_*` / `Hole_Bowl_ClimbingGround_*` (R25 bounds through
the composite), `Climb_TerrainCliff_UpAndOver`, `Walking_SteepDunes_BitIdentical`.

## Open

Low rest reads as a curl; flat-shaded low-poly bark; open-tube trunk feet; other
L-system bark may need the same closed-foot check; R23 headroom.
