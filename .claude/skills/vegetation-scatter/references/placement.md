# Placement

## Plot ids

Flat world: key = `(px, pz)` from `floor(p.x / size)`, `floor(p.z / size)`.

Planet: project the direction from the planet centre onto a cube; face 0..5
by dominant axis; `u = sc/ma`, `v = tc/ma` in `[-1, 1]`; cell `cu = floor((u+1)/2 ·
cellsPerFace)`. `cellsPerFace = ceil(R · π/2 / size)` makes the *mean* cell
edge equal `size`. `FaceUVToDir` must be the exact inverse of `DirToFaceCell`
for every face, and must return a valid direction for `|u| > 1` — that is how
neighbours across a face edge are found without edge tables: compute the
neighbour's `(u±du, v)` on the current face, convert to a direction, and
re-project to canonical `(face, cu, cv)`.

Pack ids into one `long` (`face << 56 | a << 28 | b`, flat face = 0x7F with
sign-extended 28-bit coordinates) so cache, region and eviction are
world-agnostic.

## Exact enumeration

BFS from the eye's cell over 4-neighbours; accept a cell when its centre is
within `radius + cellDiagonal` of the eye, measuring **chord** distance
between unit directions times R on a planet (`acos(dot)` loses precision at
1.5 mrad on a 100 km sphere) and horizontal distance on a flat world. Cap the
fill at 64 k cells as a safety net. Re-run only when the eye moves a quarter
plot or the radius changes — not while plots are pending; the gather loop
re-requests whatever is missing anyway.

Verify a new enumeration in Python: dense-sample the disc (3 m pitch), map to
cells, and assert the flood fill is a superset at a face centre, a face edge,
a corner and 30° latitude; then walk 60 × 1 m from a corner and assert no
in-range cell leaves the region.

## Uniform density on a cube-sphere

Cell area `dA = R² du dv / (1+u²+v²)^{3/2}` varies ~5× from centre to
corner. Expected count `= perPlot · dA / size²`, floor it and add one with
probability of the fraction. Corners then contain more, smaller plots with
fewer plants each; the density per square metre is constant.

## Ground finding

Positive density is solid. From a start point in open air, march along the
"down" direction (−Y or −radial) with `step = clamp(-d · 0.5, 0.25, 24)`; the
fields here are `height − y` plus bounded detail, so `|d|` is roughly the
distance to ground and the walk converges in ~10 samples. Bisect the last
air/solid pair 8 times, then `normal = -gradient`. The planet's search band
is `[R + minH, R + maxH]` from `TryGetSurfaceBand`; the flat band from
`TryGetHeightBounds`. Start-inside-solid means an overhang roof: skip the
candidate. A long step can skip a thin bridge and land the plant under it —
rare, accepted.

Sample with `filterWidth = cellSize` (LOD0). Coarser rings differ by less
than the sink depth and only far away.

## Spacing and clumping

Uniform random points inside a plot cluster and gap; acceptable for ground
cover, not for trees. Options, cheapest first:

1. **`plotChance` and a small `perPlot`** — stands rather than a carpet.
2. **Jittered grid inside the plot**: `k×k` cells, one candidate per cell at a
   random offset. Blue-ish noise, deterministic, no rejection.
3. **Poisson disk (Bridson)** inside the plot: background grid with cell
   `r/√2`, active list, `k = 30` tries in the annulus `[r, 2r]`, O(n). Seed
   the first point from the plot RNG. Cross-plot spacing is not enforced;
   with `r < size/4` the seams are invisible.
4. **Noise masks**: multiply the expected count by a region-scale fbm (forests
   vs clearings) or by biome weight (`BiomeDensityField.ComputeWeights`), or gate on
   `SurfaceHardness` (no ferns on rock).

## Filters

`minUpness` compares `dot(normal, up)` (radial on a planet) with a cosine;
0.86 ≈ 30°. Height limits are relative to the nominal sphere on a planet.
Sink the base by `sink · scale` so a slope never shows a floating root.

## Threading

Workers read only a `BuildContext` snapshot (species numbers, planet
parameters, filter width, the field reference) captured on the main thread;
the density field is thread-safe by project contract (chunk meshing already
runs it on workers). Results carry the generation they were built for and
are dropped if `ClearCache` bumped it. `OnDisable`, `OnDestroy` and
`AppDomain.DomainUnload` stop the workers; join with a short timeout.

## Eviction

Keep every plot in the region; evict others only above `maxCachedPlots`.
Clearing the cache on a cap was the old bug: the forest vanished and trickled
back over ten frames every time the cap was hit.
