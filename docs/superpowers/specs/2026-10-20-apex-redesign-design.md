# Apex redesign: design

Status: design, 2026-10-20 (rev. 2). Replaces the current Apex completely. Submodule `Assets/TerrainGen`, new branch
off `feat/creature-integration` (worktree outside `Assets/`, creature-module workflow).

**Reference image:** `docs/superpowers/specs/assets/2026-10-20-apex-reference.png`, with enlarged crops beside it:
`…-reference-head-x6.png` (head, beak crests, throat flap, breathing holes), `…-reference-body-x3.png` (stance, folded
wing blades, keel, hind leg), `…-reference-tail-x3.png` (tail loops, near blade). **Open them before every work
session and before every hand-off.** The picture is the spec for the look: shape, proportions, pose, colours and
details. The user's words (quoted in §1) say what the parts *are* and how they move; for how they *look*, the picture
leads — use the enlarged crops for small details. The user drew a colour-highlighted copy of the picture but it never
reached us; the crops stand in for it.

## 0. Intent

The user wants a new creature, "the Apex", that looks like the reference image and moves the way they describe. The
previous attempt (and an earlier one) came out as a pterodactyl; the user wants it deleted and nothing of it reused.

There is a second purpose: **every new part is a reusable building block.** "If this goes well, we can reuse the
assets from the Apex to create lots more cool creatures." So each part is a general, parameterised kit part (its own
name, its own `[Param]` fields, catalogue entry and tests), made with care (the head and the wings above all). The Apex
is only its first user. No part is hard-coded to the Apex.

## 1. What it is (from the user and the reference)

A large winged predator. Its wings are thick, soft and meaty, a bit like a manta's, but they fold, and on the ground
it walks on the folded wings like crutches. One pair of dragon-like hind legs. **One flowing body from the head to the
tail tip**: the trunk thins into the neck and the neck into the head without a break.

| Part | What the reference shows | User's words |
|---|---|---|
| **Stance** | Body held high and chest-up, the neck raised steeply, the head highest, pointing up and forward. The folded wings are the front supports: each is a long, soft, leaf-like **blade** standing on the ground at its lower end and rising past the shoulder to a pointed tip **high above and behind the back** (both tips stand side by side at the top-left of the picture). The near blade's ground end is in front of the hind leg; the far blade reaches the ground ahead and to the right. | "walks on its wings when on ground" |
| **Wings** | Thick, soft, never a plane. Folded: the blade is broad (a leaf, not a stick), its **lower end a blunt, rounded, soft club** on the ground (no visible claw), its lower half maroon like the body, its upper half teal-green, with **dark lengthwise stripes** running along the whole blade. The root starts at the shoulder and follows the flank part of the way toward the hips. Open: a broad manta-like sail, smooth trailing edge. | "meaty, a little like the manta, only foldable"; "the wings go the entire way up to its body"; "make sure to make the wings soft, not just a plane" |
| **Back** | A **sharp hump** on the back over the shoulders/wing roots; the back is dark maroon with teal mottling. | "almost a sharp hump" |
| **Chest** | Pale; a **keel** (sternum) jutting forward and down from the chest below the neck root. | "a chestbone, basically like birds have" |
| **Trunk** | Muscular but slender; dark maroon/plum on top. | "both muscular and slender" |
| **Neck** | The body thins into a long, raised neck — **the same chain as the body**. Dark top with a **teal stripe along the top** from the head back. | "it should just be an extension of the body, following the same chain … a very flowing transition from body to head" |
| **Throat flap** | Very large: the **whole underside from the jaw back to the chest is one broad, pale sail**, deep, with a nearly straight, sharpish lower edge running from under the jaw down and back to the chest, and a **soft rounded rim** along that edge. Faint lengthwise creases. | "skin flap … or a skin bag like a pelican, but a bit sharp, soft edge along the entire thing" |
| **Breathing holes** | A row of **five or six dark pits** with pale rims, on the upper part of the flap / side of the throat, in the front third of the neck, running along the neck. | "breathing holes high on the underside of the neck" |
| **Flap motion** | The flap has **its own small chain connected to the body chain** so it swings a little. | "maybe this flap should have its own chain that is connected to the main body chain" |
| **Head** | Long, tapering, **beaked serpent's head**: dark maroon top, pale underside, pointed beak. Fine **ribbed grooves along the mouth line** (lamellae). On top of the upper beak near its tip, **two equal teal crests side by side, splaying apart in opposite directions (left and right): seen from the front their cross-section is a "V"**; each curls back a little like a hook. In the side view they overlap (user correction 2026-10-20). The transition from neck to head is seamless. This is the showpiece. | "almost like a beaked serpent's head, with 2 large protrusions on the upper beak, which makes it look really cool"; "make the head really nice" |
| **Tail** | **Very long and large**, teal with darker stripes like the wings, a **broad flat ribbon** flattened side to side (cross-section a rounded "\|"). Even standing, it leaves the hips low and then rises in a **big loop** behind the body. | "very long and quite large … cross-section would look like a rounded \|" |
| **Hind legs** | One pair, slim, dark maroon-brown, dragon-like (digitigrade), clawed feet, under the rear of the trunk. | "dragon like legs" |

