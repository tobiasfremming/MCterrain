# This project's density fields

Code lives in `Assets/TerrainGen/Scripts/Terrain/` (a git submodule at
`Assets/TerrainGen`). Assets in `Assets/TerrainGen/Config/`.

## The contract (`DensityField`)

| member | must |
|---|---|
| `Sample(p, fw)` | signed density, `+` solid; pure function of `(p, fw)` |
| `SampleGrid(origin, nx, ny, nz, step, dest)` | identical values to `Sample` per point; override to batch per column |
| `Gradient(p, eps, fw)` | identical to central differences of `Sample` (seams depend on it) |
| `TryGetHeightBounds` | *conservative* surface band; lying here makes chunks vanish (empty-chunk skip) |
| `TryGetEmptySkip(min, max)` | override for non-Y "up" (planets) |
| `GpuType` / `ToGpuLeafParams` | required for any biome member, or the whole world meshes on CPU |
| `AddDensityColumn` | override to cache per-(x,z) work; this is how 3D fields stay fast |
| `HasVertexColors` / `GetVertexColor` | biome weights for the shader; pure function of position |
| `SurfaceHardness` | 0 soft (footprints) .. 1 rock |

Base classes: `HeightDensityField` (column-optimised 2D height + optional
bounded `Extra3D`), `BiomeDensityField` (softmax blend of `Biome` assets),
`PlanetField` (wraps any field onto a sphere via triplanar blend),
`ModifiedDensityField` (runtime wrapper adding edit deltas; never subclass it).

Existing leaves: `DuneHeightfield` (analytic transverse dunes, three
superimposed systems), `CanyonVolumeField` (ridged massifs + narrow smoothstep
classifier for sheer walls + spires + explicit arch primitives),
`FrostVolumeField`, `AlienVolumeField` (sin/cos lattice + gorges),
`LSystemGroveField` (grammar-grown spires as capsule SDFs, CPU atlas + GPU
evaluation), `ErodedHeightField` (fbm base with analytic derivatives run
through `ErosionNoise.Filter`, Rune Johansen's erosion filter -- one class,
two assets: MountainField and DesertMountainField differ only in
`ErosionParams`, base relief and sand fill; add a landform with erosion by
making a third asset, not a third class). Read the one closest to what you are building before writing a
new one; the shape of the problem repeats.

## Noise primitives (`TerrainNoise`)

Seeded integer-hash gradient noise with a 32-direction LUT (`GNoise`, 2D),
`VNoise3`/`Fbm3` (3D, IQ-style corner hash, cubic fade, amplitudes
0.5/0.25/0.125, frequency ×2.02), `RidgedFbm` (Musgrave feedback form),
`DetailFade(fw, featureSize)` for band-limiting, `Hash(ix, iy, seed)` for
cell decisions, `GNoiseD`/`FbmD` (same values with analytic d/dx, d/dy --
what the erosion filter steers by). Never `Mathf.PerlinNoise` (not seedable, not mirrored on GPU).
Every primitive has a twin in `Shaders/Compute/TerrainNoiseGPU.hlsl`; keep
them equal to ~1e-4 and keep `MC_FADE_START/END` in lockstep with
`kFadeStart/kFadeEnd`.

## Verification workflow (what has actually caught bugs)

1. **Python mirror** of `TerrainNoise` in the session scratchpad (it is
   ephemeral; rebuild it from the C# each session rather than assuming a
   previous file exists). Hillshade render, viewed with Read.
2. **Benchmark 50×50 first**, extrapolate, `timeout` the script. A 400×400×150
   render once ran for 8 hours.
3. **ASCII cross-section** (`#`/`.` per sample, 40×100) printed to the console
   when a render disagrees with expectations. Ground truth is a column of
   raw densities; when a plot and a column disagree, the plot is wrong.
4. **Flood fill for floaters**: 3D air/solid connectivity at 3–7 sites,
   including sites *found by the feature's own placement*, not hand-picked.
   Zero floaters, and for arches also "single connected air component
   reaching the box edge" so a sealed cave is not mistaken for open air.
5. **C# ↔ Python parity** at ~10 points, ≤1e-4 m. The existing checks lived in
   scratchpad `canyoncheck`/`shaderportcheck.cs`; recreate as needed.
6. **Offline C# compile** (see the `marchingcubes-workflow` skill) before the
   Editor sees it.
7. **In the Editor**: play mode, walk the seam between two LOD rings, look for
   cracks (band-limit disagreement or `Gradient` mismatch) and for terrain
   that changes shape per ring (feature above the band limit).

## Rules learned the hard way

- Amplitude-large terms that vary with y create floating islands. 2D macro,
  bounded 3D detail only.
- A saturated classifier (`smoothstep` at 0 or 1 almost everywhere) has a zero
  gradient almost everywhere. Never orient anything by its gradient; use the
  full height function's gradient plus a hashed fallback angle.
- Search-and-validate placement is the wrong architecture, not a slow
  constant. Hash a cell, take one cheap directional sample, build the safety
  into the construction (legs extend to real ground).
- When a per-column search must call the expensive height function, factor
  out a cheap proxy (classifier only) for the scan and pay full price once on
  the winner.
- Spires/hoodoos stand near valley floors, gated on *local terrain height*,
  and hard-clamped below the tallest possible peak.
- Terrain edits (`TerrainModificationCache`) are not band-limited: a dig is
  authored at a size, not procedurally generated. `ModifiedDensityField`
  layers them so every LOD sees the same edited field.
- Hot reload: `TerrainTuning.NotifyChanged()` from `OnValidate` regenerates
  in play mode; tune the `.asset`, not the C# defaults.
- Two projects' MCP servers can answer on the same port; verify the instance
  before believing a scene (`marchingcubes-workflow`).
