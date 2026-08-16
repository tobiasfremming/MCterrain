# Voxel Terrain System

How this project's procedural terrain works, end to end: from a math function to
meshes you can walk on, dig into, and see for kilometers.

---

## 1. The big picture

There is (almost) no stored voxel data. The terrain is an **implicit surface**:
a pure function `density(x, y, z)` where **positive = solid rock/sand,
negative = air**, and the ground surface is wherever the function crosses zero.
Everything else in the system exists to *sample* that function and turn it into
triangles efficiently:

```
                     Biome assets (shape + material per biome)
                                    │
                            BiomeDensityField          "what does the world look like"
                       (softmax blend of biomes)
                                    │
                          ModifiedDensityField         "…plus what the player changed"
                    (+ sparse voxel edit deltas)
                                    │
    ┌───────────────────────────────┴─────────────────────────────┐
    │                        MCChunkManager                        │
    │  clipmap LOD boxes · streaming queues · staged LOD swaps     │
    └───────────────┬───────────────────────────────┬─────────────┘
                    │  ChunkMeshJob (worker threads) │
                    ▼                                ▼
              ChunkMesher                      MarchingChunk
      marching cubes + Transvoxel          mesh upload + collider
         (pure math, threaded)               (main thread only)
```

Because every consumer samples the *same continuous function*, consistency is
structural: any two chunks, any two LOD levels, the render mesh and the physics
mesh — they can never disagree about where the ground is.

Key files:

| Area | Files |
|---|---|
| Density fields | `DensityField`, `HeightDensityField`, `DuneHeightfield`, `CanyonVolumeField`, `AlienVolumeField`, `BiomeDensityField`, `ModifiedDensityField`, `TerrainNoise` |
| Biomes | `Biome`, `BiomeWorld.asset`, `DesertBiome.asset`, `CanyonBiome.asset`, `AlienBiome.asset` |
| Meshing | `ChunkMesher`, `MarchingCubesTables`, `TransVoxelTables` |
| World management | `MCChunkManager`, `MarchingChunk`, `WorldConfig` |
| Terrain editing | `TerrainModificationSystem`, `TerrainModificationCache` |
| Player | `PlayerBootstrap`, `SimplePlayerController`, `FootprintEmitter`, `TerrainDigger`, `DesertAtmosphere` |
| Rendering | `Shaders/SandTerrain.shader`, `Materials/SandTerrain.mat`, generated textures in `Textures/` |

---

## 2. Density fields (the terrain itself)

### 2.1 Two kinds of field, one contract

Everything is a `DensityField`: `Sample(p)` returns positive inside rock,
negative in air, and the mesh is the zero level set. Only the **desert** is a
heightfield; the canyon and alien biomes are **pure 3D functions** (SDF-style)
— `Sample(p)` is their whole definition, with no height layer underneath, so
overhangs, leaning walls and tunnels come for free.