### What it does

- Walks around on its folded wings and hind legs.
- Flies. **In flight the whole body bobs with each wingbeat and the bob travels down the body chain**, like the
  Winged Serpent ("quite good at this"), so it looks natural. The neck carries the head steadier than the shoulders.
- **In flight the tail twists and turns** on its own, a slow travelling roll and curl. It is decoration: the tail does
  **not** visibly steer or change the flight.
- Takes off from the ground and lands back on it (it must reach every flight phase the kit checks: wing-walk, launch,
  beat, glide, flare, touchdown).

## 2. Goals, non-goals, anti-goals

**Goals.** Every feature in §1 present and recognisable; the side silhouette on the ground matches the reference;
it walks, flies with a visible travelling bob, twists its tail in the air, lands; the new parts are general kit
parts; all 14 kit checks green with **no** `kKnown` entry for the Apex; zero GC per frame; sizes from `sizeScale`.

**Non-goals.** No new behaviour or hunting AI (it may keep the shipped flight behaviours, §6). No sound, no new
shading model (colours through the existing look modules and `Layers` rows / named kinds). No change to any other
species' look or numbers.

**Anti-goals (a failure even if every test passes):**
- **It reads as a pterosaur.** No single long wing finger with a thin membrane, no pteroid / propatagium, no crested
  bony pterosaur skull, no thin bird-like body on stilt arms, no knuckle-walking on a short folded hand under the
  chest. The folded wing is a tall soft *blade* rising high above the back; the open wing is a thick manta-like sail.
- **Anything from the deleted Apex comes back**: SailWing, SerpentNeck, CasqueHead, its generator, its numbers.
- A visible break between trunk, neck and head (a separate neck tube, a seam, a step in the outline).
- The bob is invisible (the old Apex had kLift 0.75 and airLevel 0.8, which flattened it).
- The tail visibly drives the flight, or the tail just hangs straight in the air.
- The head is a plain cone or capsule; the crests are small bumps.

## 3. Constraints (from the project)

- Creature-kit rules: `.claude/skills/creature-kit/SKILL.md` and `references/` — author at scale 1 in metres; lengths
  x s, times x sqrt s; zero GC per frame; main thread; never edit core files (`CreatureSim`, `CreatureLegs`, mesh
  builders, renderer) for one species; generic behaviour in a shared system enters as a data flag, off by default, with
  every shipped species bit-identical (goldens untouched). **This applies to the flight and mesh code too** (my call,
  resolving a builder question): no species yet combines a custom chain body (`ISpineChainBody`) with the shared wing
  flight; where `CreatureWings` / `WingedMeshBuilder` / compose assume `SpineBody` fields, the builder may add opt-in
  data flags or read the body through `ISpineChainBody`, off by default, every other species bit-identical. New part
  types `MeshOrder` 100; never take a new global material id (use named kinds); `[Param]` on every field; catalogue
  regenerated.
- The user judges the look in Unity (memory: no render-iteration loop for taste; offline renders are fine as a
  sanity check for placement, clipping and gross silhouette).
- Unity MCP: verify the instance is `MarchingCubes@…` before acting (CLAUDE.md). Terrain is untouched.

