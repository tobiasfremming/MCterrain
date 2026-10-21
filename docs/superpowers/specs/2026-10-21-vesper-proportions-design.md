# Vesper, step 1 rev 2: proportions — design

Status: approved by the user in chat, 2026-10-21. Follows `2026-10-21-vesper-skeleton-design.md` (step 1, done and merged
into `feat/creature-integration`). Reference: `assets/2026-10-20-apex-reference-hires.jpg` (the user re-sent it with this
feedback). Submodule `Assets/TerrainGen`, branch `feat/vesper` (worktree `wt/vesper`).

## Why (the user's feedback from VesperLab)

"Great work with the skeleton, but": the spine rises smooth and uniform and not steep — the tail on the floor, low hips,
low shoulders, the head the highest point. In the picture the backside sits high, there is a hump, and then it is quite
flat to the head: a humpbacked build. The hips must be much higher, which changes the hind legs, and the last leg bone
(down to the foot) should be way longer. The wing arms' knuckles, which carry all the front weight when walking, should be
way more in front and a little further out on each side. The neck and head are not that long; the tail is really long.
The strides are too small — make them longer.

## Decided by the user

- **Shorter head and neck by closer joints, not fewer.** Same joint counts (head 4, neck 7); the joints sit closer
  together. This needs per-joint spacing on the spine chain, which today is one `spacing` everywhere.
- The profile below (heights, hump, flat neck), longer metatarsus, knuckles forward and out, longer tail, longer strides.

## Goals

1. **Per-joint spine spacing (shared, opt-in).** A spine body can give its segments different lengths, varying smoothly
   along the chain (no sudden jump between neighbours). Off by default; every shipped species bit-identical (goldens).
   Honoured everywhere Vesper's skeleton goes: the chain sim (walk, rest/bind, ground), flight (AirChain, CreatureFlight,
   CreatureWings, launch/touchdown/perch drape), legs/arms attachment, FlowBody's own joint<->arc mapping (the future
   skin), F3. A part that assumes a uniform chain and cannot honour it must refuse it in Validate, not silently misdraw.
2. **Vesper's new build** (metres at scale 1; SCALE stays 4), all in `Tools~/SpeciesGen/Vesper.py`:

   | Part | Joints | Spacing | Length |
   |---|---|---|---|
   | Head | 4 | 0.05 | ~0.2 |
   | Neck | 7 | 0.06 | ~0.42 |
   | Trunk (shoulder -> hump -> hips) | 6 | 0.1 | ~0.6 |
   | Tail | 21 | 0.1 | ~2.2 |

   - Standing heights: tail tip ~0.08 (reaches the ground), hips **0.80** (was 0.43), the **hump the highest point ~0.92**
     over the back just behind the shoulders, shoulders **0.85** (was 0.52), neck to head nearly flat, head ~0.88 (not the
     peak).
   - Hind legs (DrakeLeg): thigh 0.24 -> 0.28, shin 0.26 -> 0.32, metatarsus (`ankleHeight`) 0.14 -> **0.30**.
   - Wing arms: the planted wrist/knuckles ~**0.45 in front of** the shoulder (was 0.22 behind) and ~0.35 out from the
     spine (was ~0.16); forearm 0.5 -> ~0.8, upper arm 0.2 -> 0.25 so it reaches the ground; the elbow up and back.
   - Folded fingers re-tuned to lie back along the longer forearm, tips standing up behind the shoulders, never crossing
     over the back (the existing separation test).
   - **Longer strides** on both arms and legs (step threshold, duration and lift grow with the longer limbs); the gait
     stays stable (no foot sliding, Gait/Layout kit checks).
3. Flight, launch, landing, perching and the M-menu commands still work on the new body: the existing Vesper and
   CommandBrain tests pass (constants retuned only with a stated reason), plus a new test pinning the profile (hump is the
   peak, hips high, neck-to-head near flat, tail reaches the ground, head+neck shorter by closer joints).

## Non-goals

Skin, meshes, step 2 bones, changing any other species, using the new spacing anywhere but Vesper.

## Anti-goals

A shipped species changing by a bit; a head/neck shortened by deleting joints; a visible kink where the spacing changes;
a hump made by a mesh channel instead of the bones.

## Constraints

Creature-kit rules (opt-in flags, goldens, zero GC per frame, RED proofs, Froude sizing). The user judges the look in
Unity; offline: tests + kit checks. Unity MCP port 8040, verify `MarchingCubes@...` 6000.2.6f2.

## Left to the builder

The representation of per-joint spacing (a FlowBody profile channel compiled to per-segment lengths on the species is the
expected shape), how each consumer reads it, the exact stride numbers, finger fold angles, any flight constant needed to
keep the tests' margins.

## Addendum: the landing flare (user, 2026-10-21: "make the wings flare when landing")

Today the landing's Flare mode (CreatureFlight) only brakes with slow high-drag strokes; the wings do not *look*
flared. Wanted: as Vesper comes in to land, the wings open wide and pitch up into an air brake, like a bird or a bat
landing — fingers fanned to their widest, the wing swept forward and high, the membrane span (the finger chains) cupped
by the air — held through the last moment before touchdown, then folding onto the walk after the feet are down.
- Opt-in (a WingSpec/FlightSpec flag, off by default; shipped flyers bit-identical); on for Vesper.
- Smooth in and out (no pop: the wing blends into the flare over the flare's start and out of it over the touchdown).
- Works for open-ground and rock-perch landings and for a go-around (the flare abandoned, back to beating).
- The fingers' air flex reads the flare (they billow/cup harder at the high angle).
Left to the builder: blend times, the exact pose numbers, whether a last braking beat or a held flare.
