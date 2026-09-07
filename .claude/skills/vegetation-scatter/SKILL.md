---
name: vegetation-scatter
description: Place and render procedural vegetation and props over generated terrain — deterministic world-anchored plots (flat grid or cube-sphere cells on a planet), flood-fill enumeration, Poisson/blue-noise spacing, slope/height/biome filters, GPU-instanced drawing, mesh LOD and baked impostor cards, and background plot building — using this project's PlantScatter, PlantWorld, PlantPrototypeSet and PlantPrototypeBaker. Use when plants, trees, rocks or debris must be scattered, when "plants look different depending on where I stand", flicker, pop, float, sink, or hitch the frame, when adding a species or tuning density and draw distance, or when adding a far LOD. Trigger for any "scatter", "instancing", "impostor", "billboard", "vegetation density" request in this repo.
---

# Vegetation scatter

The contract, learned by breaking it: **what grows where is a function of the
world and never of the viewer.** Placement, variant, scale and rotation depend
only on the plot id and the world seed. The eye decides *whether* a plant is
drawn and *which representation*; nothing else.

References, read on demand:

- `references/placement.md` — plot identity on flat worlds and planets, exact
  enumeration by flood fill, uniform density on a cube-sphere, ground finding,
  Poisson/blue-noise spacing, filters, and threading.
- `references/impostors.md` — LOD tiers, the impostor bake (atlas, card,
  shader), draw-call and triangle budgets, the render-target flip, and the
  pitfalls that cost a day.

## Architecture in this repo

```
PlantProfile + grammar ──bake──▶ PlantPrototypeSet   (N variants × 3 LODs + impostor atlas/cards)
Biome.flora (per-biome species: rarity, filters, distances) ──┐
PlantWorld.species (everywhere species) + world settings      ├──▶ PlantScatter ──▶ Graphics.RenderMeshInstanced
DensityField (ground) + BiomeDensityField (biome weights)     │      plots built on worker threads
MCChunkManager.target (the eye)                               ┘
```

Nothing is a GameObject. A forest is instance matrices grouped by
`(species, variant, lod)`, one draw call per group per submesh.

