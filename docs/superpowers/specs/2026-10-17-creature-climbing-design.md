# Creature climbing: design

Status: design (Phase 1), 2026-10-17. Implementation branch: submodule `feat/creature-climbing`.

User constraints (binding):
- No separate representation of a plant for foot placement: feet and body find surfaces on the object's own render mesh (plants: LOD0 bark submesh at the instance transform). No capsules, SDFs or proxies (FloraObstacles capsules explicitly excluded).
- Generic: anything with real geometry in the user's game (SpaceGame) is climbable with no per-object authoring.

## 1. Goals / non-goals

Goals:
- The desert monitor climbs the lab Baobab and other real geometry: up, rest, turn on the trunk, head-first descent.
- Generic surface query: any collider set selected by `PhysicsScene` + `LayerMask` (SpaceGame: TerrainColliders, baked MC MeshColliders, buildings; flat, gravity −Y).
- Concave and convex transitions (ground→trunk 90°, trunk→branch) without folds; segments within 5 %; planted feet within 2 cm.
- Walking cost unchanged (0.031 ms/monitor, ≤ 4 ms per 100, R23); climbing monitor ≤ 0.25 ms.

Non-goals (this branch): terrain walls with tilted up (Q2); falling/slipping physics (sim stays kinematic); overhangs past `maxSurfaceAngleDeg`; netcode; Burst/RaycastCommand batching; changes to the plant baker.

## 2. Architecture

```csharp
public struct SurfaceHit { public Vector3 point, normal; public int source; public float distance; } // 0 terrain, else collider id
public interface ISurfaceProbe : IGroundProbe {
    bool Probe(Vector3 near, Vector3 up, float window, int preferSource, out SurfaceHit hit);
    bool Cast(Vector3 origin, Vector3 dir, float maxDist, out SurfaceHit hit);
    bool AnySurfaceNear(Bounds b);
}
```
The sim climbs only when `ground is ISurfaceProbe` and `species.climb.canClimb`; otherwise today's path runs unchanged.

Add (Scripts/Creatures/):
- `SurfaceProbes.cs`: `SurfaceHit`, `ISurfaceProbe`, `PhysicsSurfaceProbe(PhysicsScene, LayerMask)` (ray probe, smooth normals, inside test, triangle cache), `CompositeSurfaceProbe(terrain, surfaces)` (nearest surface, source hysteresis, AABB gate).
- `SurfaceMeshCache.cs`: per collision mesh tris + normals, read once. `BarkOnly(Mesh lod0)` shares lod0 vertices/normals with submesh 0's triangles exactly; `Physics.BakeMesh` once; cached per source mesh.
- `CreatureSurfaces.cs`: owns the surface PhysicsScene (MarchingCubes: a local physics scene in play mode — no layer/ProjectSettings change, player and terrain chunk colliders not in it; SpaceGame: default scene + mask). `Register/Unregister`, active AABB list, `FindClimbables`.
- `ClimbableFlora.cs`: every 0.25 s gathers PlantScatter instances of climbable species near creatures; pooled MeshColliders (bark-only LOD0 at instance TRS); `Physics.SyncTransforms`; ≤ 1 bake per frame.
- `CreatureSurfaceMesh.cs`: optional component registering a render-only object's `MeshFilter.sharedMesh`.
- `CreatureClimb.cs`: up field, head anticipation casts, pitch limiter, steepness factors.
- `ClimbingBrain.cs`: wraps WanderBrain with climb states.

Change: `CreatureSim.cs` (per-joint up field; parallel-transported heading; climb gait factors; pitch limiter; `Up[]`, `ClimbWeight[]`, `Source[]`, `Blocked`, `ClimbAllowed`; `upAt` stays gravity up), `CreatureLegs.cs` (`Up(l)` from sim; steepness step factors; wrap-cast rest fallback; grip rule), `GroundProbes.cs` (`FlatGroundProbe : ISurfaceProbe`; cache `Cast` + `TangentPlane`), `CreatureSpecies.cs` (`ClimbSpec climb`: canClimb, maxSurfaceAngleDeg 100, maxHeightBodyLengths 1.5, speedFactor 0.5, descentSpeedFactor 0.4, clearanceFactor 0.65, strideFactor 0.6, stepTimeFactor 1.2, liftFactor 0.6, upRateDeg 270, upSmoothJoints 3, pitchLimitDeg 25, minWidthFactor 1.5; 0 = default), `CreatureWorld.cs` (composite ground; `groundSource {Auto, Physics}` + `surfaceMask`; `queriesHitBackfaces` around TickAll; per-creature gate), `EnclosureArea.cs` (`maxHeight`, `obstacleClimbable[]`), `WanderBrain.cs` (skip the climbed obstacle), `EnclosurePlant.cs` (registers bark LOD0), `CreatureLab.cs` (ClimbingBrain, climbable trunk, maxHeight = min(cap, 0.45 × plant height)), `PlantScatter.cs` (read-only `GetClimbables(Bounds, list)`, append-only), `CreatureDebugView.cs`.

## 3. Algorithms

3.1 Physics probe: ray from joint centre c = near + u·clear along −u over clear + window, backfaces on. Front-face hit = answer. Back-face hit (inside solid) → re-cast from c + u·window down, front faces only, take the exit surface above (R25 nearest-surface rule; never drop through a branch, never lift onto one from below). Normal = barycentric interpolation of mesh vertex normals; non-mesh colliders fall back to `hit.normal`. Per query slot triangle cache: test the last triangle analytically (Möller–Trumbore); a hit within (0, 2·clear] is exact; else raycast.