## 4. Decisions

### Decided by the user
1. Complete redesign; **delete the current Apex** and reuse none of it.
2. Every anatomical part is new, and each is a reusable building block for future creatures.
3. Ground: walks on folded wings + hind legs. Air: flies with the Winged-Serpent-style travelling bob.
4. Tail twists and turns in the air, cosmetically.
5. Throat flap gets its own chain connected to the body chain.
6. Wing root: from the shoulder, following the flank part of the way toward the hips (adjustable up to the hips).
   Wings are soft and fleshy, not planes.
7. **The neck is part of the body chain**, not a separate neck structure: smoother in motion and a more coherent,
   flowing shape from body to head.
8. The picture leads on how things look, including the beak crests; use enlarged crops for detail.

### My calls (the user approved the first five on 2026-10-20)
- **"New parts" means new anatomy, not a new physics engine.** The shared *systems* stay: `CreatureSim` (the spine
  chain), `CreatureLegs` (gait, two-bone IK), `CreatureFlight` / `CreatureWings` / `FlightModel` / `AirChain` (wingbeat
  as a step in the air, launch, landing, wing-walk), `FlightBrain`, the kit services and checks. Every *part* (shape,
  mesh, part runtime) is new.
- **The name stays "Apex"** (new asset, new GUID; the roster entry is repointed).
- **Size:** the largest flyer in the lab, at least the old Apex's size (scale ~4); the builder fixes the exact scale
  inside `FlightBrain.FitsAviary`.
- **Mouth closed at rest** (the reference shows a closed beak), opening on calls / strikes.
- **Colours** (sRGB, approximate from the image): dorsal maroon-plum `#4A1E33`; belly / chest / throat flap / lower jaw
  cream `#D9CDB8`; wing fan and tail teal-green `#1F6B66` with darker lengthwise stripes `#163F45`; the wing's lower
  (arm) half maroon blending into the teal; teal dorsal stripe along the neck top; beak crests bright teal `#3FC0B0`;
  breathing holes and claws near-black.
- **New in rev. 2: the tail loops on the ground too.** The picture shows it rising in a big loop while standing. The
  tail overlay (§5.6) therefore has a calm ground pose (a raised loop, slow drift) as well as the livelier air motion;
  both strengths are parameters (ground strength can be set to 0).

## 5. The parts

Six new part types. Names are proposals; the builder may rename, but each stays generic. Each gets a test class
(`Tests/EditMode/Creature<Name>Tests.cs`) with its invariants and a RED proof that each test bites (kit rule).

### 5.1 `FlowBody` — one chain from head to tail (Body part, `ISpineChainBody`)
Replaces `SpineBody` for this species (SpineBody's mesh can only draw elliptical rings; `RayBody` is the precedent for
a body that lays out the chain and draws its own mesh). It is **the whole animal's spine: head, neck, trunk and tail
are one chain**, as the user asked. Same chain data as SpineBody (joints from profile keys, spacing, rigid head
joints, clearance, bend limits).
- **Neck in the chain.** On the ground the sim's follow-the-leader chain and the joints' clearances carry the neck
  raised and the head highest (the reference's pose); in flight the shared `AirChain` already lays the joints ahead of
  the girdle along a curve to a steadied head target, so the head stays steadier than the bobbing shoulders. The
  joint spacing in the neck should be fine enough for a smooth S-curve.
- **Section channels** along the body (profile keys with extra channels), drawn as one continuous surface:
  - `hump` height, `humpSharpness` and its place: a sharp dorsal ridge over the shoulders (a peak, not a broad bump);
  - `keel` depth, `keelSharpness`, `keelForward`: the sternum jutting forward and down from the chest;
  - `flankMuscle`: the muscular shoulder/flank masses;
  - `blade` (tail): the section goes from the trunk's oval to a **tall, narrow rounded ribbon** (a superellipse with
    height/width >= 3 on most of the tail, round top and bottom edges), tapering to a fine tip;
  - the neck's section: slimmer, slightly taller than wide, flowing into the head.
