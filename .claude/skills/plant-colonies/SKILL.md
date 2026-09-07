---
name: plant-colonies
description: How vegetation is PLACED in this repo — per-biome flora lists, a cover mask for glades and thickets, and colony grammars (2D L-systems walked over the ground) that put plants in groves, veins, fairy rings and thickets with open ground between, plus a spacing rule; and the offline simulator that renders a placement map from the real rewriter in seconds without the Editor. Use for "plants look random/cluttered", "make stands/clusters/glades", "which plants belong in this biome", "add a species to a biome", "plants next to plants", "the desert should be sparser", any edit to Biome.flora, Biome.colony, coverScale/Threshold, PlantSpecies.symbol/minSpacing, and before touching PlantScatter's colony path. The plant SHAPES are the crooked-branches skill; the draw/LOD/impostor side is vegetation-scatter.
---

# Plant colonies

Uniform scatter inside a 24 m plot has no structure below the plot and none
above it, and it looked like noise. Placement here is three layers, all pure
functions of (world seed, plot id), so nothing depends on the viewer:

```
Biome.flora  (species: prototypes, letter, spacing, filters, distances)
Biome.colony (2D L-system: letters at positions)  ─┐
Biome.cover* (glade/thicket noise)                 ├─▶ PlantScatter.BuildPlot ─▶ instances
PlantSpecies.minSpacing                            ┘
```

1. **Cover mask**: world-anchored fbm at `coverScale` (120–180 m), thresholded
   at `coverThreshold` with a `coverSoftness` edge. Gates every candidate of
   the biome before the ground search. Glades and thickets cross plot edges
   because the noise is world space; on a globe it samples the sphere
   position, never the height.
2. **Colony**: each plot seeds one L-system per colony source (the biome's,
   and the PlantWorld's for everywhere species) with `colonyChance`, from the
   plot hash. The turtle walks the ground plane (heading +Z, up +Y): `+ -`
   yaw, `f` moves, `[ ]` branch, every other letter is a species marker whose
   parameter is a scale multiplier. A plot also walks its EIGHT neighbours'
   colonies and keeps the markers that land inside it, so a stand across a
   plot edge is whole from both sides (the Worley trick). Letter → species
   through `PlantSpecies.symbol`; several species may share a letter and the
   marker picks one at random.
3. **Spacing**: candidates are taken largest `minSpacing` first and one is
   dropped when closer to an accepted plant than the SMALLER of the two
   spacings. Two trees keep a tree's distance; moss may sit at a tree's foot.
   Affinity is the grammar's job, exclusion is this rule.

Where a biome has a colony grammar it is the only thing placing that biome's
plants and the rarity presets are ignored; the uniform path is a fallback for
a biome without one.

## Writing a colony grammar

Read `references/colony-grammars.md` first: the five grammars in the world
with their letter tables and settings. The pattern:

```
#iterations: 22
#axiom: X
X -> +(rand(360)) f(rand(0,4)) K          // face anywhere, start off-centre
K : 0.44 -> V(rand(3,5))                  // grove
K : 0.22 -> W(rand(12,18), rand(1.5,3))   // vein
K : 0.16 -> C(rand(6,10))                 // thicket
K : 0.04 -> H                             // hero (landmark)
K : 0.06 -> f(0)                          // nothing
```

- **Kinds**, each a small rule: *grove* = chain of anchor trees 9–16 m apart,
  each `[ +(rand(360)) f(r) letter ]` satellites; *vein* = `W(n,l)` that yaws
  ±45 and steps `l`, dropping ground cover beside it; *ring* = `O(n,t,r)` with
  `+(360/t*n + rand(-10,10)) f(r)`; *thicket* = n branches of `f(rand(1.5,5))`;
  *hero* = one landmark letter with satellites 8–20 m out; *pairs*, *lone
  giants*, *dune lines* likewise. Mix by probability at `K`.
- **Only `+ - f [ ]` and letters.** `F` draws (harmless but wasteful); `& ^ / \
  $ !` leave the plane and the simulator warns. A species letter is never
  `F G f g`. Rule names and species letters must not collide: uppercase rules
  (`K V W C H`), lowercase species, capitals for landmarks that no rule uses.
- **Counts**: mean 8–27 markers per colony; with the mask taking ~45 % and
  spacing ~5–10 %, that is 0.6 (desert) to 4 (dolomite) plants per plot.
  Hero kinds at 2–4 % of colonies; at 5–15 % it was a 40k-triangle landmark
  every 100 m.
- **Iterations** = the deepest chain: `X → K → V(5) → S(5) → B` is 1+1+5+5+1;
  a vein `W(18)` is 18 more than its prefix. The simulator checks termination
  by deriving two extra generations.
- **Plausibility**: a biome lists only what could live there — succulents,
  palms at oases and dry giants in the desert; rock and dead-wood plants on
  canyon ledges (with `minUpness` ~0.55 so they take slopes); wet things
  (horsetail, crozier, reeds) in dolomite and frost. The desert seeds fewer
  colonies (0.3) and more glade.

## Workflow

1. Edit the grammar text and the letter table (`scripts/colony_assets.py`
   writes a grammar asset and a biome's flora list with letters, spacings,
   colony reference and cover settings; see its docstring).
2. Simulate before the Editor:
   ```bash
   python .claude/skills/plant-colonies/scripts/colony_sim.py --biome DolomiteBiome --out map.png
   python .claude/skills/plant-colonies/scripts/colony_sim.py --grammar my.lsys --letters "T:4,m:0.8" --chance 0.45
   ```
   It compiles `ColonySim.cs` against `Library/ScriptAssemblies/TerrainGen.LSystem.dll`
   (the real parser and rewriter) with a 2D turtle, runs 60 seeds for
   termination, marker counts, reach and unmapped letters, then a 14×14 plot
   grid with the neighbour walk, mask and spacing, and renders a map. Look at
   the map with the Read tool: groves should be clumps, veins lines, rings
   rings, and there should be empty bands. Its noise is a stand-in for
   `TerrainNoise.Fbm`, so the glade share in the Editor differs by ±10–20 %.
3. Editor: `refresh_unity`, then drive `PlantScatter.Update` by reflection
   with a temporary eye on the planet surface (the edit-mode loop is idle
   while unfocused) and count instances per species; the Frost/Desert points
   must show their own lists dominating. Then play mode from the spawn.
4. Record what changed in `references/calibration.md` if a number failed.

## Debug checklist

| Symptom | Cause |
|---|---|
| a letter places nothing | not in the biome's flora `symbol`s, or it is `F G f g` |
| plants in a straight fan | `+` without `rand()`; or the axiom lacks `+(rand(360))` |
| moss never near trees | spacing used the larger radius; it must be the smaller |
| everything is glade | `coverThreshold` too high for the noise range (0.05–0.12 is half-open) |
| landmarks every 100 m | hero kind above 4 %, or landmark spacing under 40 m |
| stands cut at plot edges | neighbour walk missing, or a rule's reach > one plot (keep < 70 m) |
| grammar never terminates | a counting rule without its `n <= 0` production; iterations too low |
| same colony in every plot | seed not from the plot hash |
