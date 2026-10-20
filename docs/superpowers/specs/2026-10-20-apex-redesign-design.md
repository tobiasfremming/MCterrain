# Apex redesign: design

Status: design, 2026-10-20. Replaces the current Apex completely. Submodule `Assets/TerrainGen`, new branch off
`feat/creature-integration` (worktree outside `Assets/`, creature-module workflow).

**Reference image:** `docs/superpowers/specs/assets/2026-10-20-apex-reference.png`. **Open it before every work
session and before every hand-off.** The picture is the spec for the overall look, proportions, pose and colours. The
image is small: for details it cannot resolve, the user's own words (quoted in §1) are authoritative — in particular
the **two large protrusions on the upper beak**, which the picture shows only as a teal tuft at the beak.

## 0. Intent

The user wants a new creature, "the Apex", that looks like the reference image and moves the way they describe. The
previous attempt (and an earlier one) came out as a pterodactyl; the user wants it deleted and nothing of it reused.

There is a second purpose: **every new part is a reusable building block.** "If this goes well, we can reuse the
assets from the Apex to create lots more cool creatures." So each part is a general, parameterised kit part (its own
name, its own `[Param]` fields, catalogue entry and tests). The Apex is only its first user. No part is hard-coded
to the Apex.

## 1. What it is (from the user and the reference)

A large winged predator. Its wings are thick and meaty, a bit like a manta's, but they fold, and on the ground it
walks on the folded wings like crutches. One pair of dragon-like hind legs.

Read the image in this order:

| Part | What the reference shows | User's words |
|---|---|---|
| **Stance** | The body is held high and chest-up, with the neck raised steeply and the head highest. The folded wings are the front supports. **The wrist is on the ground** and the folded hand runs back up along the forearm and well past it, so each folded wing is a tall, straight-ish **blade** from the ground up to a tip high above and behind the back (near wing: ground at front-centre up to top-left; far wing: a second blade to the ground at the right). | "walks on its wings when on ground" |
| **Wings** | Thick, meaty, **soft** (never a flat plane); the root starts at the shoulder and follows the flank part of the way toward the hips. Folded, the lower (arm) part of the blade is maroon like the body and the folded fan is **teal-green with paler stripes running lengthwise** along the blade. Open, a broad manta-like sail with a smooth trailing edge (no scallops, no single long finger). | "meaty, a little like the manta, only foldable"; "the wings go the entire way up to its body" |
| **Back** | A **sharp hump** on the back over the shoulders/wing roots. | "almost a sharp hump" |
| **Chest** | A **keel** (sternum) jutting forward and down from the chest below the neck root, like a bird's. | "a chestbone, basically like birds have" |
| **Trunk** | Muscular but slender; dark maroon/plum on top. | "both muscular and slender" |
| **Neck** | The body thins into a long neck. The underside is pale cream and hangs as a **large flap/pouch** (pelican-like, but with a sharpish profile and a **soft rounded rim** along its whole edge). A row of **small breathing holes** high on the underside of the neck. | "skin flap … or a skin bag like a pelican, but a bit sharp, soft edge along the entire thing"; "breathing holes high on the underside of the neck" |
| **Flap motion** | The flap has **its own small chain connected to the neck** so it swings a little. | "maybe this flap should have its own chain connected to the main body chain" |
| **Head** | A long **beaked serpent's head**: dark top, pale underside, pointed beak. **Two large protrusions on the upper beak** (teal, rising and curving back). This is the showpiece. | "almost like a beaked serpent's head, with 2 large protrusions on the upper beak"; "make the head really nice" |
| **Tail** | **Very long and large**, teal like the wings, **flattened side to side**: its cross-section is a rounded "\|" (a tall blade with round edges). | "very long and quite large … cross-section would look like a rounded \|" |
| **Hind legs** | One pair, slim and dark, dragon-like, with clawed feet, under the rear of the trunk. | "dragon like legs" |

### What it does

- Walks around on its folded wings (wrists as the front feet) and hind legs.
- Flies. **In flight the whole body bobs with each wingbeat and the bob travels down the body chain**, like the
  Winged Serpent ("quite good at this"), so it looks natural. The head stays steadier than the shoulders.
