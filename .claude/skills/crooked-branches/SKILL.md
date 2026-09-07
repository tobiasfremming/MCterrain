---
name: crooked-branches
description: The baseline recipe for authoring plant grammars in this repo whose limbs look alive — crooked, gnarled, lumpy, sweeping — instead of smooth cones and pin-cushion forks; and the full workflow around it (concept → architecture → grammar + profile → eight-seed check → lab render → iterate). Use for any "make this plant", "the branches look too smooth/regular", "match this concept art", "more fractal/intricate", "why does every seed lean the same way", or "add laterals along the limb" request, and read it before writing any new tree, shrub, coral or pod-bearing grammar. Built from the Population Zero pod tree, which is the reference implementation.
---

# Crooked branches

A branch that looks alive is a **random walk with a bias**, not a curve. The
sweep of a limb comes from a small pitch toward the sky on every segment; the
life comes from every segment also being a kink of uneven length and lumpy
width, with an occasional sharp bend in a random direction. Get those two
things right and the tree reads as gnarled at any distance. Get only the first
and it reads as a bent pipe; get only the second and it reads as noise.

The reference implementation is the pod tree in `references/pod-tree.md`. Its
grammar is the baseline: copy its limb rule and change the numbers before
inventing a new one. `references/limb-recipes.md` has every rule fragment used
in the lab so far, each with the numbers that worked.

Read `lsystem-grammars` first for the engine's syntax and the ten grammar
rules; this skill is what comes after those.

## The limb rule

One rule shape does almost everything. Carry five parameters:
`L(k, l, w, u, i)` = segments left, base length, width, rise per segment,
segments grown so far.

```
L(k,l,w,u,i) : k > 0 : 0.75 -> !(w*rand(0.85,1.2)) F(l*rand(0.6,1.4)) &(rand(-22,22)) +(rand(-22,22)) /(rand(-40,40)) $ ^(u*rand(0.3,1.9)) S(i, w) L(k-1, l*0.97, w*0.95, u, i+1)
L(k,l,w,u,i) : k > 0 : 0.25 -> !(w*rand(0.9,1.25))  F(l*rand(0.5,0.9)) /(rand(360)) &(rand(20,40))                  $ ^(u*rand(0.5,1.5)) S(i, w) L(k-1, l*0.97, w*0.95, u, i+1)
L(k,l,w,u,i) : k <= 0 -> <tip>
```

Read it left to right; every term is a deliberate choice:

| term | what it does | if you drop it |
|---|---|---|
| `!(w*rand(0.85,1.2))` | lumpy width, bumps and waists | a tapered cone |
| `F(l*rand(0.6,1.4))` | uneven segment length | evenly spaced kinks read as a chain |
| `&(rand(-22,22)) +(rand(-22,22))` | the kink: pitch and yaw in a random direction | a smooth arc |
| `/(rand(-40,40))` | roll, so the next kink is in a new plane | kinks in one plane, a zigzag |
| `$ ^(u*rand(0.3,1.9))` | roll upright, then rise toward WORLD up by an uneven share of u | no sweep, or a metronome sweep |
| the 0.25 variant | one segment in four takes a 20..40° bend in a random direction | the walk is too polite |
| `S(i, w)` | the hook for laterals (see below) | nothing sprouts along the limb |
| `w*0.95`, `l*0.97` | taper and shortening per segment | limbs that end as thick as they start |

`$` before `^` is what makes the rise point at the sky regardless of where the
kinks have turned the heading. Without `$`, `^` pitches about the limb's own
axis and the limb corkscrews.

## Launch, dip, fork, sweep

- **Launch angle** decides the silhouette. `&(rand(88,108))` from vertical
  gives the concept's droop-then-sweep: limbs leave level or slightly dipping,
  then the rise pulls them up. At 95..125 they lie on the ground before rising
  (it happened; the trunk was too short). Pair a deep dip with a taller trunk.
- **Rise per segment** `u` = 7..10° with 11..14 segments turns a horizontal
  launch into a vertical end. Total rise ≈ launch angle; check the end heading
  is near vertical if pods or tufts sit there.
- **Fork once, part-way**, by letting `k` cross a value: `k > 5.5 && k <= 6.5`
  fires exactly once because `k` decrements by 1 from a random start. Both
  halves get `u*1.1` so they rise a little faster after the split. Forking at
  every segment is what makes a broadleaf tree; the concept trees fork once.
- **Trunk**: three short kinked segments with different widths
  (`!(rand(0.42,0.55)) F(..) &(rand(-15,15)) /(rand(360)) !(rand(0.4,0.6)) ...`).
  A single straight `F` under crooked limbs looks like a lamp post.

## Laterals along the limb

