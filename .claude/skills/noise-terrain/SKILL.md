---
name: noise-terrain
description: Design, tune and debug noise-based procedural terrain — heightfields and 3D density fields built from fBm, ridged/hybrid multifractals, domain warping, derivative-weighted (erosion-like) noise, terraces, biome blending and hydraulic/thermal erosion — with the specific rules this MarchingCubes project's DensityField stack imposes (positive = solid, band-limiting by sample spacing, no y-dependent macro amplitude, GPU-leaf parity, floater checks). Use whenever the task touches a DensityField, Biome, TerrainNoise, dunes/canyon/frost/alien fields, "the terrain looks wrong/flat/blobby/repetitive", adding a landform (mountains, mesas, caves, arches, rivers), a new biome, or tuning a Config/*.asset terrain parameter. Trigger even if the user only says "make the ground more interesting".
---

# Noise terrain

Terrain here is a **signed density field** sampled by a clipmap of marching-cubes chunks. Everything below serves one question: *what function of position gives the landform I want, and does it stay correct at every LOD?*

Two documents carry the detail; read them when the task calls for them, not up front:

- `references/noise-recipes.md` — the techniques, with formulas: fBm and its parameters, ridged/hybrid multifractals, domain warping, derivative-weighted fBm, redistribution and terraces, 3D density construction (hard floors, shelves, caves), biome blending, planet wrapping.
- `references/erosion.md` — particle and pipe-model hydraulic erosion, thermal erosion, and when an offline erosion pass is worth it versus erosion-*like* noise.
- `references/project-fields.md` — the contract every field in this repo obeys, the classes to extend, and the verification workflow that has caught every floater and seam so far.

## The governing rules

**1. Positive is solid.** `DensityField.Sample(p, filterWidth)` returns `+` inside rock, `-` in air; a heightfield returns `h(x,z) - y`. Every consumer (mesher, gravity, plant scatter, digging) assumes it. Do not invent a field with the opposite sign.

**2. A field is a pure function of position and sample spacing.** No caches keyed on the player, no order dependence, no `UnityEngine.Random`. Chunks mesh on worker threads in arbitrary order and at six LOD levels; two evaluations at the same point and spacing must agree bit-for-bit or the Transvoxel seams crack. `[ThreadStatic]` scratch and `ConcurrentDictionary` plot caches are fine (see `LSystemGroveField`); shared mutable state is not.

**3. Band-limit by spacing, never by distance.** `TerrainNoise.DetailFade(filterWidth, featureSize)` fades an octave out when the grid cannot resolve it. Pass the grid's real spacing from grid fills, `0` from point queries. A feature at full strength on one LOD and gone on the next reads as the terrain changing shape at every ring, which is why the fade band spans a factor of four. Mirror any change in `TerrainNoiseGPU.hlsl` (`MC_FADE_START`/`MC_FADE_END`) or CPU normals stop matching GPU geometry.

**4. Macro amplitude must not depend on y.** Any term whose amplitude is a large fraction of local relief (massifs, walls, mesas) is 2D: `f(x,z)`. Only small bounded terms (erosion striation, crag, ~10–20 m) may vary with height. Three canyon rewrites produced floating rock islands before this rule existed. If you must break it, flood-fill for floaters before trusting it (`references/project-fields.md`).

**5. Fixed cost, no search.** Landform placement is a hash of a cell (Worley-style) plus a few cheap samples, never a per-column search-and-validate loop. Safety is built into construction (a bridge leg extends to the *real* ground height at its own x,z), not checked afterwards. The bridge feature went through three search-based versions, each too slow, before this shape.

**6. Every biome must be a GPU leaf.** `BiomeDensityField.TryBuildGpuLeaves` needs every member to report a `GpuFieldType`; one `None` drops the whole world to CPU meshing. A grammar-driven or otherwise non-closed-form field splits the work: CPU builds a compact atlas per plot, the GPU evaluates it (see the grove field).