- **In flight the tail twists and turns** on its own, a slow travelling roll and curl. It is decoration: the tail does
  **not** visibly steer or change the flight.
- Takes off from the ground and lands back on it (it must reach every flight phase the kit checks: wing-walk, launch,
  beat, glide, flare, touchdown).

## 2. Goals, non-goals, anti-goals

**Goals.** Every feature in §1 present and recognisable; the side silhouette on the ground matches the reference;
it walks, flies with a visible travelling bob, twists its tail in the air, lands; the six new parts are general kit
parts; all 14 kit checks green with **no** `kKnown` entry for the Apex; zero GC per frame; sizes from `sizeScale`.

**Non-goals.** No new behaviour or hunting AI (it may keep the shipped flight behaviours, §5). No sound, no new
shading model (colours through the existing look modules and `Layers` rows / named kinds). No change to any other
species' look or numbers.

**Anti-goals (a failure even if every test passes):**
- **It reads as a pterosaur.** No single long wing finger with a thin membrane, no pteroid / propatagium, no crested
  bony pterosaur skull, no thin bird-like body on stilt arms, no knuckle-walking on a short folded hand under the
  chest. The folded wing is a tall *blade* rising high above the back; the open wing is a thick manta-like sail.
- **Anything from the deleted Apex comes back**: SailWing, SerpentNeck, CasqueHead, its generator, its numbers.
- The bob is invisible (the old Apex had kLift 0.75 and airLevel 0.8, which flattened it).
- The tail visibly drives the flight, or the tail just hangs straight in the air.
- The head is a plain cone or capsule.

## 3. Constraints (from the project)

- Creature-kit rules: `.claude/skills/creature-kit/SKILL.md` and `references/` — author at scale 1 in metres; lengths
  x s, times x sqrt s; zero GC per frame; main thread; never edit core files (`CreatureSim`, `CreatureLegs`, mesh
  builders, renderer) for one species; generic behaviour in a shared system enters as a data flag, off by default, with
  every shipped species bit-identical (goldens untouched). **This applies to the flight and mesh code too** (my call,
  resolving a builder question): no species yet combines a custom chain body (`ISpineChainBody`) with the shared wing
  flight; where `CreatureWings` / `WingedMeshBuilder` / compose assume `SpineBody` fields, the builder may add opt-in
  data flags or read the body through `ISpineChainBody`, off by default, every other species bit-identical. New part types `MeshOrder` 100; never take a new global
  material id (use named kinds); `[Param]` on every field; catalogue regenerated.
- The user judges the look in Unity (memory: no render-iteration loop for taste; offline renders are fine as a
  sanity check for placement, clipping and gross silhouette).
- Unity MCP: verify the instance is `MarchingCubes@…` before acting (CLAUDE.md). Terrain is untouched.

## 4. Decisions

### Decided by the user
1. Complete redesign; **delete the current Apex** and reuse none of it.
2. Every anatomical part is new. Parts are reusable building blocks for future creatures.
3. Ground: walks on folded wings + hind legs. Air: flies with the Winged-Serpent-style travelling bob.
4. Tail twists and turns in the air, cosmetically.
5. Throat flap gets its own chain connected to the neck.
6. Wing root: from the shoulder, following the flank part of the way toward the hips (adjustable up to the hips).
   Wings are soft and fleshy, not planes.
7. The beak protrusions are two large ones on the upper beak, as described (the image is too small to show them).

### My calls (flag any you disagree with)
- **"New parts" means new anatomy, not a new physics engine.** The shared *systems* stay: `CreatureSim` (the spine
  chain), `CreatureLegs` (gait, two-bone IK), `CreatureFlight` / `CreatureWings` / `FlightModel` / `AirChain` (wingbeat
  as a step in the air, launch, landing, wing-walk), `FlightBrain`, the kit services and checks. They are the engine
  every creature runs on, and the bob the user praised *is* `FlightModel` + `AirChain`. Every *part* (shape, mesh, part
  runtime) is new.