- **The head end** is where the head part (§5.4) sits: the body's front rings end inside the head's solids so the
  outline runs on without a seam or step (test: no outline step at the join, measured on the rest mesh's silhouette).
- Normals from the surface (finite differences), dorsal / belly shading channel as the body's. Must survive the full
  bend range (MaxBend, PoseSweep) without inverted triangles.

### 5.2 `FleshWing` — the soft folding wing (`WingPart` subclass)
Flown, folded and walked by the shared flight system (beat, fold, launch, touchdown, wing-walk on the wrist). Its own
mesh and its own bones/runtime:
- **Soft, not a plane.** A fleshy volume: thickest along the arm and the root, a round leading edge, thinning toward
  the trailing edge and tip, rounded everywhere (no hard sheet edges), subtle swells over the arm and root muscles, a
  soft rounded rim along the trailing edge, a little sag and billow. Edge-on it reads as flesh, never as a card.
  Test: at mid-span the thickness is at least a set fraction of the local chord; no zero-thickness edges.
- **Root: a middle ground.** From the shoulder the root follows the body back along the flank — default about half to
  two-thirds of the way to the hips — then ends, leaving the rear flank and hind legs free. The rear attach is a
  parameter (`membraneRearJoint` + flank patches following the body's curve) that can run anywhere from the shoulder
  to the hips without other changes, so the user can try both in the Inspector. The root blends smoothly into the body
  (no gap, no seam line).
- **Fleshy arm** inside the wing's leading edge (maroon, blending into the teal), not a visible bone tube.
- **Ground end: a blunt, rounded, soft club** that it walks on — the reference shows no claw. The shared `thumbPlant`
  keeps the drawn contact planted (Gait checks the drawn foot).
- **Lengthwise stripes**: dark colour stripes and shallow ridges running along the rays (along the blade when folded).
- **Smooth trailing edge** (manta), no scallops, no single long finger.
- **Chain motion** as on the manta: the outer wing lags and whips at the stroke's turn, the trailing edge feathers and
  billows (new runtime; `AngleChain` is a fine utility to use).
- **Ground pose = the reference's blades**: the ground end in front of the hind feet, the fan folded back up along
  the forearm (shared `groundTallStance`, `groundLiftDeg`, `fanRearRollsWithFan`), the tips standing **well above and
  behind the back** (test: the blade tip is higher above the ground than the hump by at least 0.5 x hump height, and
  behind the shoulder). The folded blade is broad like a leaf (test: folded width at mid-blade >= a set fraction of
  its length). The thick layers must not interpenetrate or invert when folded (bind part-folded if needed, as the
  shared system allows).
Fold geometry is fragile (recorded lessons: two-ray zones turn inside out, mirrored bones in launch). Scan the fold
numbers over a grid with `KitChecks.MaxBendProblem` and take the middle of a passing region.

### 5.3 `Dewlap` — the throat flap with its own chain (part with runtime)
A large pale sail hanging from the underside of the neck, from just behind the jaw back to the chest: deepest under
the front-middle of the neck, a nearly straight, sharpish lower edge running from under the jaw down and back to the
chest, a **thickened soft rim** along that edge, faint lengthwise creases. It roots on the body's neck joints (sockets
on the body chain, so it rides the same chain as the neck) and has **its own chain** (2–4 links hanging down at a few
stations along the neck): a damped swing that lags the neck's motion, the wingbeat bob and turns, with gravity and
limits so it never passes through the neck or chest. Skinned between the neck joints and its own bones. Tests: it
swings (measurable lag after a neck move), settles without jitter, never enters the neck/chest, Froude-scaled.

### 5.4 `CrestBeakHead` — the beaked serpent head (head part)
The showpiece; look at the head crop. Built from SDF solids (`SculptMesher` is shared infrastructure), rigid to the
body's head joints. A long, tapering, slightly flattened serpent skull flowing into a pointed beak; small eyes set
back under a soft brow; dark top, pale underside and lower jaw; a closed mouth line along the side with **fine ribbed
grooves** (lamellae). **Two equal crests on top of the upper beak near its tip, a mirrored pair side by side, splaying
apart left and right so that seen from the front they form a "V"**, each curling back a little, bright teal keratin,
clearly visible in the side and front silhouettes (user correction 2026-10-20: same size, opposite directions). The head's
back end overlaps the body's front rings so neck and head flow together. Jaw on its own bone (closed at rest, opens on
calls / strikes). Parametric: skull length/width/depth, beak length and hook, crest count, positions, heights, curl
and thickness, groove count and depth. Tests: closed solids, crests in the silhouette and above the beak line, jaw
opens and closes, no inverted triangle through the jaw's range, mesh build inside the 5 ms budget (cache).