3.2 Composite: terrain part bit-identical when up ≈ gravity; tilted up intersects the cache node's tangent plane (reject n·u < 0.2 or |t| > window). Surface part only when `AnySurfaceNear`. Choose smallest |offset|; `preferSource` wins within 0.25·clear (hysteresis).

3.3 Up field: per joint normal, Gaussian-smoothed along the chain (K = upSmoothJoints), climb weight w = smoothstep(25°, 50°, angle to gravity), target = slerp(g, ñ, w), rate-limited (upRateDeg) and low-passed. Frame up = slerp(GroundNormals, Up, w). Heading parallel-transported by the head's up rotation (not projected). Head anticipation: concave forward cast; convex probe ahead plus wrap cast at an edge; normals past maxSurfaceAngle → `Blocked`, braking stop.

3.4 Gait: steepness s = smoothstep(30°, 80°) per attach joint lerps clearance ×0.65, step threshold/overshoot ×0.6, step duration ×1.2, lift ×0.6, speed ×0.5 up / ×0.4 head-down, sway ×0.5. Grip: at s > 0.5 a step starts only if ≥ 1 foot per girdle and ≥ half of all feet stay planted. Rest probe miss on a cylinder → cast toward the attach ground point (feet hug the trunk). Pitch limiter (pitchLimitDeg) after grounding + RestoreLengths, only lifts away from surfaces: concave fold lifts joint i, convex fold lifts joint i+1; lengths restored again. Also removes R25's 50–61° rim folds.

3.5 ClimbingBrain: goals from horizontal casts at h ∈ [0.3, 1]·maxHeight, accepted if surface angle ∈ [60°, max] and width ≥ minWidthFactor·body width (two opposite casts). States: Wander → Approach (p = 0.35 after a pause) → Climb → Rest 4–10 s → Descend (target on the ground 1–1.5 body lengths away → helical U-turn, head-first) → Wander. Safeguards: no progress 4 s → Descend; Blocked → re-pick; above maxHeight → Descend.

3.6 Debug view: per-joint Up, probe sources coloured, anticipation casts, climb goal, surface collider AABBs; allocation-free.

## 4. Perf

Per-creature gate (joint AABB + reach vs active surface AABBs); far from surfaces = terrain-only (+~0.5 µs). Climbing ≈ 70–90 queries/frame; worst ~0.18 ms all raycasts, expected ≤ 0.08 ms with the triangle cache; budget ≤ 0.25 ms per climbing monitor. No per-tick GC. Bakes 1–3 ms, one per frame. Report a before/after Stopwatch table plus raycasts/frame and cache hit rate.

## 5. Tests (EditMode; generated real meshes + MeshColliders, scales 1 and 4)

SurfaceProbe_CylinderSide_SmoothNormal; SurfaceProbe_InsideSolid_ExitsAbove / _UnderBranch_StaysOnGround; SurfaceProbe_IgnoresTriggersAndOtherLayers; SurfaceProbe_TriangleCache_MatchesRaycast; Composite_Corner_NoFlipFlop; Composite_FarFromSurfaces_NoPhysicsQueries; Walking_BitIdentical_WithInertSurfaces; Climb_GroundToTrunk_NoFold (3D bend ≤ 30°, pitch ≤ limit + 2°, segments ≤ 5 %); Climb_FeetOnSurface (± 2 cm·scale); Climb_BodyClearsTrunk; Climb_NoJitter; Climb_TrunkToBranch_Convex; Climb_DescendHeadFirst_ReturnsToGround; Climb_OverhangPastLimit_Blocks; Climb_RealBaobab_Smoke; SurfaceMesh_BarkOnly_IsRenderGeometry; ClimbableFlora_PoolPlacesAtInstanceTrs; ClimbingBrain_GoalsOnSurface_BelowMax; Containment_3D_WanderAndClimb_60s; Renderer_Bounds_ContainClimbingBody; Perf_Walking100_Unchanged (≤ 4 ms); Perf_ClimbingMonitor (≤ 0.25 ms); Climb_NoAlloc. All existing tests stay green.

## 6. Editor verification

Verify the instance (MarchingCubes@…, 6000.2.6f2), CreatureLab in play mode: concave corner, mid-climb front/side, resting, helical U-turn, head-first arrival, F3 view, R25 hole re-shots, scatter grove with ClimbableFlora AABBs. Read back sim ms walking vs climbing, raycasts/frame, cache hit rate, pool size, bakes. Full EditMode suite.

## 7. Risks

Thin R23 headroom (gate per creature); Mono raycast cost unmeasured (triangle cache mitigates); global `queriesHitBackfaces` toggle (main thread only); open L-system tube ends; unreadable meshes give faceted normals; LOD0 used beyond its draw distance; PlantScatter plots only near the eye; local physics scene needs play mode; tight helix vs lateral bend limits; module still in TerrainGen.Runtime (separate asmdef for SpaceGame later).

## 8. User decisions

(Recorded in the ledger once answered.)

User decisions, 2026-10-17:
1. Keep the monitor at scale 4; raise the lab Baobab `plantScale` from 1.2 to 2.0.
2. Creatures also climb steep terrain (dug-hole walls, cliffs) with the same tilted-up path. This replaces the non-goal in §1: the composite's terrain part must answer tilted-up probes properly (field probe along the tilted up, not only the cache tangent plane), and R25's hole tests must stay green.
3. Climbable plants: every species with `obstacleRadius > 0`, bark submesh only, no new authoring field.