- **The name stays "Apex"** (new asset, new GUID; the roster entry is repointed).
- **Size:** the largest flyer in the lab, at least the old Apex's size (scale ~4); the builder fixes the exact scale
  inside `FlightBrain.FitsAviary`.
- **Mouth closed at rest** (the reference shows a closed beak), opening on calls / strikes.
- **Colours** (sRGB, approximate from the image): dorsal maroon-plum `#4A1E33`; belly / throat / lower jaw cream
  `#D9CDB8`; wing fan and tail teal-green `#1F6B66` with paler lengthwise stripes `#5FA39A`; the wing's arm zone
  blends from body maroon into the teal; beak crests bright teal `#3FC0B0`; breathing holes and claws near-black.

## 5. The parts

Six new part types and one new runtime overlay. Names are proposals; the builder may rename, but each stays generic.
Each gets a test class (`Tests/EditMode/Creature<Name>Tests.cs`) with its invariants and a RED proof that each test
bites (kit rule).

### 5.1 `KeelBody` — the trunk and tail (Body part, `ISpineChainBody`)
Replaces `SpineBody` for this species (SpineBody cannot have a non-elliptical section; `RayBody` is the precedent for
a body that lays out the chain and draws its own mesh). Same chain data as SpineBody (joints from profile keys,
spacing, rigid head, clearance, bend limits), plus **section channels** along the body:
- `hump` height, `humpSharpness` and its place: a sharp dorsal ridge over the shoulders (a peak, not the broad sin²
  bump of Swell);
- `keel` depth, `keelSharpness`, `keelForward`: the sternum jutting forward and down from the chest;
- `flankMuscle`: the muscular shoulder/flank masses;
- `blade` (tail): the section goes from the trunk's oval to a **tall, narrow rounded blade** (a superellipse with
  height/width >= 3 on most of the tail, round top and bottom edges), tapering to a fine tip;
- a neck socket at the front (the chain part §5.3 roots there; the body does not draw a snout).
Normals from the surface (finite differences), dorsal / belly shading channel as the body's. Must survive the full
bend range (MaxBend, PoseSweep) without inverted triangles.

### 5.2 `FleshWing` — the meaty folding wing (`WingPart` subclass)
Flown, folded and walked by the shared flight system (beat, fold, launch, touchdown, wing-walk on the wrist).
Its own mesh and its own bones/runtime:
- **Thick**: a real airfoil with volume, thickest along the arm and the root, a round leading edge, thinning toward
  the trailing edge and tip. Not a sheet.
- **Root: a middle ground (user, 2026-10-20).** From the shoulder the wing's root follows the body back along the
  flank for a stretch — default about half to two-thirds of the way from the shoulder to the hips — then ends, leaving
  the rear flank and the hind legs free. "Or maybe it does [go to the hip], not sure": the rear attach is a parameter
  (`membraneRearJoint` + flank patches following the body's curve) that can run anywhere from the shoulder to the hips
  without other changes, so the user can try both in the Inspector. The root blends smoothly into the body (no gap,
  no seam line).
- **Soft, not a plane (user, 2026-10-20).** The wing is a soft, fleshy volume: rounded everywhere (no hard sheet
  edges), with subtle swells over the arm and the root muscles, a soft rounded rim along the trailing edge, a little
  sag and billow, and soft motion (the chains below). Seen edge-on it must read as flesh with thickness, never as a
  flat card. Test: at mid-span the wing's thickness is at least a set fraction of its chord there, and there are no
  zero-thickness edges.
- **Fleshy arm**: the arm is muscle inside the wing's leading edge (maroon, blending into the teal), not a visible
  bone tube. A blunt callused **wrist pad** is the foot it walks on (`thumbPlant` keeps the drawn contact planted).
- **Lengthwise stripes**: shallow ridges and colour stripes running along the rays (along the blade when folded).
- **Smooth trailing edge** (manta), no scallops, no single long finger.
- **Chain motion** as on the manta: the outer wing lags and whips at the stroke's turn, the trailing edge feathers and
  billows (new runtime; `AngleChain` is a fine utility to use).
- **Ground pose = the reference's blade**: wrist on the ground ahead of the hind feet, the fan folded back up along
  the forearm (shared `groundTallStance`, `groundLiftDeg`, `fanRearRollsWithFan`), its tips standing **well above
  the back** (test: the blade tip is higher above the ground than the hump by at least 0.5 x hump height, and behind
  the shoulder). Meaty fold: the thick layers must not interpenetrate or invert when folded (bind part-folded if
  needed, as the shared system allows).
Fold geometry is fragile (recorded lessons: two-ray zones turn inside out, mirrored bones in launch). Scan the fold
numbers over a grid with `KitChecks.MaxBendProblem` and take the middle of a passing region.

### 5.3 `ArcNeck` — the long neck (chain part)
Its own bones rooted on the trunk's front joint; the head rides its last bone. Carriage on the ground (raised,
reference angle), steady head in flight (the bob is filtered from the head), call / glance / strike aim as a long neck
does. Its own mesh: thins out of the chest, dark top, pale underside, and a **row of breathing holes** (recessed pits
with a soft rim, count and size as params) high on the underside, near the head end. The builder may build the carriage
on `LongNeck`'s runtime if it fits (it is a motion system); the mesh and part are new.

