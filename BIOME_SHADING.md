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

## Grass: what to change

The grass scatter still reads the old vertex-colour bake, which is why that
bake has been left in place (marked TRANSITIONAL in the code). With the
world now holding six biomes, grass currently sees biomes 4 and 5 as biome 0.
The migration is self-contained:

1. **`Shaders/Compute/GrassScatter.compute`**: include
   `../Biomes/BiomeSelectGlobals.hlsl` (or `BiomeSelect.hlsl` and read your
   own parameters) and call `MC_BiomeWeights` at the triangle centroid in
   world space instead of decoding the vertex colours. The globals are set on
   the render thread by `Shader.SetGlobal*`, which compute shaders also see.
   If the scatter runs before the manager has published (first frame), call
   `MCChunkManager.PublishBiomeShadingGlobals(world, planet)` yourself; it is
   public and static and idempotent.
2. **`GrassCommon.hlsl` / the 24-byte blade record**: the `weights` word
   (4 x unorm8) can stay as a per-blade cache of the centroid weights, but it
   only holds four; either widen it, store the dominant biome index plus its
   weight, or look the weights up again from the blade root in the grass
   vertex shader (cheap: root position is already in the record).
3. **`Scripts/Grass/TerrainGrass.cs` `BuildBiomeParams`** and
   **`GrassSystem.BiomeParams`**: drop the `Mathf.Min(BiomeCount, 4)` and the
   `Vector4`-per-property layout; use eight-wide arrays
   (`SetGlobalFloatArray` / `SetVectorArray`) or a small `ComputeBuffer`.
   The Dolomite meadow line is already in `_BiomeShadeLines[i].xy`, so the
   special case there can read the table instead of the field.
4. **Then delete the bake**: `BiomeDensityField.HasVertexColors`,
   `GetVertexColor`, `GetVertexColorWithWeights`, `PlanetField.GetVertexColor`,
   the `GetVertexColor` call in `ChunkMesher.VertexColorWithAO` (write
   `Color(0, 0, 0, ao)`), and the per-vertex `MC_ComputeBiomeWeights3D` /
   weights write in `TerrainMesh.compute`. Keep the colour stream itself:
   `.a` is the baked AO and the 40-byte vertex layout does not change.
   CPU meshing loses one softmax per vertex.

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
