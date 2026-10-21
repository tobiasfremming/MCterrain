# Vesper, step 1: the skeleton — design

Status: design, 2026-10-21. A new creature, **Vesper**, the same animal as the Apex (references:
`docs/superpowers/specs/assets/2026-10-20-apex-*`), built with a new, collaborative, skeleton-first workflow. The Apex
stays as it is, as a reference. Submodule `Assets/TerrainGen` + the parent repo (scene), a new branch off
`feat/creature-integration`.

## Why

The user found the Apex stiff and not organic. The first lizards felt authentic because they were "basically a
shrinkwrapped skeleton": one chain, one skin pulled tight around it, so every motion of the skeleton shows in the
surface. The Apex was assembled from many separately built pieces (sculpted head solid, separate club, flap with its own
rules, shape tweaks on top) that do not move as one body.

**New rule: the skeleton is the creature.** Every visible feature will come from a bone or chain under it. The work goes
in steps, each judged by the user in Unity before the next:
1. **The skeleton** (this design): spine, head joints, legs, wing arms with finger chains, motion, a command menu.
2. Extra bones: claws, jaws, crests/protrusions, the throat pouch.
3. Skin: shrink-wrap the skeleton (the lizards' technique as the starting point; the user also wants to sculpt).
4. Facial features.

Only step 1 is designed here.

## Goals (step 1)

- **A dedicated scene** `Assets/Scenes/VesperLab.unity`: flat ground, open sky, camera, light, a few perch rocks/posts.
  One Vesper. No terrain streaming, no lab arc.
- **Skeleton only, no skin.** Vesper draws no mesh in this step. The skeleton is shown by the existing F3 debug view,
  extended so it also draws everything Vesper has (finger chains, head joints, claws), not only spine and legs. F3 can be
  switched off later when skin exists. Joint sizes (the existing per-joint ellipses) show proportions.
- **The skeleton:**
  - **Spine:** ONE chain from the head's tip to the tail's tip (head, neck, trunk, tail).
  - **Head:** a few joints at the front of the same chain, constrained stiff (not one rigid block, not a separate part).
  - **Two hind legs** (dragon-like, digitigrade proportions from the references).
  - **Two wing arms** (short upper arm, very long forearm, as the anatomy reference `2026-10-20-apex-anatomy.jpg`).
  - **Wing fingers:** per wing, **4 long fingers**, each a **jointed chain**; the wing surface will later be drawn
    *between* the fingers, so the fingers' length and spread define the wing's shape. **Plus a 5th digit: a small claw
    pointing forward** (a thumb).
  - Finger chains **bend slightly from the air in flight** (lag/flex with the beat, billow gliding) and **droop slightly
    under gravity on the ground** (folded). Folding the wing folds the fingers along the forearm; on the ground Vesper
    walks on the folded wings (the hand/claw end on the ground) and the hind legs.
- **Motion** from the existing shared systems (CreatureSim chain, CreatureLegs, CreatureFlight / CreatureWings /
  AirChain — the travelling bob the user likes), so Vesper walks on folded wings + hind legs, launches, flies with a
  visible bob, glides, lands, perches.
- **"M" menu:** pressing M in play mode opens an in-game menu to command Vesper; it carries out the command with proper
  transitions (e.g. "Walk" while flying makes it land, then walk). Commands: **Stand**, **Walk around**, **Walk to me**
  (to the camera's ground point), **Take off & fly**, **Circle**, **Land**, **Perch on a rock**. The menu shows what
  Vesper is doing now.

## Non-goals (step 1)

Skin, mesh, colours, head shape, jaws, crests, throat pouch, claws other than the wing thumb, sculpting, facial features,
the Creature Lab roster. No change to the Apex or any other species.

## Anti-goals

- Anything assembled from separate rigid solids or shape tweaks — step 1 is bones and chains only.
- Fingers as single straight rays (the old wing): each finger must visibly bend.
- A menu that teleports or snaps states: every command transitions through the creature's real motion.
- Breaking any shipped species (shared changes are opt-in flags, off by default, bit-identical).

## Decided by the user

Name Vesper (picked from the controller's proposal); new scene; skeleton first; F3 for the skeleton view; one spine
chain; head = multiple constrained joints; long finger chains forming the wing; a 5th small forward claw; fingers bend in
air and droop on the ground; M menu with behaviour commands and proper transitions; the Apex kept as reference.

## My calls (flag any you disagree with)

- Size and proportions start from the Apex (scale ~4; wing arm upper ≈ 0.4 × forearm), retuned by the user in Unity.
- The command menu uses the project's existing input style (old Input Manager, IMGUI like OctopusLab/GrassLab); it needs
  a small "manual" brain because the current flight brain is random and private.
- Vesper is a kit species asset (`Config/Creatures/Vesper.asset`) generated from `Tools~/SpeciesGen/Vesper.py`; it is
  not added to the Creature Lab roster in this step.
- Finger chains: a generic, reusable finger-chain mechanism (3D: air flex + gravity droop + bend limits), built for
  Vesper but usable by future wings; no mesh.
- Scene ground: `FlatGroundProbe`; perches: a few simple collider rocks/posts the flight system can land on.

## Constraints

Creature-kit rules (`.claude/skills/creature-kit/`): scale-1 authoring, size rules, zero GC per frame, main thread, no
edits to core systems for one species except opt-in flags (shipped species bit-identical), tests with RED proofs, the
user judges looks in Unity. Unity MCP: verify `MarchingCubes@…` on 6000.2.6f2 first; the server is on port 8040.

## Done means (step 1)

In `VesperLab.unity`, Play: Vesper's skeleton is visible with F3 (spine, head joints, legs, wing arms, 4 finger chains +
thumb claw per wing); M opens the menu; every command works and transitions naturally; fingers visibly flex in flight and
droop when folded on the ground; offline tests and the kit checks that apply to a mesh-less species pass; the user can
change the skeleton's numbers and see them.

## Left to the builder

Joint counts and spacing, finger segment counts, how the finger chains are simulated (reuse AngleChain / a PBD chain /
new), how the wing's flight system consumes the fingers, how F3 learns to draw part runtimes for Vesper, the menu's
layout, the scene's dressing.

## Builder-check answers (my calls unless marked)

- **Wings on the existing flight system.** The arm, the beat, the fold, launch/landing and the wing-walk (the wrist end
  planted by CreatureLegs as a foot) stay the flight system's (CreatureFlight / CreatureWings / WingSpec, as the Apex's
  FleshWing does); the existing aerodynamics (WingSpec area, lift, glide) are kept. The **fingers are new bone chains of
  Vesper's wing part**, rooted at the wrist and aimed by the flight system's finger directions (spread/fold), simulated on
  top: air flex and gravity droop, bend limits. The planted wrist always wins on the ground; droop acts only on the free
  finger chains. The thumb claw is a short rigid/2-joint digit pointing forward from the wrist.
- **Skeleton only, no skin.** If the renderer or compiler needs a mesh, add an opt-in "skeleton only" path (no draw) —
  off by default, every shipped species bit-identical. Kit checks: Validate, Layout (bones), Wander, Gait, Size, Gc, Perf,
  Lab apply; MeshTime, MaxBend, Bounds, PoseSweep, Group (mesh-based) are skipped for a skeleton-only species with a
  `SkipReason` "skeleton only" (they come back with the skin in step 3).
- **Joint sizes are authored now** (spine, limbs, fingers: a radius per joint) because they become skin radii later;
  F3 shows them.
- **Head:** the first 3–4 spine joints with tight bend limits (stiff but jointed), not the RigidHead block.
- **Command brain:** a new `ICreatureBrain` using CreatureFlight's public calls (Launch, SteerTo, Land incl. perch with a
  branch axis) and the sim's Halt; "Walk to me" and "Circle" are small new motion code in that brain; perches are the
  scene's rocks/posts (colliders the flight system's surface probe sees). FlightBrain is not refactored.
- **"Me"** = the scene's player/camera ground point; VesperLab gets the project's existing player/free camera controller
  (SimplePlayerController) or an orbit camera if that fits better (builder's call).
- **Tuning:** numbers live in `Config/Creatures/Vesper.asset` (editing it in play mode respawns Vesper, as for every
  species) and are regenerated from `Tools~/SpeciesGen/Vesper.py`.
- **Branch:** `feat/creature-integration` now contains all kit and Apex work (merged 2026-10-21); branch `feat/vesper`
  off it in a worktree outside `Assets/` (`wt/vesper`).