Grid meshing goes through `AddDensityColumn(x, z, yStart, yStep, count,
weight, dest…)`, which each field overrides to cache its per-(x, z) work once
per column (the desert's `HeightAt`, the canyon's ripple term, the alien
field's tunnel-layout noise). This keeps pure-3D fields nearly as cheap to
grid-sample as heightfields.

For terrain that *is* a heightfield (`density = HeightAt(x, z) − y`), the
abstract `HeightDensityField` provides:

- **Column-optimized sampling** — `SampleGrid` evaluates the expensive
  `HeightAt` once per (x, z) column instead of once per 3D sample (~33× fewer
  noise calls for a full-resolution chunk).
- **Cheap exact gradients** — ∂/∂y of `h − y` is exactly −1, so normals need
  only 2D height differences instead of 6 full density samples.
- **Optional 3D extras** — `Extra3DAt(x, y, z)` is added on top, enabling
  overhangs, bridges and caves while keeping the column fast path
  (`AddExtra3DColumn` caches all (x, z) work per column). The gradient
  automatically switches to full 3D central differences inside the feature
  band (`Get3DBand`) — the two formulas agree exactly where the extra term is
  zero, so the switch can't create seams.

### 2.2 Noise

All fields share `TerrainNoise`: seeded integer-hash gradient noise with a
32-direction gradient LUT. It is deterministic across machines (unlike
`Mathf.PerlinNoise`) and mirrored 1:1 by the Python prototypes used to tune
the terrain (see §8).

### 2.3 The dune field

`DuneHeightfield` builds transverse dunes from geomorphology (see the papers in
the repo owner's collection — Bishop et al. 2001, Paris et al. 2019):

- **Asymmetric profile**: ~72% of each dune period is a long concave windward
  rise ending in a sharp crest brink, then a short steep slip face near the
  angle of repose. This asymmetry is what makes dunes read as dunes.
- **Three superimposed systems**: mega-dunes (~320 m), secondary dunes riding
  on them (~62 m, slightly rotated wind, appearing in patches), and a ~7 m
  ripple texture.
- **Domain-warped phase** for sinuous crests, plus regional sand-supply and
  size modulation so the field varies over kilometers.

### 2.4 The canyon field (pure 3D, IQ "Canyon" techniques) — mountains + canyons

`CanyonVolumeField` is a faithful port of the *construction* in Inigo Quilez's
"Canyon" shadertoy, reimplemented on our own noise (his code is
license-restricted; techniques only):

```
massif  = peakBase + peakRange · ridgedFbm(x/peakScale, z/peakScale)
        + detailAmp · ridgedFbm(x/detailScale, z/detailScale)   // jagged peaks
thn     = fbm3(x/thScale, 0, z/thScale) · 1.06
th      = smoothstep(thLo, thHi, thn)          // 1 = canyon/valley, 0 = mountain
h(x,z)  = floorHeight + massif·(1 − th) + ripple                // "terrain()"
density = h(x,z) − y − disAmp · fbm3(x, y·disSquash, z, /disScale)  // "dis()"
```

- `massif` is **ridged multifractal noise** (`TerrainNoise.RidgedFbm`:
  Musgrave-style `(1−|noise|)²` per octave, each weighted by the previous
  octave) — this is what turns rounded fbm hills into dramatic, jagged
  mountain ridgelines and peaks, with a second finer ridged layer adding
  sub-peak/spire detail.
- **`h` is deliberately a function of (x, z) only.** Early iterations let the
  macro shape itself vary with height (to get "3D" leaning walls) and this
  reliably produced floating rock under 3D flood-fill testing — once a
  100+ m mountain shape swings with y, a column's solid/air crossings stop
  being predictable. Keeping `h` a pure 2D function guarantees peaks of *any*
  height stay attached to the ground, matching IQ's own two-stage
  construction (a `terrain()` height function, then a separate small 3D
  `dis()`).
- The **erosion displacement is the only y-dependent term** — bounded
  amplitude (`disAmp`), vertically squashed (`disSquash`) — and is what
  carves real overhangs, undercuts and the striated eroded-cliff look without
  ever being large enough to disconnect rock from the ground.
- A **narrow smoothstep window** (`thLo`/`thHi` close together, e.g.
  0.47/0.52) is what makes the mountain→canyon transition a sheer cliff
  instead of a gentle slope; widen the window for foothills instead of
  cliffs.
- `floorHeight` sits near the desert base so sand collects where it's low and
  the mountains tower over it.
- Verified via 3D flood-fill across 7+ world sites (0 floaters) and numeric
  cross-check against the Python prototype (≤1.2e-4 agreement).

**Rock spires (pillars).** A pure `(x, z)` height boost (`SpireBoost`):
Worley-style jittered-cell placement (`spireCellSize`, `spireChance`) picks
sparse tower centers, each contributing a radial bump (`spireRadius`/
`spireHeight`, wobbled by `spireIrregularity` for an eroded, non-circular
silhouette). Because it's still purely a function of `(x,z)`, it inherits the
same floater-safety argument the mountains use — no separate verification
needed.

Unlike the mountain massif, the spire contribution is added **after** the
`*(1-th)` multiply, not before, and is gated by the *local terrain height*,
not by `th`: `spireMaxBaseHeight`/`spireBaseFadeBand` smoothly fade a spire's
strength to zero once the ground it would stand on rises above that height,
so pillars only appear near the valley floor / cliff base — never on a
mountain's own peak (an earlier version added the boost *before* the
`(1-th)` multiply, which meant spires were scaled by mountain-ness and so
appeared strongest on peaks and vanished in the canyon — backwards from real
erosion-formed hoodoos, which stand apart from what eroded them). The result
is also hard-clamped to `floorHeight + peakBase + peakRange + detailAmp` (the
tallest a mountain can ever be), so a pillar can never read as taller than
the peaks around it.

**Natural rock arches (bridges) — fixed-cost, no search.** Two search-based
designs were tried and discarded before landing on this one (see below); the
final architecture places and shapes a bridge with a *fixed* number of noise
calls per candidate site, with no loop over directions and no accept/reject
validation step at all:

1. **Placement** is the same Worley-style jittered-cell hash spires use — a
   fixed O(9) neighbor-cell lookup, gated by `bridgeChance` for rarity. Not a
   search.
2. **Orientation** comes from *one* cheap directional sample: the gradient of
   `ThAt` (the mountain/canyon classifier alone, no massif/ridge/spire cost)
   at the candidate center, from 4 extra `ThAt` calls. This is an
   approximate "which way does the valley run" guess, not a validated
   search — if it's not quite right, the bridge just looks a little less
   dramatic; it never breaks structurally, because of point 3.
3. **Legs always follow the real terrain down to solid ground.** Each leg's
   bottom is set directly from `HeightAt` at the leg's own (x,z) — two direct
   calls, no rejection: `legBottom = min(0, (realHeightThere - springline) -
   embedMargin)`. Whatever is really there — a dramatic cliff or a modest
   hillock — the leg embeds into it. **This is what removes the need for any
   validity check**: the geometry is built to always reach whatever ground
   already exists at that point, so it cannot fail to connect.

The arch shape itself is a union (plain `min()`, not smooth — they're one
explicit object) of three primitives: the circular-arc top (clipped to
`v > -tubeR*1.2` — an earlier version let the full circle show through,
which mirrored a second solid ring below the springline, a "floating lens"
of rock) and two straight vertical leg capsules running from the springline
down to `legBottomA`/`legBottomB`. That combined shape is then
smooth-unioned (`SMax`) onto the base terrain so it welds into the
surrounding rock without a hard seam.

Total fixed cost per candidate: 1 `HeightAt` (center) + 4 `ThAt`
(orientation) + 2 `HeightAt` (leg embedding) — regardless of whether the site
ends up "near a wall" or "in the middle of an open valley". Verified via 3D
flood-fill at two *freshly generated* sites (not hand-picked) — 0 floaters at
both, plus an explicit "is there open air under the arch" sample check at
each.

**Two earlier, discarded designs**, kept here because the reasoning matters
for future changes:
- **v1 — accept/reject via full-height 8-axis search.** Scanned
  `bridgeAxisSamples` directions with the *full* `HeightAt` (ridged massif +
  spire Worley, ~85 noise ops) at each, then only accepted a site if some
  direction cleared `bridgeMinWallClearance` on both sides. This ran for
  *every* low-lying candidate cell (~30% of the world), not just ones near an
  actual gap — an 8-minute terrain build resulted.
- **v2 — cheap-scan-then-verify.** Kept the accept/reject structure, but
  used `ThAt` (cheap classifier only) to pick the best-looking axis, and paid
  for the accurate `HeightAt` check only once. Much faster (~194ms → ~42ms
  worst case per chunk's columns) but still fundamentally a per-site search
  with a validation gate — and the user correctly pointed out that placement
  should be "part of the terrain calculation" with no searching, sampling at
  most one cheap incline check. The terrain-following-legs design above is
  the result: no search, no validation, fixed cost, same floater guarantee
  via construction instead of via checking.

**Orientation must never be allowed to degenerate to zero.** The first
implementation picked the span axis from the gradient of `ThAt` (the
mountain/canyon classifier alone, for cheapness). `ThAt` is a smoothstep that
*saturates* to an exactly-flat, exactly-constant 0 or 1 everywhere outside
its narrow transition band — so its gradient is *exactly zero* almost
everywhere a bridge actually gets placed (canyon floor, by definition away
from the cliff edge where `th` is doing anything). A zero gradient made
`perpX`/`perpZ` collapse to `(0,0)`, which collapsed the `u`/`w` local
coordinates to 0 for every point in the world — turning the arch into a
function of height alone, i.e. **an infinite flat slab** at whatever
elevation the arc/leg shape happened to be solid at. This is what the user
saw as "random flat large planes." Fix: use the gradient of the full
`HeightAt` instead (which keeps varying continuously everywhere from the
ridge/detail/ripple noise, so it's non-zero in all but pathological cases),
with a deterministic hashed-angle fallback for the rare case even that's
too flat (`glen <= 0.05`) — orientation can now never be degenerate. Found
via direct ASCII-art cross-section dumps in the C# verification harness
(ad-hoc matplotlib scripts had already proven unreliable for this feature —
see below — so plain console output of `#`/`.` per sample point was the
fastest reliable way to see the actual shape).

**Scale: they have to look like bridges, not landforms.** The first pass at
this design used span/rise/tube sizes carried over from the old
search-based version (span 90–160m, tube radius 5–9m, blend radius 6) and,
seen up close from underneath, it read as a giant amorphous overhang rather
than a recognizable arch — both because a structure that large dwarfs the
player and the frame at typical viewing distance, and because a wide smooth
blend radius welding it into the terrain ballooned the connection into a
rounded mass rather than a crisp span. Fix: shrink everything to a scale
that reads as a walkable stone arch relative to the ~150m mountains around
it — `bridgeHalfSpanMin/Max` 45–80 → 15–30 (span 30–60m), tube radius 5–9 →
2.5–4.5, walkway half-width 6 → 3.5, and `bridgeSmoothing` 6 → 3 for a
tighter, more distinct weld into the rock. Re-verified 0 floaters at the same
scale-adjusted sites and re-confirmed the numeric port. `bridgeChance` is
untouched (0.02) — this was a shape fix, not a frequency fix.

### 2.5 The alien field (pure 3D, Shane "Desert Canyon" techniques)

`AlienVolumeField` — the cold rocky alien biome — ports Shane's `map()`
construction (again techniques only):

- A **3D sin/cos lattice** at two frequencies where y participates, giving
  genuinely three-dimensional bulbous, overhanging rock swells.
- A `fbm3` detail term on top.
- **Tunnel gorges** carved with a **smooth-min** along the zero contours of a
  large 2D noise — his single camera-path tunnel generalized to a
  world-spanning network. `tunnelBlend` is the smooth-min radius.

Both volume fields were verified floater-free with 3D flood-fill scans over
multiple world sites before porting.

---

## 3. Biomes

A `Biome` asset bundles everything that defines one biome:

- `terrain` — any `DensityField` (heightfield or pure 3D volume; its subclass
  exposes all shape parameters in the inspector),
- `bias` — how much of the world it claims,
- `hardness` — 0 soft sand … 1 hard rock (drives footprints; blended smoothly),
- palette colors and optional albedo/normal detail textures.

`BiomeDensityField` (the `BiomeWorld` asset) blends the biomes:

- **Weights are a softmax** over per-biome low-frequency noises. They always
  sum to 1 (no coverage holes), vary smoothly (no hard borders), and
  `sharpness` controls transition width. Adding a biome = adding to the list.
- **Densities are blended, not meshes**: `D(p) = Σ wᵦ(x,z)·Dᵦ(p)`. The result
  is still one continuous function, so the watertightness guarantees hold
  across biome borders automatically. Gaps are impossible by construction.
  Grid sampling computes the weights once per column and lets each member fill
  the column via its own `AddDensityColumn` fast path.
- Negligible weights (< 0.004) are skipped and the rest renormalized — still a
  pure function of position, so all LODs agree exactly.
- **Vertex colors carry the weights** of biomes 1–3 (R/G/B); the shader
  cross-fades biome palettes with them, so color transitions exactly track the
  terrain blend.

Live tuning: `OnValidate` on any Biome/field asset fires
`TerrainTuning.Changed`; the manager streams a full regeneration in play mode.

---

## 4. Meshing (ChunkMesher)

Each chunk covers a cube of world space with a fixed cell grid (default 32³).
`ChunkMesher.Build` runs on **worker threads** and is pure computation:

1. **Empty-chunk skip** — if the field's conservative height bounds say the
   surface can't intersect this chunk (and no player edits overlap it), return
   an empty mesh instantly. In a cubic clipmap ~80% of chunks skip.
2. **Marching cubes** over the sampled grid: per cell, the 8 corner signs form
   a case index into a triangle table; vertices are placed on sign-changing
   edges by linear interpolation. Vertices are **deduplicated** via an
   edge-keyed cache (~4× fewer vertices and gradient evaluations).
3. **Normals** from the density gradient at each unique vertex — this is what
   gives smooth shading and what the Transvoxel offset projection needs.
4. **Transvoxel transition cells** on faces bordering finer neighbors (§5).
5. Optionally a **collision-only mesh** (no normals, no Transvoxel deformation)
   from the physics field (§6).

Vertex colors (biome weights) are baked here too, at the vertex's primary
position.

---

## 5. LOD: clipmap + Transvoxel

### 5.1 Clipmap rings

Every level-k chunk has the same cell count but covers 2ᵏ× the base world size
(cells are 2ᵏ× coarser). Each level keeps a box of chunks around the player;
the region covered by the finer level is cut out:

```
L2 L2 L2 L2 L2 L2
L2 L1 L1 L1 L1 L2        level k+1 chunks are 2x the size,
L2 L1 L0 L0 L1 L2        same cell count -> half the resolution
L2 L1 L0 &  L1 L2        & = player
L2 L1 L1 L1 L1 L2
L2 L2 L2 L2 L2 L2
```

Boxes are built **bottom-up**: level 0 tracks the player snapped to 2-chunk
alignment; each parent box wraps its child with ≥1-chunk margins on an
even-aligned position. This guarantees every LOD interface is exactly **2:1**
and lies on whole chunk faces of both levels — verified for all player
positions (box extent must be even and ≥6; extent 4 is mathematically
impossible). Default: 6 levels ≈ 1.5 km view distance from ~1150 chunks.

### 5.2 Transvoxel stitching

At a 2:1 interface the two meshes disagree, which would leave cracks. Lengyel's
Transvoxel algorithm fixes this: the **coarse** chunk squeezes its outermost
cells inward ("secondary vertex positions", Eq. 4.2 + tangent projection
Eq. 4.3) and fills the gap with a sheet of **transition cells** whose
full-resolution face matches the fine neighbor exactly and whose
half-resolution face matches its own deformed mesh. Their triangulations come
from 512-case lookup tables (`TransVoxelTables`).

Conventions that must not change (verified against the dissertation and by
watertightness tests):
- Transition case bits per full-res corner 0–8:
  `{0x01,0x02,0x04,0x80,0x100,0x08,0x40,0x20,0x10}`, bit set when density < 0.
- Vertex-data corner indices are both in the **low byte** (`>>4`, `&0xF`).
- Face bases satisfy U×V = outward normal; the table's invert bit is then the
  only winding flip needed.
- Vertices near a face **without** a transition keep their primary position
  (this seals seams with same-LOD and coarser neighbors).

---

## 6. Runtime: streaming, swaps, editing

### 6.1 The manager loop (`MCChunkManager.Update`)

1. Recompute clipmap boxes — only changes when the player crosses a boundary;
   moving within a chunk costs nothing.
2. **Apply finished builds** (oldest-first FIFO — newest-first starved one
   chunk at a time) under a per-frame millisecond budget: mesh upload +
   collider cook on the main thread.
3. **Dispatch builds** to worker threads: edit-driven (dirty) jobs first, but
   capped at half the worker slots while streaming work pends (otherwise the
   footprint stream while sprinting starves streaming entirely), everything
   sorted player-adjacent-first.
4. **Sweep retiring chunks** (staged swaps, below).
5. Periodically flush the edit cache's short-term tier.

### 6.2 Staged LOD swaps (no popping holes)

When a region changes LOD, the replaced chunk is **retired, not released**: it
keeps rendering while its replacements (8 finer children or a coarser parent,
resolved from the boxes) generate hidden. When the whole covering set is ready,
the old chunk is released and the replacements revealed **in the same frame**.
Verified: 0 holes / 0 overlaps at 180 m/s and under flip-flop movement.
Swap groups near the player jump the job queue so the ground you're looking at
never lags.

### 6.3 Terrain editing (footprints, digging, caves)

`TerrainModificationSystem` owns two sparse voxel-delta layers:

- **visual** — rendered but ignored by physics (footprints; the collider never
  re-cooks while you walk, which is also why walking is smooth),
- **physical** — rendered *and* baked into colliders (digging).

Each layer is a `TerrainModificationCache`: per-voxel density deltas with a
**short-term tier** (recently touched, hot) that consolidates into a
**persistent tier** (run lifetime) after idling. Sampling is trilinear with a
region-occupancy index so untouched terrain pays nothing; all access is
lock-protected for the worker threads.

Operations:
- `StampSphere` / `StampLine` — smooth depressions, clamped accumulation
  (footprint trails; line stamps make continuous grooves).
- `CarveSphere` — true 3D removal: forces density down to the sphere's signed
  distance, so one scoop excavates a full sphere at any rock depth. This is
  what makes tunnels and caves possible. Self-limiting (ignores the depth cap).

Edits fire `RegionModified`; the manager remeshes every generated chunk (at
every level — skipping coarser levels would open seams at LOD boundaries)
whose samples can see the edit, including chunks whose *first build is
currently in flight* (missing that was a permanent-crack bug). Visual-only
re-dirties are coalesced (≥0.25 s per chunk) so stamp streams batch.

The density stack: render field = base + visual + physical; physics field =
base + physical. Wrappers are runtime ScriptableObjects — they can survive a
domain reload with lost internal references, so the manager validates and
rebuilds them (`IsValid`).

### 6.4 Player

`PlayerBootstrap` auto-wires everything on Play (controller, camera,
footprints, digger, atmosphere; steps aside if you set things up manually).
Footprint depth scales with `1 − hardness` at the foot position — deep prints
in sand, fading near rock, none on it. The digger raycasts from the camera and
carves physical spheres (`R`, hold to repeat).

---

## 7. Rendering

One custom URP shader (`MarchingCubes/Sand Terrain`) drives all terrain:

- **Triplanar** sampling of generated tileable sand textures (albedo + normal
  map with grains and pebbles) — the mesh has no UVs. Anti-tiling blends two
  rotated/scaled samples switched by low-frequency noise.
- **Slope tinting**: slip faces (≳21°) darker/warmer than flat sand.
- **Sahara palette** sampled from reference photography; ambient is pulled
  warm (`_ShadowWarmth`) because desert shadows bounce orange, never grey.
- **View-dependent sand**: grazing-angle fresnel sheen + sparse sun glints.
- **Canyon biome** (blended by vertex color R): warped sediment layers with
  sub-layer striations (adapted from the owner's MountainLayers shader),
  sandy floors on flat surfaces.
- Double-sided with normal flip (cave interiors light correctly), fog-aware.
  `DesertAtmosphere` enables exp² haze at runtime and extends the far plane.

---

## 8. Verification methodology (why you can trust changes)

The project's discipline, and the reason most bugs never reached the editor:

1. **Prototype in Python first** (`scratchpad`: `dunes.py`, `canyon_v2.py`,
   `tv_proto.py`, …) using an exact mirror of `TerrainNoise`. Look at rendered
   hillshades/slices and iterate until it's right.
2. **Property-check the math**: watertightness = every mesh edge shared by
   exactly two opposite-direction triangles (run over every seam type: all six
   faces, chunk-edge corners, mixed-LOD junctions, 4-fine-vs-1-coarse clipmap
   interfaces, edits crossing LOD seams); floating rock = 3D flood-fill
   connectivity; clipmap box math = randomized parity/margin search; swap
   logic = a state-machine simulation asserting exactly-one-visible-chunk per
   point per frame.
3. **Port to C# 1:1 and cross-check numerically** (standalone console build in
   `scratchpad/dunetest`) — typical agreement ≤1e-4 m at random points.

If you change terrain math, keep the Python mirror in sync and re-run the
relevant checks; if you change meshing/LOD bookkeeping, re-run the seam tests
and the swap simulation.

---

## 9. Common tasks

**Add a biome**
1. Write a `DensityField` subclass — pure 3D (like `CanyonVolumeField` /
   `AlienVolumeField`: implement `Sample`, override `AddDensityColumn` to
   cache per-column 2D terms) or a `HeightDensityField` if it really is a
   heightfield. Expose parameters as public fields, use `TerrainNoise`,
   implement `TryGetHeightBounds`.
2. Create its asset + a `Biome` asset (hardness, palette, textures).
3. Add the Biome to `BiomeWorld`. Blending, colors, hardness and stitching all
just work. If it needs unique *textures* (beyond palette), the shader needs a
texture-array upgrade — the material binder in the manager is the extension
point.

**Add an edit tool** — call
`manager.Modifications.CarveSphere/StampSphere/StampLine(..., affectsPhysics)`.
Remeshing, colliders, persistence tiers and thread safety are handled.

**Tune the world live** — edit any Biome/field asset in the inspector during
play; the world regenerates streamed. Key knobs: `BiomeWorld.sharpness`
(transition width), `regionScale` (biome size), per-field shape parameters,
`generationBudgetMs` / `workerThreads` on the manager (streaming throughput),
`modMaxDepth` (footprint wear cap; carving ignores it).

**Who owns a field asset's values, code or the Inspector?** The Inspector
wins. A `.asset` file (e.g. `CanyonField.asset`) is YAML that serializes a
concrete value for every public field the first time the asset is created;
from then on, editing the C# class's default value does **nothing** to an
asset that already exists — Unity always loads the value baked into the
`.asset` file, never the compiled-in default. This is also why field
*renames* need care: if you rename a public field, Unity's serializer just
drops the old YAML entry and falls back to the new field's compiled default,
silently losing whatever was tuned in the Inspector.

Practically, when asking Claude to change terrain parameters: Claude edits
the `.asset` file directly (it's plain text — `seed:`, `peakRange:`, etc. are
simple YAML keys) so the change actually takes effect. If you've been
hand-tuning values in the Inspector in the same session, mention that (or
have Claude re-read the `.asset` file first) — otherwise Claude's edit will
overwrite your in-Inspector tuning, and conversely your next Inspector edit
after Claude's change will overwrite Claude's.

**Persist player edits across sessions** (not yet implemented) — serialize the
persistent tier of both `TerrainModificationCache`s (voxel→delta dictionaries)
per world seed and re-apply on load; everything downstream already handles it.