### 5.4 `Dewlap` — the throat flap with its own chain (part with runtime)
Hangs under the neck from the chest root to near the jaw: a pale skin flap/pouch, deepest at mid-neck, a sharpish
profile and a **thickened soft rim** along its whole edge. It follows a neck it names (like a head follows a neck;
listed after it) and has **its own chain** (2–4 links hanging down, along a few neck stations): a damped swing that
lags the neck's motion, the wingbeat bob and turns, with gravity and limits so it never passes through the neck or
chest. Skinned between the neck bones and its own bones. Tests: it swings (measurable lag after a neck move), settles
without jitter, never enters the neck/chest, Froude-scaled.

### 5.5 `ProngBeakHead` — the beaked serpent head (head part)
The showpiece. Built from SDF solids (`SculptMesher` is shared infrastructure). A long, smooth, slightly flattened
serpent skull flowing into a pointed beak; brow over small eyes set well back; pale lower jaw and underside; a closed
mouth line along the side. **Two large prongs on the upper beak**, one each side, rising from the beak's top and
curving back, keratin-teal, as tall as about half the head's depth or more (the image: very prominent). Jaw on its own
bone (closed at rest, opens on calls / strikes). Parametric: skull length/width/depth, beak length and hook, prong
count (1–3 pairs), length, rake, curl, base width. Its own runtime may reuse the shared jaw / eye conventions.
Tests: closed solids, prongs symmetric, jaw opens and closes, no inverted triangle through the jaw's range.

### 5.6 `DrakeLeg` — the hind leg (limb part)
A two-bone limb for `CreatureLegs` (it produces the same leg spec a Leg2Bone does) with its own mesh: a muscular haunch
blended into the trunk, a slim shin, a raised hock and long metatarsus, three or four toes with dark curved talons.
Slim and dark as in the image. Ground contact checks as any leg (Gait).

### 5.7 `TailFlourish` — the tail's twist in the air (Late part runtime, an overlay)
Re-poses the trunk's tail bones after the sim, in the air only (eased in by the flight's air weight, out on
touchdown): a slow **travelling roll** (the blade turns about its own axis, growing toward the tip) plus a **lazy
curl** (a sideways/vertical S that travels down the tail), with per-individual seed and Froude timing. A pose over the
sim, like the Tuck: **the flight is untouched** (test: the flight model's path and the girdle are bit-identical with
and without the overlay). On the ground the tail follows the chain as normal. Tests: roll range along the tail >= 60
deg at the tip in sustained flight, no inverted triangles (PoseSweep covers it), zero GC.

### Flight: the bob
Tune the `Fly` module for the Winged Serpent's character: low glide lift so the beats carry the body, `airLevel` low so
the trunk follows the path, a visible travelling wave (`AirChain`). Target (measured in a test, cruise, steady flight):
girdle bob peak-to-peak >= 3 % of the body length; the mid-tail moves with a visible lag behind the girdle; the head's
bob <= 1/3 of the girdle's. If the plain AirChain cannot reach it at this size, the builder may use the shared
`AirTwist` bob terms (`girdleBob`, `bobTail`) — data only.