### 5.5 `DrakeLeg` — the hind leg (limb part)
A two-bone limb for `CreatureLegs` (it produces the same leg spec a Leg2Bone does) with its own mesh: a muscular haunch
blended into the trunk, a slim shin, a raised hock and long metatarsus, three or four toes with dark curved talons.
Slim and dark as in the image. Ground contact checks as any leg (Gait).

### 5.6 `TailFlourish` — the tail's loop and twist (Late part runtime, an overlay)
Re-poses the body's tail bones after the sim, like the Tuck's pose over the sim:
- **In the air** (eased in by the flight's air weight, out on touchdown): a slow **travelling roll** (the ribbon turns
  about its own axis, growing toward the tip) plus a **lazy curl** (an S travelling down the tail).
- **On the ground** (calmer, my call from the picture): the tail leaves the hips low and rises in a big loop behind
  the body, drifting slowly; it never touches the ground beyond its base.
- Per-individual seed, Froude timing, strengths as parameters (each can be 0).
- **The flight and the walk are untouched**: the flight model's path, the girdle and the feet are bit-identical with
  and without the overlay (test). Tests: tip roll range >= 60 deg in sustained flight; the ground loop rises above the
  hips; no inverted triangles (PoseSweep); inside the culling bounds (check 6); zero GC.

### 5.7 `PitRow` — the breathing holes (surface part)
A row of recessed pits with soft pale rims on the body surface: joint range, angle around the section, count (five or
six here), size and spacing. Rides the body chain. Reusable for any spiracles, nostrils or sensory pits. Tests: every
pit sits on the surface (no floating, no hole through), no inverted triangles under bending.

### Flight: the bob
Tune the `Fly` module for the Winged Serpent's character: low glide lift so the beats carry the body, `airLevel` low so
the trunk follows the path, a visible travelling wave (`AirChain`). Target (measured in a test, cruise, steady flight):
girdle bob peak-to-peak >= 3 % of the body length; the mid-tail moves with a visible lag behind the girdle; the head's
bob <= 1/3 of the girdle's. If the plain AirChain cannot reach it at this size, the builder may use the shared
`AirTwist` bob terms (`girdleBob`, `bobTail`) — data only.

## 6. Species asset

`Config/Creatures/Apex.asset` (new GUID) from a generator `Tools~/SpeciesGen/Apex.py` (kit services, `kityaml`).
Parts: `FlowBody`, wing arm (Leg2Bone, mirrored; its own mesh hidden by the wing as wing arms are today), `FleshWing`
(mirrored), `DrakeLeg` (mirrored), `Dewlap`, `CrestBeakHead`, `PitRow` (mirrored), `Eyes`, `TailFlourish`. Modules:
`Walk`, `Fly`, `QuadLaunch` and the shared flight behaviours (`Wander`, `FlightExcursion`; `SkyHunt` optional — keep
only if it reaches every phase and lands, with `handBack`). Looks: `Skin` (maroon dorsal, cream belly, teal dorsal
stripe), `Membrane` (teal), `Layers` rows / named kinds for the crests, the stripes and the pits. Lab: the existing
Aviary roster entry, repointed to the new GUID.

## 7. Deletion (first build step)

Remove the old Apex completely: `Config/Creatures/Apex.asset` (+ .meta), `Tools~/SpeciesGen/Apex.py`,
`Scripts/Creatures/Kit/SailWing.cs`, `SerpentNeck.cs`, `CasqueHead.cs` (+ .meta; no other species uses them),
`Tests/EditMode/CreatureApexTests.cs` (+ .meta); their mentions in comments (`WingSpec.cs`, `BeakHead.cs`), the
catalogue (regenerate), the skill docs' examples (`creature-kit` SKILL.md uses Apex in its command examples: point
them at the new Apex). Findings and lessons in the skill docs that came from the old Apex are **kept and reworded** so
they no longer name it (they are general fold lessons this build relies on); the skill docs live in the parent repo, a
second commit there. Keep the shared opt-in flags (`thumbPlant`, `fanRearRollsWithFan`, `approachBleedsSpeed`,
`SkyHunt.handBack`): they are generic and the new Apex uses them. `Swell` stays (Delver, KomodoDragon, SkyDragon use
it). Every other species bit-identical.

