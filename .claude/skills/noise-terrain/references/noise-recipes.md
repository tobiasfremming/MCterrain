# Noise recipes

Formulas and parameters for the constructions the skill points at. Notation:
`noise(p)` is a gradient noise in roughly `[-1, 1]`; `p` is world position in
metres; `fw` is the sample spacing passed for band-limiting.

## fBm (fractional Brownian motion)

```
fbm(p, H, octaves):
    G = 2^(-H)            # gain per octave; H = Hurst exponent
    f = 1, a = 1, t = 0
    for i in octaves:
        t += a * noise(f * p)
        f *= lacunarity   # 2.0 nominally, 1.9–2.1 in practice
        a *= G
    return t
```

- `H = 1` (gain 0.5): natural isotropic terrain — spectral roll-off of
  −9 dB/octave, which is what real mountain profiles measure. Higher peaks are
  also wider at the base.
- `H = 0.5` (gain 0.707): rougher, "brown"; `H → 0` (gain → 1): pink, chaotic.
- Detune the lacunarity (1.99, 2.01) or rotate the domain per octave so octave
  lattices never align; aligned octaves show a visible grid at zoom.
- Octaves needed ≈ `log(extent / smallestFeature) / log(lacunarity)`. With
  band-limiting, coarse LODs drop the fine octaves for free, so the count is
  a LOD0 budget only.
- Normalise by `Σ a` when a `[0, 1]` range is needed downstream.
- Use *different seeds or fixed offsets* for independent fields (elevation vs
  moisture vs warp). Correlated fields make biomes follow ridgelines.

## Ridged multifractal (Musgrave)

```
ridged(p, octaves, offset=1.0, gain=2.0):
    weight = 1, f = 1, a = 1, t = 0
    for i in octaves:
        s = offset - abs(noise(f * p))
        s = s * s                       # sharpen the ridge
        s *= weight
        weight = clamp(s * gain, 0, 1)  # feedback: detail follows existing ridges
        t += s * a
        f *= lacunarity; a *= 0.5
    return t
```

`TerrainNoise.RidgedFbm` is this form. The feedback is the point: fine octaves
only add where a coarse ridge already exists, so valleys stay clean and peaks
get craggy. Without it you get `1 - abs(fbm)`, which is uniformly creased.
`abs(noise)` without the `1 -` is *billowy* terrain (rounded, eroded lumps).

## Hybrid multifractal (heterogeneous terrain)

Weight each octave by the *value so far* so low areas stay smooth and high
areas get rough — the Musgrave "HeteroTerrain" look:

```
t = noise(p) + offset
weight = t
for i in 1..octaves:
    weight = min(weight, 1)
    signal = (noise(f * p) + offset) * a
    t += weight * signal
    weight *= signal
```

## Derivative-weighted fBm (Quilez "erosion-like")

Use a noise that returns its analytic gradient `(n, d)` and damp octaves on
steep accumulated slope:

```
d_sum = 0, a = 1, t = 0
for i in octaves:
    (n, d) = noised(f * p)
    d_sum += d
    t += a * n / (1 + dot(d_sum, d_sum))
    f *= 2; a *= 0.5
```

Slopes become smooth and flats stay detailed, which is how real weathering
distributes detail. Analytic derivatives also give normals without resampling;
central differences cost five extra evaluations. Prefer quintic fade curves
(`6t⁵−15t⁴+10t³`) so the second derivative is continuous — cubic fades show
faceting in the derivative-driven terms.

## Domain warping

```
q = (fbm(p + o1), fbm(p + o2))
r = (fbm(p + k*q + o3), fbm(p + k*q + o4))
h = fbm(p + k*r)
```

Fixed offsets `o1..o4` (e.g. (5.2, 1.3), (1.7, 9.2), (8.3, 2.8)) make 2D
displacement out of 1D fbm calls; `k ≈ 4` is a strong warp, `k ≈ 1` a gentle
one. One warp level looks tectonic, two look organic and ropey. Feed `|q|` and
`r.y` to colour or biome selection: the intermediates are free.