## 6. Species asset

`Config/Creatures/Apex.asset` (new GUID) from a generator `Tools~/SpeciesGen/Apex.py` (kit services, `kityaml`).
Parts: `KeelBody`, wing arm (Leg2Bone, mirrored; its own mesh hidden by the wing as wing arms are today), `FleshWing`
(mirrored), `DrakeLeg` (mirrored), `ArcNeck`, `Dewlap`, `ProngBeakHead`, `Eyes`, `TailFlourish`. Modules: `Walk`,
`Fly`, `QuadLaunch` and the shared flight behaviours (`Wander`, `FlightExcursion`; `SkyHunt` optional — keep only if it
reaches every phase and lands, with `handBack`). Looks: `Skin` (maroon dorsal, cream belly), `Membrane` (teal),
`Layers` rows / named kinds for the prongs, the wrist pad and the stripes. Lab: the existing Aviary roster entry,
repointed to the new GUID.

## 7. Deletion (first build step)

Remove the old Apex completely: `Config/Creatures/Apex.asset` (+ .meta), `Tools~/SpeciesGen/Apex.py`,
`Scripts/Creatures/Kit/SailWing.cs`, `SerpentNeck.cs`, `CasqueHead.cs` (+ .meta; no other species uses them),
`Tests/EditMode/CreatureApexTests.cs` (+ .meta); their mentions in comments (`WingSpec.cs`, `BeakHead.cs`), the
catalogue (regenerate), the skill docs' examples (`creature-kit` SKILL.md uses Apex in its command examples: point
them at the new Apex). Findings and lessons in the skill docs that came from the old Apex are **kept and reworded** so
they no longer name it (they are general fold lessons this build relies on); the skill docs live in the parent repo, a
second commit there. Keep the shared
opt-in flags (`thumbPlant`, `fanRearRollsWithFan`, `approachBleedsSpeed`, `SkyHunt.handBack`): they are generic and
the new Apex uses them. `Swell` stays (Delver, KomodoDragon, SkyDragon use it). Every other species bit-identical.

## 8. Done means

- All features in §1 present; the user confirms the look in Unity against the reference.
- The six parts + overlay have their tests (with REDs); `creature_kit.py check Apex` green on all 14 checks, no
  `kKnown` entry; full harness suite green; `unity-compile`, `compile_check.py`; Unity once (`CreatureKitTests`, the new
  part tests); catalogue fresh.
- Shape tests that pin the reference's key reads: folded blade tip above the hump and behind the shoulder; hump is the
  trunk's highest dorsal point and sharp; keel below and ahead of the chest; tail section height/width >= 3 on its
  middle; prongs present and symmetric; dewlap below the neck and never inside it; the bob targets of §5.
- A side-view offline render of the ground pose placed next to the reference image as a silhouette sanity check
  (not a look-tuning loop).
- Hand-off note: the aviary, play-mode setup, what to look at per part (blade height, hump, keel, flap swing, prongs,
  tail twist, bob), and the 0.9x / 1.1x individuals.

## 9. Left to the builder

Part names, exact parameter sets and defaults, bone counts, mesh resolution, the joint count and spacing, the exact
scale, how `ArcNeck`'s carriage is implemented, the dewlap's chain topology, the tuning of the fold and the flight
numbers within the targets above, and the order of work (deletion first, species last).

## 10. Risks

- **Thick wing folding**: two-ray skinning of a volume is harder than of a sheet; the fold may invert or
  interpenetrate. Mitigation: bind part-folded, thickness offsets along zone normals, grid scans, PoseSweep.
- **Tall blade vs pole**: one arm pole serves ground and air; a high elbow shaped the Hexadrake's inverted launch blend.
- **Bob at scale ~4**: slow Froude beats weaken the visible bob; may need AirTwist's bob terms.
- **Tail overlay vs bounds**: the twisting tail must stay inside the renderer's culling bounds (check 6).
- **Perf**: more parts and a dewlap chain; stay inside the per-species budget (`PerfBudgetMs`), mesh build < 5 ms
  (SDF head: use the mesher's cache).
