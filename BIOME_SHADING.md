# Biome shading by position

How the terrain knows "which biome is here" for rendering, and how anything
else (grass first) should ask the same question. Added 2026-09-07; replaces
the vertex-colour biome channels.

## The one rule

Biome identity is a pure function of world position. It is evaluated where
it is needed and never stored per vertex. There is one GPU implementation of
the selection, `Assets/TerrainGen/Shaders/Compute/BiomeSelect.hlsl`, and one
CPU implementation, `BiomeDensityField.ComputeWeights` / `ComputeWeights3D`.
They are mirrors; both take the same parameters and produce the same
partition-of-unity weights for up to `BiomeDensityField.MaxBiomes` (8) biomes.

Every consumer calls one of those two. Density (CPU and compute), the terrain
shader and, after its migration, the grass scatter therefore agree on every
boundary by construction.

## Why the old design was wrong

Before this, `BiomeDensityField.GetVertexColor` baked the weights of biomes
1..3 into vertex colour R, G, B at meshing time (biome 0 was the remainder, A
was ambient occlusion), and `SandTerrain.shader` had exactly four `_Chan*`
property sets. The density blend handled eight biomes; shading handled four;
nothing warned when the list grew past four, a fifth biome simply rendered as
biome 0. The per-vertex snapshot was also interpolated across triangles, so a
boundary a few metres wide in the density field smeared over a 16 m triangle
on the coarse LOD rings.

## Pieces

| File | Role |
|---|---|
| `Shaders/Compute/BiomeSelect.hlsl` | `BiomeSelectParams`, `MC_BiomeWeightsFlat`, `MC_BiomeWeightsSphere`, `MC_BiomeWeights(worldPos, P, out w[8])`. The selection. Defines `MC_MAX_BIOMES`. |
| `Shaders/Compute/DensityBiomeBlend.hlsl` | Density pipeline. `MC_ComputeBiomeWeights` / `MC_ComputeBiomeWeights3D` are now thin wrappers that fill `BiomeSelectParams` from the pipeline's `StructuredBuffer`s and call the shared functions. |
| `Shaders/Biomes/BiomeSelectGlobals.hlsl` | The shader **globals** (`_BiomeSel*`, `_BiomeShade*`), `MC_BiomeSelectFromGlobals()`, and `MC_BiomeShadeWeights(worldPos, out w, out count)` (weights sharpened per biome and renormalised, what shading uses). Include this from any surface or compute shader outside the density pipeline. |
| `Scripts/MarchingCubes/MCChunkManager.cs` | `PublishBiomeShadingGlobals(world, planet)`: sets every global from the `Biome` assets whenever `TerrainTuning` fires (called from `WriteBiomeMaterialProps`). Also still pushes the few style-level textures onto the shared runtime material. |
| `Shaders/SandTerrain.shader` | Computes the weights per pixel from `positionWS`, loops over the biomes in use and dispatches each to its style module (`EVALUATE_STYLE`). Vertex colour is read for AO only. |
| `Scripts/Terrain/BiomeDensityField.cs` | `MaxBiomes`, `OnValidate` warning when the list exceeds it. |

### The globals

Published by `MCChunkManager.PublishBiomeShadingGlobals`; read via
`BiomeSelectGlobals.hlsl`. They are globals, not material properties, because
several shaders read them and none of it is per-material data, so the SRP
Batcher is unaffected.

```
float4 _BiomeSelParams;           // x seed, y regionScale, z sharpness, w biome count
float4 _BiomeSelPlanet;           // xyz planet centre, w radius
float4 _BiomeSelFlags;            // x 1 = planet mode, 0 = flat
float4 _BiomeSelBias0, _BiomeSelBias1;   // Biome.bias for slots 0..3, 4..7 (-10 for an empty slot)

float4 _BiomeShadeA[8];           // x Biome.SurfaceStyle, y Biome.blendSharpness, z Biome.hardness
float4 _BiomeShadeFlat[8];        // Biome.colorFlat
float4 _BiomeShadeSteep[8];       // Biome.colorSteep
float4 _BiomeShadeLines[8];       // style-specific height lines, planet radius ALREADY ADDED:
                                  //   Dolomite:       x rock line, y rock line blend
                                  //   Mountain:       x snow line, y snow blend, z grass line, w grass blend
                                  //   DesertMountain: x sand line, y sand blend
```