In 3D density fields, warp with low-frequency noise (`ws += 8 * noise3(ws *
0.004)`) *before* the octave sum. Large warp amplitude means more caves and
tunnels; moderate means ropey overhangs. Apply y-banding (shelves) on the
pre-warp coordinate for crisp strata, on the post-warp one for melted, sagging
strata.

## Redistribution, terraces, islands

- Valleys and sharp peaks: `e = pow(e * 1.2, k)`, k in 1.5–3. Only on a
  normalised `[0,1]` height.
- Terraces: `round(e * levels) / levels`, blended in by a mask so the whole
  world is not stepped. Softer: a smoothstep staircase.
- Island / falloff: `e = lerp(e, 1 - d, mix)` with `d = 1 - (1-nx²)(1-ny²)`
  (square bump) or `min(1, (nx²+ny²)/√2)`.
- Sea level: a hard floor `density += saturate((floorY - y) * 3) * 40` gives
  bedrock and stops a 3D field looking like a sponge.

## 3D density construction (GPU Gems 3 style)

```
density = -y                            # ground plane
ws = p + warp
density += noise(ws * 4.03) * 0.25
density += noise(ws * 1.96) * 0.50
density += noise(ws * 1.01) * 1.00
density += saturate((hardFloorY - y) * 3) * 40
```

In this repo the equivalent is `HeightAt(x,z) - y + Extra3D(x,y,z)` where
`Extra3D` is bounded (rule 4 in `SKILL.md`). Caves come from explicit SDF
carves (`TerrainModificationCache.CarveSphere`) or from a *bounded* 3D term
gated to a wall band, never from large-amplitude 3D noise. A "never-ending
cave network" is `density = 12 + noise octaves` with no ground plane — fun,
but it has no floor, so it is not a world.

## Biome blending

Softmax over per-biome affinity noises at region scale (~1000 m), sharpness
~150 so the blend is effectively an argmax with a few metres of soft edge.
Weights sum to 1, so coverage holes are impossible; blend *densities*, not
heights, and every watertightness guarantee survives. Bake weights into
vertex colours for the shader. On a planet, select from `normalize(p) * R`
(position on the sphere), not `p`: selecting from the raw position drifts
with altitude and stacks biomes vertically around every boundary.

Classic 2D alternative: elevation and moisture as two independent fbms,
`pow` redistribution on elevation, then a lookup table
`biome(e, m)` — beach below 0.12, snow/tundra/bare above 0.8 by moisture, and
so on. Good for maps; less good for a 3D density world because moisture has
no meaning under an overhang.

## Planet wrapping

Sample 3D noise on the sphere (`dir * R`) for anything global; wrap a
heightfield only via a triplanar blend of three axis-aligned evaluations
weighted by `|dir|` components — that keeps the field continuous across cube
faces (a discrete face pick cracks the mesh). Precision: at R = 100 km float
ULP is 8 mm, fine below ~10⁷ m; if it ever bites, split coordinates into an
exact integer part plus a fraction before the noise's floor/frac, do not
float-origin rebase (that broke edits and probes here once).

## Object placement from noise

For "where do trees go", high-frequency noise plus local-maximum detection
gives a passable blue-noise pattern, but Poisson disk sampling (Bridson: grid
cell `r/√2`, `k = 30` tries, O(n)) is better and deterministic per cell. See
the `vegetation-scatter` skill.

## Sources

- I. Quilez, *fBm*, *Domain warping*, *Noise derivatives* (iquilezles.org).
- F. K. Musgrave, *Procedural Fractal Terrains* (Texturing & Modeling ch. 16).
- Red Blob Games, *Making maps with noise functions*.
- GPU Gems 3 ch. 1, *Generating Complex Procedural Terrains Using the GPU*.
- G. de Carpentier, *Scape: procedural basics* (ridged / billowy / IQ noise).
