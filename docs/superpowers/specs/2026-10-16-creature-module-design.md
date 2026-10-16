# Creature module + Creature Lab — design

Date: 2026-10-16. Status: draft for review.

## Intent

The project already generates terrain and plants procedurally. This adds
**procedurally animated animals**, built with the technique from the user's
Manim video (`Documents/video_manim/lizard.py`): a chain of joints that
follow the head under a distance constraint and a bend limit, a radius per
joint that defines the body, a skin built around those radii, and legs that
stay planted until they lag behind, then step, solved with two-bone IK
(law of cosines). Here it runs in 3D, on this project's terrain.

The user's two priorities, in order:

1. **It looks really good.** A look between stylized and realistic. Clean
   shapes, real shading (lit, with received and cast shadows), smooth
   bodies with no visible polygon kinks at joints. Not a debug render of
   tubes.
2. **It is fast.** Usually 1–2 creatures are on screen, occasionally many. The
   architecture must not need a rewrite when "many" arrives.

The first deliverable is a **Creature Lab** scene: generated dune terrain
with one enclosure per species. Each species has a creature wandering
inside its enclosure, and the player walks around to look at them.

## Goals

- A generic creature system driven by **data**. A species is an asset
  (body profile, legs, gait, look). Adding a spider, a snake or a six-legged
  insect means authoring an asset, not writing new code paths.
- v1 ships one species, the **lizard**, polished.
- Creatures walk on the real terrain. Spine and feet follow the ground,
  including dune slopes, in both flat-world and globe mode. Up comes from
  `PlanetGravity.UpAt(p)`.
- **Procedural texturing** through a creature shader: patterns and palette
  per species, with small per-individual variation.
- GPU-deformed, instanced rendering: **one rest-pose mesh per species, one
  draw call per species** (plus its shadow pass), whatever the number of
  individuals.
- Behaviour v1: **wander** inside the enclosure.
- The Creature Lab scene, as described below.

## Non-goals (v1)

- Eye tracking. Eyes are plain black for now, but glossy, so they catch a
  specular highlight. Tracking is a later add-on, so eyes are separate
  bones, rotatable later.
- Scales as geometry. These come later as **vertex-shader displacement**.
  The design must keep the inputs for that available (see Rendering).
- Hand-painted textures. That decision comes later, but UV0 must already be
  a sensible unwrap so that a texture could be used without rebuilding
  anything.
- Reactions: to the player, to each other, food, fleeing. These get added on
  later through the brain interface.
- Physics interaction. No Rigidbody, and creatures don't push the player or
  get pushed.
- Crowd-scale simulation (Burst, GPU sim). Not installed and not needed now.
  Only the data layout must allow it later (see Performance).
- Fences or walls around enclosures.

## Anti-goals (failure even if it "works")

- A body that reads as segmented sausages, kinks visibly at joints, or
  shows flat-shaded facets.
- Feet that slide while planted, float above the sand or sink into it.
  Legs that snap or pop through the body.
- A creature that ever leaves its enclosure, even with only its tail.
- Per-frame GC allocations, or per-frame mesh rebuilds on the CPU.
- A species system where a new animal needs code changes in the simulation
  or the mesh builder. Gait and leg count must not be hard-coded to 4.

## Constraints (from the repo)

- Code lives in the submodule `Assets/TerrainGen` and goes into the
  `TerrainGen.Runtime` assembly, because it needs `DensityField`. Unity
  6000.2.6f2, URP 17, D3D11.
- Main-thread Unity APIs only. No `Task.Run` workers (Mono crash, see
  repo notes). v1 runs the simulation on the main thread.
- Ground queries go through the density field, **not colliders**.
  Colliders only exist in the LOD0 box. Use
  `TerrainQuery.TryFindGround(MCChunkManager.Instance.PhysicsField, …)`
  semantics (positive = solid, outward normal = −gradient). Its default
  search scans in 0.5 m steps, which is too coarse and too slow for
  per-joint per-frame use, so the module probes with a narrow window around
  the last known ground point (see Ground).