**7. Assets are authoritative.** A `Config/*.asset` serialises concrete values. Changing a C# default does nothing to an existing asset; tune the `.asset` (or the inspector) and say so.

## Choosing the construction

| You want | Reach for | Not |
|---|---|---|
| Rolling ground, dunes, plains | fBm of gradient noise, H≈1 (gain 0.5), 4–6 octaves | value noise alone (blocky), many octaves at LOD0 |
| Jagged peaks, ridgelines | ridged multifractal `(1-|n|)²` weighted by the previous octave (`TerrainNoise.RidgedFbm`) | `abs(fbm)` (creases, not ridges) |
| Eroded, heterogeneous slopes | derivative-weighted fBm: scale each octave by `1/(1+dot(d,d))` | post-process blur |
| Organic, twisted, "tectonic" layouts | domain warp `fbm(p + k·fbm(p + ...))` with fixed offsets | higher octave count |
| Flat floors under sheer walls | smoothstep classifier with a **narrow** band (0.47–0.52) | wide bands (rolling slopes) |
| Overhangs, caves, arches | explicit 3D SDF primitives (capsules, arcs) smooth-unioned onto a 2D base | 3D noise with large amplitude (floaters) |
| Mesas, strata | terraces: `round(e·levels)/levels` blended by a mask, or y-banding on *pre-warp* coordinates | hard steps everywhere |
| Distinct regions | softmax biome weights over region-scale fbm, sharpness ~150 for near-argmax | lerp by distance to a centre |

## Workflow for a terrain change

1. **Prototype in Python first.** Mirror `TerrainNoise` in a scratchpad script (the hash and gradient LUT are small), build the formula, render a hillshade, and *look at it with the Read tool*. Stats alone never caught "rolling hills, not cliffs". Benchmark a 50×50 grid before any big render and wrap exploratory scripts in `timeout`.
2. **Verify shape numerically before rendering it.** A column of raw densities or a 40×100 ASCII cross-section printed to the console beats a plotting library when a render looks wrong: trust ground truth over the visualiser.
3. **Flood-fill for floaters** at several sites whenever a term varies with y or a new primitive is added. Zero is the only acceptable count.
4. **Port to C#** and check parity at ~10 points (≤1e-4 m). Keep the prototype next to the port's name in the scratchpad notes; the scratchpad is ephemeral, so record what it proved in the commit or a memory.
5. **Check every LOD**, not just LOD0: coarse rings alias; if a feature appears only near the player, its octave is above the band limit. If it vanishes at distance, `TryGetHeightBounds` may be lying (empty-chunk skip).
6. **Then the Editor**, once: enter play mode, walk, screenshot. See the `marchingcubes-workflow` skill for the MCP rules.

## Parameter intuition worth memorising

- **Gain 0.5 (H=1)** gives natural, isotropic terrain: higher mountains are also wider. Gain toward 1 is rain, not rock.
- **Lacunarity ≈ 1.9–2.1**, detuned from exactly 2, kills octave alignment artefacts. Rotate the domain a little per octave for the same reason.
- **Octaves = log(extent / finest feature) / log(lacunarity)**. With band-limiting you can afford more, because coarse rings drop them for free.
- **Normalise** fBm by the sum of amplitudes if a `[0,1]` range matters (redistribution, biome thresholds). Multifractals don't normalise; clamp instead.
- **Redistribution** `pow(e·1.2, k)` with k in 1.5–3 turns a Gaussian heightmap into valleys with sharp peaks. Do it on the 2D height, not on 3D density.
- **Biome sharpness** high (~150) behaves as an argmax with soft edges of a few metres; select biomes from the *sphere position* on a planet, never from height, or a strip 200 m wide around every boundary stacks one biome over another.

## What to report back

State the construction chosen and why, the parameters that matter and their asset paths, what was verified (floater sites, parity error, which LODs were viewed) and what was not. If a rule above was bent, say which and what the check was.