## 8. Done means

- All features in §1 present; the user confirms the look in Unity against the reference.
- The six parts have their tests (with REDs); `creature_kit.py check Apex` green on all 14 checks, no `kKnown` entry;
  full harness suite green; `unity-compile`, `compile_check.py`; Unity once (`CreatureKitTests`, the new part tests);
  catalogue fresh.
- Shape tests that pin the reference's key reads: folded blade tip above the hump and behind the shoulder, blade broad;
  hump is the trunk's highest dorsal point and sharp; keel below and ahead of the chest; neck raised with the head
  highest; no outline step between neck and head; tail section height/width >= 3 on its middle; crests a mirrored equal pair splaying into a V (front view); dewlap below the neck and never inside it; the bob targets above.
- A side-view offline render of the ground pose placed next to the reference image as a silhouette sanity check
  (not a look-tuning loop).
- Hand-off note: the aviary, play-mode setup, what to look at per part (blade height and softness, hump, keel, the
  flowing neck, flap swing, crests, tail loop and twist, bob), the knobs for each, and the 0.9x / 1.1x individuals.

## 9. Left to the builder

Part names, exact parameter sets and defaults, bone counts, mesh resolution, the joint count and spacing, the exact
scale, the dewlap's chain topology, the tuning of the fold and the flight numbers within the targets above, and the
order of work (deletion first, species last).

## 10. Risks

- **Thick wing folding**: two-ray skinning of a volume is harder than of a sheet; the fold may invert or
  interpenetrate. Mitigation: bind part-folded, thickness offsets along zone normals, grid scans, PoseSweep.
- **Raised neck in the walking chain**: the walking sim was built for low necks; a steep neck from clearances alone
  may lag or sag in turns. Mitigation: profile clearances and bend limits first, a check that the head stays highest
  while walking; if the sim cannot hold it, an opt-in data flag (off by default) in the shared system.
- **Tall blade vs pole**: one arm pole serves ground and air; a high elbow shaped the Hexadrake's inverted launch blend.
- **Bob at scale ~4**: slow Froude beats weaken the visible bob; may need AirTwist's bob terms.
- **Tail overlay vs bounds**: the looping, twisting tail must stay inside the renderer's culling bounds (check 6).
- **Perf**: more parts and a dewlap chain; stay inside the per-species budget (`PerfBudgetMs`), mesh build < 5 ms
  (SDF head: use the mesher's cache).

## 11. Additions, 2026-10-20 (user, with a higher-resolution reference)

**Best reference now:** `docs/superpowers/specs/assets/2026-10-20-apex-reference-hires.jpg` (736x600), crops
`…-hires-head.png` and `…-hires-wingend.png`. It leads over the small screenshot.

- **Mouth (supersedes my "closed at rest" call):** the mouth hangs slightly open at rest, showing rows of small teeth
  along the upper and lower jaw (the "lamellae" are teeth). Rest gape a few degrees; calls open it wider.
- **Crests:** the V-shaped mirrored pair, **1.5x larger** than the Task 4b default (user agreed).
- **Folded wing's ground end:** a thick, fleshy club where the wing sheet rolls and wraps around the forearm's end
  (a rounded, rolled end — no claw), stripes running along the whole blade.
- **Throat sail:** very deep (deeper than the neck), five pits on its upper part near the jaw end.
- **Bob:** the Apex bobs **way more** than the Winged Serpent because it is heavier: girdle bob peak-to-peak
  >= 6 % of the body length (twice the serpent-like target in §5), still travelling down the body with the head steadier.
- **Integration:** at the end, merge `feat/apex-v3` into `feat/creature-integration` **locally** (no push). Rebuilding
  the Creature Lab (and committing `CreatureLab.unity`) is approved.