Things that sprout from the side of a limb (pods, cones, tufts, fruit) go
through a hook rule that runs every segment and decides by chance and by age:

```
S(i,w) : i >= 3 : 0.3 -> [ +(rand(35,60)) /(rand(-30,30)) ^(rand(10,30)) P(w*0.5, rand(1.1,1.5), 26) ]
S(i,w) : i >= 3 : 0.3 -> [ -(rand(35,60)) /(rand(-30,30)) ^(rand(10,30)) P(w*0.5, rand(1.1,1.5), 26) ]
S(i,w) : i >= 3 : 0.4 -> $
S(i,w) : i < 3  -> $
```

`i >= 3` keeps the first segments bare; the two 0.3 rules pick a side; the
0.4 rule is "nothing this segment". This is the knob for density and for
triangle budget: the pod tree went from 15 to 120 pods by adding this hook.

Whatever sprouts must **re-find vertical on its own**, because the limb's
heading at that point is anyone's guess: `P(w,z,r) -> F(0.22) $ ^(r) F(0.22)
$ ^(r) ...` with `r` = 26 for laterals (four steps recover ~100°) and 8 for
limb ends (already near vertical; more would overshoot and tip the pod).

## Per-seed variation and the lean trap

Draw the big numbers once in the first rule and thread them through the
parameters: limb count, launch angle, segment count, rise, shrink. `#define`
is for what never varies. Size `#iterations` for the *maximum* of every random
count, then check eight seeds (`scripts/lab_check.cs`).

**Start every grammar with `/(rand(360))`.** The turtle's initial frame is the
same for every seed, so the first pitch of every plant leans the same world
direction otherwise. Every plant in this repo leaned the same way until this
was added.

## Parts on crooked limbs

- A part's local frame is the turtle's: +Z heading, +Y up. Capsules, cones,
  cylinders are built along +Y, so `eulerOffset` x=90 (`ALONG` in the
  generator) lays them along the stem, x=-90 (`AGAINST`) points them back.
- Compose weird shapes from stacked primitives with small bends between them:
  the pod is neck, three capsules each `&(rand(3,8))` off the last and
  widening, a ring, an eye. Nothing looks moulded.
- Colour gradients along a limb: the last generations draw coloured
  cylinder parts instead of `F` (`f(l*0.5) Z(l) f(l*0.5)`), see the coral
  shrub recipe. One grammar, several profiles = several colourways.
- Needle cards (quads, 2 tris) for the last level of tufts; cubes (12 tris)
  for beads and knobs; spheres only where they are big enough to be seen.
  A sphere at every tip cost 54k triangles once.

## Workflow

1. Look at the concept and name the **architecture** in words before any
   rule: trunk height, where limbs launch and at what angle, do they dip,
   how many forks, what sprouts where, what the tips carry.
2. Write the grammar and profile with `scripts/plant_assets.py` (fixed GUIDs
   per asset, so regenerating never orphans a scene reference). Grammar
   comment block: what it is, the per-seed variation, the iteration count
   arithmetic.
3. Refresh, then run `scripts/lab_check.cs` through `execute_code`: parse
   errors, termination on eight seeds, unmapped symbols, height and width
   spread, `minY` (parts under the ground), triangle range, **lean direction
   per seed** (should scatter around the compass).
4. Put it in `Assets/Scenes/FloraLab.unity` on a free stage row with a
   `PlantBuilder` (SingleMesh, seed override) and render it from eye level,
   from above, and as a strip of three seeds. Look at the renders with the
   Read tool; the numbers never caught "smooth", "fat", "confetti" or "lying
   on the ground".
5. Iterate one thing at a time and re-render. Three passes is normal.
6. Delete the screenshots you wrote under `Assets/Screenshots`, refresh.

If the user has a scene open and is in play mode, wait; then open the lab
additively, work with a camera whose `overrideSceneCullingMask` is the lab's,
save it and close it, and leave their scene alone. If the Editor is on a
different MCP port than this session, route through the workflow skill's
`mcpcall.py` with `UNITY_INSTANCE` pinned.

## Budgets that held

| plant | tris at LOD0 | note |
|---|---|---|
| pod tree, 76..136 pods | 39k..69k | hero; pods are four capsules each |
| coral shrub, 7 generations | 14k..36k | cube knobs; spheres doubled it |
| frond tower, 3-level fronds | 24k..36k | needle cards at the last level |
| oak, 10 generations, leaf clumps | 27k..73k | hero |
| anything scattered | ≤ 20k | `PlantPrototypeBaker.kTriangleBudget` |

## Report

Name the architecture, the launch/rise/fork numbers, what sprouts where, the
eight-seed ranges (height, width, tips or pods, triangles), which renders were
looked at, and what was changed between passes and why.
