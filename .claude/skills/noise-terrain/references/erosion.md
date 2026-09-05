# Erosion

Two questions before writing any erosion code:

1. **Is it a heightmap?** Real erosion simulation operates on a 2D height grid.
   This project's world is an *infinite, unbounded, LOD-streamed density
   field*; there is no grid to erode. Erosion here is therefore either
   (a) *erosion-like noise* (derivative-weighted fBm, ridged feedback, striation
   terms — see `noise-recipes.md`), which is a pure function of position and
   works at every LOD, or (b) an **offline** pass over a finite region baked into
   a texture that a field samples. Choose (a) unless a hero area justifies (b).
2. **Does the result need to be a pure function of position?** A simulation is
   path-dependent by nature. Baked textures are fine; running a simulation
   inside `Sample` is not.

## Particle (droplet) hydraulic erosion

Cheap, good-looking, the standard first choice for heightmaps.

State per droplet: position, velocity, water, sediment. Per step:

```
g = gradient(height, pos)                 # bilinear
dir = lerp(dir, -g, 1 - inertia); normalize
pos += dir
Δh = height(pos) - height(oldPos)
capacity = max(-Δh, minSlope) * speed * water * capacityFactor
if sediment > capacity or Δh > 0:        # slowing down / going uphill
    deposit = (Δh > 0) ? min(Δh, sediment) : (sediment - capacity) * depositRate
    height(oldPos) += deposit (bilinear)
else:
    erode = min((capacity - sediment) * erodeRate, -Δh)
    remove `erode` from a radius around oldPos, weighted by distance
speed = sqrt(max(0, speed² + Δh * gravity))
water *= 1 - evaporate
stop when water ≈ 0, off-map, or max steps
```

Typical values: 30–50 k droplets for a 512² map, 30–64 steps each, inertia
0.05, capacity factor 4, min slope 0.01, erode 0.3, deposit 0.3, evaporate
0.01, gravity 4, erosion radius 3. Erode at the *previous* position so a
droplet does not dig itself into a pit. A light Gaussian blur afterwards hides
grid noise at low resolutions.

Variant (Job Talle): treat droplets as snowballs with normal-based rates —
`deposit = sediment * depositionRate * n.y`,
`erode = erosionRate * (1 - n.y) * min(1, i * iterationScale)` — and stop when
the normal points straight up. Same character, fewer parameters.

## Grid (virtual pipes) hydraulic erosion — GPU

Mei/Decaudin/Hu 2007, Jákó 2011. Per cell: terrain height `b`, water `d`,
suspended sediment `s`, outflow flux to four neighbours `f`. Each step:

1. Rain: `d += r * Δt`.
2. Flux: `f_i = max(0, f_i + Δt * A * g * Δh_i / l)` with `Δh_i = (b+d) -
   (b_i+d_i)`; scale all four by `K = min(1, d*l² / (Σf * Δt))` so a cell
   cannot lose more water than it has.
3. Water update from net flux; velocity from the flux differences.
4. Capacity `C = Kc * sin(tilt) * |v|` (clamp `sin(tilt)` to a minimum so
   flats still carry); if `C > s` erode `Ks (C - s)` from `b`, else deposit
   `Kd (s - C)`.
5. Advect sediment semi-Lagrangian: `s(p) ← s(p - v Δt)`.
6. Evaporate: `d *= 1 - Ke Δt`.

Thermal erosion (talus): for each cell, move material to lower neighbours when
the slope exceeds the talus angle, `Δ = Δt * Kt * (h - h_i - talus)`, spread
proportionally over the neighbours that exceed it. Runs in the same pass; it is
what turns needle-thin ridges into scree slopes.

This maps to compute shaders one texture per quantity, ping-ponged. Unity
reference: `bshishov/UnityTerrainErosionGPU`.

## Which one

| | droplets | pipes |
|---|---|---|
| look | gullies, fans, dendritic valleys | broad rivers, lakes, deltas |
| cost | CPU seconds for 512² | GPU real-time |
| control | droplet count, radius | rain map, evaporation |
| determinism | seeded droplet order | deterministic per step |

## Using a baked result in this project

Bake to a height *delta* texture in a fixed world rectangle, sample it in a
`DensityField` as `HeightAt(x,z) += delta(x,z) * fade(edge)`, with the fade to
zero over ~10 % of the rectangle so the seam is invisible. It is still a pure
function of position, still band-limitable (mip the texture, pick the mip by
`fw`), and the GPU sampler needs a matching `GpuFieldType` that binds the
texture — do that or the whole world falls back to CPU meshing.

## Sources

- Mei, Decaudin, Hu, *Fast Hydraulic Erosion Simulation and Visualization on GPU* (2007).
- B. Jákó, *Fast Hydraulic and Thermal Erosion on the GPU* (CESCG 2011).
- J. Talle, *Simulating hydraulic erosion* (particle/snowball variant).
- dandrino, *terrain-erosion-3-ways* (simulation, ML, and noise compared).