- Shaders: follow the `Grass.shader` template (target 4.5, StructuredBuffer
  plus SV_InstanceID, Lighting.hlsl with main-light shadow multi_compiles,
  ShadowCaster with `ApplyShadowBias`, DepthOnly). Respect the documented
  D3D11 gotchas: uniform loop bounds, 1-element placeholder buffers so
  nothing is unbound, C#/HLSL structs matched field-for-field.
- Don't touch the shared `Config/WorldConfig.asset` (`useGlobe: 1`).
- No new packages in v1 (no Burst, Mathematics or Animation Rigging). This is
  my call: the IK and chain are a few dozen lines, and package churn isn't
  worth it at this scale.

## Architecture

Five parts with one-way dependencies. Folder:
`Assets/TerrainGen/Scripts/Creatures/`.

```
CreatureSpecies (asset)        pure data: body, legs, gait, look
      │
      ├──► CreatureSim         pure C#: chain + frames + legs + gait. No Unity scene objects.
      │        ▲   uses IGroundProbe (field-backed in game, stub fields in tests)
      │        └── ICreatureBrain  (WanderBrain v1) chooses where the head goes
      │
      ├──► CreatureMeshBuilder rest-pose mesh + per-vertex bone indices/weights,
      │                        built once per species at runtime (no baking step)
      │
      └──► CreatureRenderer    per species: bone GraphicsBuffer, one instanced draw
                               (+ shadow), reads the sims' bone matrices each frame

CreatureWorld (MonoBehaviour)  owns all sims, ticks them, feeds renderers
CreatureEnclosure (MonoBehaviour) area + border mesh; constrains a brain
CreatureLab (MonoBehaviour)    lays out one enclosure + one creature per species
```

### CreatureSpecies (ScriptableObject)

All lengths are in metres. Assets live in `Assets/TerrainGen/Config/Creatures/`.

- **Spine:** joint count, segment spacing, and a **cross-section per joint**
  (width and height as separate radii, so the body is an ellipse: wider than
  tall, flatter belly). Plus a vertical offset so the belly sits at a
  per-joint clearance above the ground. Also the per-joint bend limit (cone
  half-angle), a set of rigid joints (the lizard head), and head/tail cap
  shapes (rounded snout, pointed tail tip).
- **Legs:** a list, any length (0 for a snake, 4, 6, 8). Each leg has its
  attach joint, side (±1), shoulder offset, rest-foot offset in the body
  frame, upper/lower lengths, thickness profile, knee direction
  (forward/back, as a pole vector in the body frame), step threshold, step
  duration, step lift height and forward overshoot. Optional
  third segment / foot shape: v1 needs a foot pad with toe nubs, and
  spiders need nothing more than two bones.
- **Gait:** each leg has a **gait group**. Only one group may be stepping at
  a time, and a group may start stepping only when a leg in it is past its
  threshold. Lizard: diagonal pairs (FL+RR, FR+RL). Hexapod: alternating
  tripods. Spider: alternating tetrapods. This replaces the video's
  hard-coded "partner" leg.
- **Locomotion:** head speed, turn rate, accelerate/brake, and how much
  speed drops while turning sharply.
- **Eyes:** joint, offsets, radius. Black and glossy.
- **Look:** palette (dorsal, flank, belly, pattern colour), pattern type and
  parameters (bands / spots / stripes / blotches; scale, contrast,
  softness), specular and roughness, rim strength. Per-individual
  variation ranges: size ±%, hue/value jitter, pattern offset.
- **Overall scale.** Lizard default: about 1.5 m long, so it reads well next
  to a 2 m player. My call.

### CreatureSim (per individual, pure C#)

State: joint positions, joint frames (forward/up/right), leg state (planted
foot point and normal, stepping flag, step progress, step start and goal),
and the current head heading. No allocation after construction.

Each tick (fixed sub-steps, for example 2 per frame as in the video):

1. **Head.** The brain gives a target point. The head turns toward it, with
   its heading clamped by turn rate in the **tangent plane of the ground**
   (up from the ground normal blended with `PlanetGravity.UpAt`). It moves
   forward at a speed that slows near the target and in sharp turns.