Slot `i` is `BiomeWorld.biomes[i]`. Order in the list still only affects
the selection noise and therefore the region map, never which style renders
a biome.

### Using it from a shader

```hlsl
#include "Biomes/BiomeSelectGlobals.hlsl"     // path relative to your shader

// raw partition of unity (sums to 1), what the density blend used:
float w[MC_MAX_BIOMES];
MC_BiomeWeights(worldPos, MC_BiomeSelectFromGlobals(), w);

// or the shading weights (sharpened per biome, renormalised):
int count;
MC_BiomeShadeWeights(worldPos, w, count);

// per-biome data for slot b:
int   style     = (int)round(_BiomeShadeA[b].x);
float sharpness = _BiomeShadeA[b].y;
float hardness  = _BiomeShadeA[b].z;
```

`worldPos` is the absolute world position. In globe mode the function
projects it to `normalize(worldPos - center) * radius` itself; do not
pre-project, and never select from a per-face triplanar coordinate (the
three faces would disagree).

## Grass (migrated 2026-09-07)

The grass scatter is now a consumer of the selection like everything else,
and the vertex-colour bake is gone.

- **`Shaders/Compute/GrassScatter.compute`** includes
  `../Biomes/BiomeSelectGlobals.hlsl` and calls `MC_BiomeWeights` at the
  triangle centroid (world space) inside `EvaluateTriangle`. Vertex colour is
  read for AO (`.a`) only. Its own per-biome table is three eight-wide
  compute arrays set per scatter by `GrassSystem.Scatter`:
  `_GrassBiome[i]` (x blades/m², y local height where grass stops with the
  radius already added, z fade metres), `_GrassBase[i]`, `_GrassTip[i]`,
  plus `_GrassUseBiomes` (0 for worlds without a `BiomeDensityField` and for
  `GrassLab`: slot 0 applies everywhere and the `_BiomeSel*` globals are not
  read).
- **Blade record**: the fourth word is now `colors`, two RGB565 colours
  (base | tip << 16) blended over the biomes at the centroid weighted by
  `w[i] * density[i] * heightMask[i]`. `Grass.shader` unpacks them and no
  longer knows biomes exist; the record stays 24 bytes for any biome count.
- **`TerrainGrass.BuildBiomeParams`** fills `GrassSystem.BiomeParams`
  (`table`, `baseColors`, `tipColors`, eight slots, `useBiomeSelect`) from
  `Biome.grassDensity/grassColorBase/grassColorTip`. Height lines mirror the
  ground shading from the field assets: Dolomite `baseHeight + meadowLine`,
  Mountain (`ErodedHeightField`) `baseHeight + grassLine`, radius added. It
  calls `MCChunkManager.PublishBiomeShadingGlobals(world, planet)` whenever
  its parameter hash changes, so the globals exist before the first scatter.
- **Deleted**: `DensityField.HasVertexColors/GetVertexColor` and every
  override (`BiomeDensityField`, `PlanetField`, `ModifiedDensityField`),
  `GetVertexColorWithWeights`, the weight bake in
  `ChunkMesher.VertexColorWithAO` and `TerrainMesh.compute`'s
  `MC_VertexColor`. Both now write `(0, 0, 0, ao)`. The 40-byte vertex layout
  is unchanged.

## Border heights (relief fade)

Selection is a softmax with sharpness ~150, so a boundary is only ~20 m wide;
blending a 240 m mountain into a dune plain over 20 m is a cliff. Lowering
sharpness would cross-fade two mountain ranges into mush instead, so the fix
is separate from the weights: every biome's terrain fades toward a flat plane
at `BiomeDensityField.edgeHeight` as its *lead* in raw selection score over
the runner-up drops below `edgeBand` (0.2 score units, roughly 60-80 m per
side at regionScale 1000). At the border the lead is 0 and both sides sit at
`edgeHeight`; inside a region the lead is large and the terrain is untouched.
Borders therefore become lowlands (valley floors, sand flats, meadows), which
is also what real biome boundaries tend to be.

- CPU: `BiomeDensityField.ComputeWeights(x, z, w, relief, n)` /
  `ComputeWeights3D(pos, w, relief, n)` return the factors;
  `SampleWithWeights(p, w, relief, n, fw)` and `SampleGrid` apply
  `r * D_i + (1 - r) * (edgeHeight - y)` per biome before weighting.