**Species live on biomes.** Each `Biome` asset carries a `flora` list of
`PlantSpecies`; `PlantWorld.species` is only for things that grow
everywhere. `PlantScatter` merges them into one table (world entries first,
then each biome's list in `BiomeWorld` order) and treats every entry as its
own species with its own draw batches. A biome species' candidate is
accepted with probability equal to that biome's weight at the candidate's
spot, from the same `ComputeWeights` / `ComputeWeights3D` the terrain blends
with, so flora and ground agree exactly and stands thin out across the
few-metre cross-fade. The acceptance number is drawn before the ground
search like every other per-candidate draw (rule 4), and the weight test
runs before the ground search because it is a hundred times cheaper.

`PlantRarity` presets fill `perPlot`/`plotChance` on validation: common
8 @ 0.85, uncommon 3 @ 0.5, rare 1 @ 0.25, landmark 1 @ 0.04 (and mesh LOD
off). Landmark is the tier for hero assets over the 20k triangle budget:
bake them with 3 variants, cull at 900 m, impostor from 150 m. The presets
only drive the uniform fallback; a biome with a colony grammar ignores them.

## Colonies: structure instead of uniform scatter

The authoring side (writing a colony grammar, letter tables, plausibility per
biome, the offline simulator) is the `plant-colonies` skill; this section is
the placement contract only.

Uniform scatter in a 24 m square has no structure below the plot and none
above it, and it looked like noise. Where a `Biome` (or the `PlantWorld`)
sets a `colony` grammar, placement is three layers, all still pure
functions of (world, plot id):

1. **Cover mask** (`coverScale`, `coverThreshold`, `coverSoftness` on the
   Biome): world-anchored fbm at ~140 m, thresholded with a soft edge, gates
   every candidate. Glades and thickets that run across plot edges, one
   noise sample per candidate, taken before the ground search.
2. **Colony grammar**: a 2D L-system (`+ - f [ ]` and markers only; no
   pitch, roll or `F`) walked in the ground plane once per plot with
   `colonyChance`, seeded from the plot hash. Markers are species letters
   (`PlantSpecies.symbol`, never `F G f g`), the parameter is a scale
   multiplier; several species may share a letter and the marker picks one.
   A plot also walks its eight neighbours' colonies and keeps the markers
   that land inside it, so a stand across a plot edge is whole from both
   sides. Grammars live in `Config/Flora/*ColonyGrammar.asset`; the
   generator with all five is the session's `gen_colonies.py` pattern:
   an axiom that picks a colony KIND by probability (grove / vein / ring /
   thicket / hero / nothing), each kind a small rule with `f(rand(a,b))`
   offsets. The offline simulator (`ColonySim.cs` against
   `TerrainGen.LSystem.dll` with a 2D turtle) renders a map of a 14x14 plot
   grid in seconds; use it before the Editor.
3. **Spacing** (`PlantSpecies.minSpacing`): candidates are taken largest
   spacing first and dropped when closer to an accepted plant than the
   SMALLER of the two spacings (the larger killed every moss-at-a-tree's-foot
   the grammars asked for). Trees 4 m, shrubs 1.8, ground cover 0.8,
   landmarks 40. Affinity is the grammar's job; exclusion is this.

Numbers from the simulator with the mask on: 1.5 (desert) to 3.2 (dolomite)
plants per plot against ~35 for the uniform version, roughly 45 % of
candidates lost to glades and 15 % to spacing. Hero kinds at 2–4 % of
colonies gave one landmark per ~250 m; at 5–15 % they were a landmark every
100 m, which is far too many 40k-triangle plants.

## Rules

1. **Plot identity is world-anchored.** Flat: `floor(x/size), floor(z/size)`.
   Planet: a cube-sphere cell `(face, u, v)`. Contents are a pure function of
   `(seed, plot id, PlantWorld)`; the RNG is `LRandom(plotHash, speciesIndex)`.
2. **Enumerate plots exactly.** Flood fill over plot adjacency from the eye's
   cell, accepting cells whose centre is within `radius + cellDiagonal`.
   Sampling a lattice of directions *misses cells* wherever cells are smaller
   than the lattice pitch (cube-sphere corners are half the size of centres),
   and which cells it misses moves with the eye: plants blinked in and out
   while walking. Simulate any new enumeration in Python against a dense
   reference before trusting it.
3. **Density is per unit area.** On a cube-sphere, scale the expected count by
   the cell's true area `R²·du·dv / (1+u²+v²)^1.5` over the nominal `size²`,
   with stochastic rounding. Otherwise corners are five times sparser.
4. **Draw every random number a candidate needs before its ground test**, so
   a rejected candidate never shifts the stream of the next one.
5. **Find the ground on the field the player stands on**: sample at LOD0's
   filter width, march adaptively (step by half the density value, min 0.25 m,
   max 24 m), bisect the last air/solid pair, take `-gradient` as the normal.
6. **No viewer-dependent transforms.** No scale-to-zero fade band (a 10 m tree
   at half height at 90 m that grows as you approach), no billboards that
   change size. Plants pop at `cullDistance`; make that far enough that the
   pop is a few pixels, or give the species an impostor.
7. **Build plots off the main thread**, on dedicated background `Thread`s
   with a bounded nearest-first queue. `Task.Run` for a long-lived blocking
   worker crashed the Editor (Mono threadpool monitor refcount bug). No Unity
   externs on workers: `Quaternion.Euler`, `Matrix4x4.TRS` are out; managed
   quaternion/matrix helpers are in `PlantScatter`.
8. **Invalidate by hashing the settings that feed placement** (seed, plot
   size, per-species density/filters/scale/lean/sink, prototype identity,
   and every biome's flora list plus the biome field's seed, region scale,
   sharpness and biases), never by `OnValidate` on the component — inspector
   touches would throw the forest away. Draw distances change nothing about
   placement and are not in the hash. The populated radius is raised at
   runtime above every species' cull distance, biome lists included, because
   `PlantWorld.OnValidate` cannot see them.
9. **Cull and LOD by true 3D distance to the eye; region membership by
   distance from the eye's vertical axis** (height ignored) so a player on a
   rise keeps the plants at their feet. Measure from the eye, not the planet
   centre, so numbers stay float-exact at R = 100 km.

## Tuning knobs (`Config/*Biome.asset` flora lists; `Config/Flora/DefaultPlantWorld.asset` for world settings)

| knob | effect |
|---|---|
| `plotSize` | 24 m; cube-sphere cells 14–30 m across a face |
| `perPlot`, `plotChance` | density and clumping; `plotChance < 1` makes stands |
| `minUpness`, `minHeight/maxHeight` | slope (cosine) and altitude filters |
| `scaleRange`, `leanDegrees`, `sink` | per-instance look; sink hides the base on slopes |
| `useLod`, `lod1/lod2Distance` | mesh LOD swaps (silhouette changes; keep far) |
| `impostorDistance` | card beyond this; trees 120 m, ground cover 70 m |
| `cullDistance` | trees 700 m, ground cover 220 m; `radius` follows the max automatically |
| `plotsBuiltPerFrame`, `workerThreads` (component) | queue depth and builders |

Measured on this machine at the spawn with four species: 9 k plots, ~4 k
drawn instances, ~130 draw calls, 3 ms/frame steady, 2 s cold fill with no
main-thread hitch. With 53 species over four biomes (2026-09-07): 16–23 k
drawn instances and ~680 draw calls at a point, and a ~950 m populated
radius (the landmarks' 900 m cull) of ~5 k plots that takes tens of seconds
to fill cold. Draw calls scale with species × variants × LODs present, so
rare species bake 4–6 variants and landmarks 3. The baked sets are
text-serialised: 53 sets came to 1.2 GB under `Config/Flora/Prototypes/`
(gitignored); the lattice fan alone is 100 MB. Keep hero bakes to 3
variants and consider dropping LOD1/2 for anything that only ever draws as
a landmark.

## Verification that counts

- **Round trip**: record every drawn plant within 80 m, teleport 300 m away,
  come back with the cache cleared, diff. Zero missing, zero added.
- **Corner spawn**: the player spawns near a cube corner here; that is the
  worst case for enumeration and density. Check `PlotsPending` reaches 0 and
  the count is comparable to a face centre.
- **Impostor A/B**: force `impostorDistance` to 1 and to 10⁵, screenshot
  from the same camera; cards must match size, orientation and brightness.
  Restore the asset values afterwards (edits in play mode persist).
- **`PlotsBuiltTotal` must stop rising** when standing still.

Then the Editor once, via `marchingcubes-workflow`.