2. **Chain.** For i = 1..N−1, pull joint i to `spacing` from joint i−1. Clamp
   the direction against the previous segment's direction with a cone
   (`RotateTowards` with the bend limit; limit 0 for rigid joints). This is
   the 3D form of the video's angle clamp.
3. **Ground.** Each joint is placed at ground height + its clearance along
   up, using the ground probe. The probe is seeded from the joint's previous
   ground point, so it is a narrow bisection, not a scan. Ground height and
   normal are smoothed over a few frames to stop ripple chatter.
4. **Frames.** forward = direction toward the previous joint (the head uses
   its heading). up = smoothed ground normal, made perpendicular to forward.
   right = up × forward. Frames are what the skin and legs hang off. Without
   them the body twists.
5. **Body tilt.** Optional roll/pitch from the average of the planted feet.
   This is a nice-to-have, and should be enabled only if it looks better.
6. **Legs.** Rest point = attach-joint frame × rest offset, projected to the
   ground. A planted foot stays fixed in the world. A foot becomes eligible
   to step when it is farther than its threshold from rest. The gait groups
   decide which steps actually start. A step moves the foot toward
   rest + forward overshoot along a smoothstep, lifted by `sin(πt)`, and its
   **goal is probed on the ground** once, at step start.
7. **IK.** Two-bone, law of cosines, as in the video. In 3D the elbow lies
   on a circle, so it is resolved by the species' pole vector (front elbows
   back and up, rear knees forward and up). Leg length is clamped. The foot
   pad aligns to the ground normal and the body's heading.
8. **Bone matrices.** Write one 3×4 matrix per bone into the creature's slice
   of a shared array: spine joints, then 2 per leg plus the foot, then eyes.
   The renderer uploads it.

### ICreatureBrain / WanderBrain

`Vector3 Target(sim, dt)`. WanderBrain picks a random point inside the
**enclosure's safe area**, walks there, pauses for 0.5–3 s (sometimes with a
short head-turn "look around"), then picks again. It favours targets that
need moderate turns, so the path curves the way the video's lizard does.
It is seeded per individual, so behaviour is deterministic.

### Ground (IGroundProbe)

`bool Probe(Vector3 near, Vector3 up, float window, out Vector3 point, out Vector3 normal)`.

- **Game:** a field-backed probe on `MCChunkManager.Instance.PhysicsField`,
  so terrain edits (footprints, digging) are respected. It bisects inside
  `near ± window·up`. If that misses, it falls back to a wider
  `TerrainQuery.TryFindGround`. The normal comes from the field gradient.
- **Tests:** the stub fields in `Tests/EditMode/TestFields.cs` (plane,
  sphere, two-layer).

### Enclosure containment (hard guarantee)

An enclosure is a circle with a centre (projected to the ground) and a
radius R. The containment comes from the follow-the-leader chain: the body
lies (approximately) on the head's past path. So if the head's path never
leaves a radius `R_safe = R − (max body half-width + max leg reach + margin)`,
the whole creature stays inside R. The brain picks targets inside
`R_safe`. The sim also **hard-clamps the head position** to `R_safe`, as a
safety net against turn-rate overshoot. An EditMode test runs a long
wander and asserts that every joint and foot stays within R. Lizard
default: R = 8 m. My call.

## Mesh (CreatureMeshBuilder)

Built once per species at runtime, before the first draw, in under 5 ms.
No asset baking.

- **Body.** A tube of elliptical rings. There are **several rings per spine
  segment** (3–4), so the silhouette stays smooth. Each ring's radii come
  from a smooth (Catmull-Rom) interpolation of the per-joint profile.
  Normals are correct for an elliptical, tapering tube, not just radial:
  the taper term goes into the normal. The head and tail ends are closed
  with caps: the head is rounded or elongated into a snout, the tail tip
  is pointed. Ring vertex count is around 16 for the lizard body (my
  call), tuned for silhouette.
- **Skinning.** Each body vertex is weighted to the two nearest spine joints
  by its position along the segment (linear blend, ≤ 2 weights). Since
  bends are ≤ ~20° per joint, linear blend skinning without
  dual quaternions is fine. **Acceptance:** no visible creasing at maximum
  bend.