- GPU: `MC_BiomeWeightsFlatRelief` / `MC_BiomeWeightsSphereRelief` in
  `BiomeSelect.hlsl` (parameter `BiomeSelectParams.edgeBand`, published in
  `_BiomeSelFlags.y`); `EvaluateBiomeBlendWithRelief` in
  `DensityBiomeBlend.hlsl`; `BiomeBlendParams` gained `edgeHeight`, `edgeBand`.
- Shading and grass ignore the relief factor: they only need the weights.
- Set `edgeBand` to 0 on the `BiomeWorld` asset to turn it off.

## Eroded Dolomites

`Config/DolomiteBiome` now points at `Config/DolomiteErodedField`, an
`ErodedHeightField` in `baseMode = Massif`: meadow floor, scree apron, sheer
warped wall and summit crests built with analytic derivatives, run through
the erosion filter (60 m couloirs, 5 octaves) with the fade target at 0
except toward the summits and the erosion masked out on the meadow
(`erosionOnsetRelief`). The Dolomite surface style is unchanged; its
meadow/rock line is the field's `grassLine`, which the grass reads too. The
old `DolomiteVolumeField` class and `Config/DolomiteField` asset remain,
unreferenced.

## Test scenes

`Assets/Scenes/Biomes/<Biome>.unity`, one per biome (Desert, DesertMountains,
Frost, Mountains, Canyon, Dolomites, Alien, Grove). Each is the SampleScene's
world objects pointed at `Config/Test/<Biome>WorldConfig`, a flat-world config
whose `defaultDensity` is `Config/Test/<Biome>World`, a `BiomeWorld` holding
only that biome. Press Play: the terrain streams around the origin, the
player drops onto the surface, plants and grass run as usual. To test on the
planet instead, tick `useGlobe` on that test config and give it a
`PlanetField` whose `surface` is the single-biome world.

The scenes are generated, not hand-edited: `Marching Cubes / Rebuild Biome
Test Scenes` (Assets/TerrainGen/Editor/BiomeTestScenes.cs) rebuilds all of
them from whatever the open SampleScene currently contains, remapping the
copied objects' references onto each other and setting every `worldConfig`
field. Add a biome = add a `<Name>WorldConfig` + `<Name>World` pair under
Config/Test and rebuild.

## Gotchas

- **Height lines are absolute local heights.** In globe mode `localHeight`
  in the shaders is the distance from the planet centre (~100 km). Every
  line in `_BiomeShadeLines` already has the radius added by the manager;
  do not add it again.
- **Uniform loop, divergent branch.** The terrain shader's biome loop has a
  uniform trip count (`_BiomeSelParams.w`) and an ordinary `if` on the
  per-pixel weight inside it. Texture samples inside a loop whose trip count
  is per-pixel would be a compile error (X4014); keep the loop bound uniform
  if you copy the pattern.
- **Per-pixel vs per-vertex.** `MC_BIOME_WEIGHTS_PER_PIXEL` in
  `SandTerrain.shader` (default 1) chooses between evaluating the selection
  in the fragment shader (exact boundaries at all LODs) and in the vertex
  shader with two `TEXCOORD` interpolators (free, looks like the old bake).
  Planet-mode selection costs two octaves of 3D value noise per biome per
  evaluation.
- **Textures are still per style, not per biome.** `_MainTex`/`_NormalTex`
  (Sand), `_PebbleTex`/`_PebbleNormal` (Alien), `_RockTex`/`_RockNormal`
  (Canyon, Dolomite, Mountain, DesertMountain) are single material slots; if
  two biomes share a style the last one in the list supplies the texture.
  Lifting that is a `Texture2DArray` indexed by biome slot, a separate task.
- **`MaxBiomes` is 8** on the CPU blend, in `MC_MAX_BIOMES`, and in the
  globals; `BiomeDensityField.OnValidate` warns past it. Nothing silently
  shades as biome 0 any more.
- **Selection is not band-limited** on purpose: it is kilometre-scale, and
  fading it would move biome boundaries with LOD.

## Current world

`Config/BiomeWorld.asset`, in slot order: Desert (Sand), Desert Mountains
(DesertMountain), Frost Glacier (Frost), Eroded Mountains (Mountain), Canyon
(Canyon), Dolomites (Dolomite). Six biomes, all GPU leaves.