- **Legs.** Tapered tubes per bone, with a blended zone at the knee and
  elbow and a rounded shoulder blob that sinks into the body so the joint
  never shows a gap. A foot pad with toe nubs is skinned rigidly to the
  foot bone.
- **Eyes.** Small spheres skinned to an eye bone (child of the head joint).
- **Vertex data:**
  - position and normal in rest pose (bone-local, or rest-world with
    inverse bind; builder's choice)
  - bone indices and weights
  - **UV0 = (arc length along the part in metres, angle around / 2π)**:
    tile-uniform, ready for the scale shader and usable as a texture unwrap
  - UV1 = (part id: body/leg/foot/eye, ventral↔dorsal coordinate −1..1)
  - one submesh

## Rendering (CreatureRenderer + Creature.shader)

- One renderer per species in use. It owns a `GraphicsBuffer` of bone
  matrices (`count × bonesPerCreature × float3x4`) and a small
  per-instance buffer (seed, size, hue/value jitter, pattern offset).
- Each frame: upload the bones and call **one** instanced draw for all
  individuals of the species, using `Graphics.RenderMeshPrimitives` with the
  instance count, or the indirect variant. The shader indexes by
  SV_InstanceID. `worldBounds` = the union of the creatures' bounds. The
  builder must verify on D3D11 that SV_InstanceID is 0..n−1 for this draw
  path, and should fall back to `RenderMeshIndirect` if it isn't.
- **Vertex stage.** Blends the bone matrices into a world position and
  normal. A clearly marked hook, `CreatureDisplace(...)`, is where scales
  will go. In v1 it does nothing.
- **Look: "stylized-realistic."**
  - Lit by the URP main light with **received** shadows (main-light shadow
    keywords) plus SH ambient.
  - A soft wrapped diffuse, a gentle subsurface-ish warm tint in the
    terminator, GGX-ish specular controlled by roughness, a subtle rim,
    and fog.
  - Belly-to-back colour gradient from the dorsal coordinate.
  - Procedural pattern evaluated in UV0 space (so it sticks to the body as
    it bends), from the species parameters plus the per-instance seed:
    bands, spots, stripes or blotches, with soft edges and slight noise
    breakup.
  - Black glossy eyes.
  - Cast shadows through a ShadowCaster pass, and a DepthOnly pass.
- **Pattern code** goes in its own `Shaders/Creature/CreaturePattern.hlsl`,
  so hand-painted textures can later replace it behind a keyword.

## Creature Lab scene

- **Config.** A new `Config/Test/CreatureLabWorldConfig.asset`, made from
  `DesertWorldConfig` (flat world, dunes exactly as the generator makes
  them, `DesertWorld` density). **Plant scatter is off** in the lab, so the
  creatures stay readable. Grass follows the desert defaults. Both are my
  call and a one-line toggle.
- **Scene.** `Assets/Scenes/CreatureLab.unity`, generated by an Editor menu
  `Marching Cubes/Rebuild Creature Lab` that reuses the
  `BiomeTestScenes` copy-from-SampleScene approach (terrain, light, volume,
  player, target), plus a `CreatureLab` object.
- **CreatureLab component.** Holds a list of species. For each one it places
  an enclosure along a gentle arc near the player spawn, about 25 m apart
  (my call), and spawns one individual inside. Placement is at runtime
  once the ground is available (probe), so it adapts to wherever the dunes
  are. Placement prefers flatter spots within a search radius, but dune
  slopes are fine and are a deliberate test of the feet.
- **Border.** "Slight" means a low curb: about 12 cm high and 30 cm wide,
  conformed to the terrain by probing, in a sandstone tone, with no fences.
  The player can walk in and out freely. Creatures ignore the player in v1.
- **Debug view.** Toggled by a key, `F3` (my call): draws the chain, joint
  ellipses, foot rest points and IK lines, as a nod to the video and a
  tuning aid.

## Performance targets

- Simulation: ≤ 0.1 ms per creature per frame on the main thread
  (measured with Stopwatch, as in the repo's before/after convention).
  Most of that is ground probes; spine probes are narrow bisections.
- Rendering: 1 draw per species, plus shadow and depth passes, regardless
  of individual count.
- No GC allocations per frame (checked in the Profiler).
- Stress check: 100 lizards in one enclosure at ≤ 3 ms total simulation.
  This shows the "many" path isn't blocked. Moving the simulation to Burst
  jobs later is possible because sim state is flat arrays per creature and
  the bone output is already a flat array.

## Extensibility check (acceptance)

Without changing any simulation, mesh or renderer code, these must work:

- A **snake** asset (no legs, long spine, side-to-side gait coming from the
  brain's wandering path).
- A **hexapod** asset (6 legs, tripod gait groups).

Both get EditMode tests that build the mesh and run the simulation on a
stub plane. They don't need art polish or lab placement in v1; the lab
list just accepts them when they exist.

## Testing and verification

- **EditMode** (`TerrainGen.Tests`):
  - chain distance and cone-limit invariants
  - IK reaches reachable targets and clamps unreachable ones
  - gait: never two groups stepping at once
  - planted feet don't move
  - containment over a long seeded wander
  - mesh builds for lizard, snake and hexapod, with weights summing to 1
  - no NaNs on sphere and two-layer fields
- **Offline compile** via the workflow's `compile_check.py` before any
  Editor visit.
- **Editor:**
  - shader has no errors (`ShaderUtil.ShaderHasError`)
  - play mode in CreatureLab
  - screenshots from the player's eye, close up on the lizard on a slope
  - Stopwatch stats read back against the targets above

## Decided by the user during review

- **Base branch:** the most recent work. That is the submodule's
  `feat/game-integration` (2026-09-17, contains all of `main`), which holds
  `TerrainQuery`, the test fields and `TerrainGen.Tests`. The creature work
  goes on a new submodule branch, **`feat/creatures`, cut from
  `feat/game-integration`**. All code is in the `Assets/TerrainGen`
  submodule (the ground truth). The parent repo only gets the scene, the
  submodule pointer bump and this doc.
- **v1 lizard look: a desert monitor.**
  - **Shape:** long and low, with a long neck and a narrow head tapering to
    a pointed snout. A heavy, muscular tail tapers to a fine tip, and the
    tail is about as long as head plus body.
  - **Legs:** strong, splayed limbs; the elbows and knees sit out to the side.
  - **Colour:** sandy tones. A pale sand-ochre back, warmer flanks, a pale
    cream belly. Dark brown cross-bands across the back and tail, broken up
    by small pale spots, with banding that gets stronger along the tail.
  - **Eyes:** black and glossy.
  - **Movement:** the side-to-side sway from the undulation parameter, kept
    small.

## Settled during review (my calls)

- **Globe mode in v1 means code-path correctness only.** Up always comes
  from `PlanetGravity.UpAt`, and the sphere stub test checks that chain,
  feet and containment behave on a curved surface. Containment distance is
  measured in the local tangent plane. That is accurate enough for an
  8 m enclosure on a planet-sized radius. There is no globe scene in v1.
- **Performance numbers are targets, not fixed mechanics.** The builder may
  change how ground is probed to meet them:
  - probe every k-th joint and interpolate
  - probe once per frame instead of every sub-step
  - keep a small per-creature height cache
  Hard requirement: feet visibly on the ground, and no joint visibly
  inside or above the sand. Measure the real per-sample cost of
  `DesertWorld` first, and pick the strategy from that number.
- **Lab contents in v1: the lizard only.** The snake and hexapod assets
  exist for the extensibility tests. Adding them to the lab's species list
  must just work: each enclosure's radius comes from its species' size, and
  the arc spacing adapts.
- **Snake undulation is a generic locomotion parameter,** not a per-species
  brain: lateral head oscillation, with amplitude and frequency in the
  species asset, applied by the simulation on top of any brain's target.
  Lizards can use a small amount of it too, since real lizards sway.
  It is visible in the snake test as side-to-side motion.

## Left to the builder

- Exact bone matrix layout, rest-pose convention and buffer packing.
- Ring and vertex counts beyond the stated intent.
- Whether to do a quick 3D Python prototype of the simulation first. It's
  optional, since the 2D sim in `lizard.py` is already the reference.
- Exact shading maths, as long as it meets the look described above.
- File and class splits inside the folder.
