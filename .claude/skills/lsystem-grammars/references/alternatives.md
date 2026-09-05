# Alternatives to grammars

Both produce the same thing a grammar does — a branching skeleton — so they
can feed `LSkeleton` and everything downstream unchanged. Choose by what
decides the shape: *rules* (grammar), *space* (colonization), or *competition
over time* (self-organising).

## Space colonization (Runions et al. 2007)

Branches grow toward a cloud of attraction points and consume them. Breaks
the symmetry L-systems tend to have; excellent for crowns, roots, shrubs,
lightning, blood vessels, river networks (run it on a plane).

```
attractors  = N points inside a crown volume (sphere, ellipsoid, or a
              silhouette you drew); correct for volume so density is uniform
              (r = R * sin(u*π/2)^0.8 for a sphere, or rejection sample)
nodes       = [root]
repeat until no attractors or max iterations:
    for each attractor a: find the nearest node n within attractionRadius
                          (skip if none); add normalize(a - n) to n.dir
    for each node n with any dir: child = n.pos + normalize(n.dir) * step
                                  (+ small random vector to break ties)
    remove every attractor within killRadius of any new node
thicken: post-order, radius_n = (Σ radius_child^k)^(1/k), k ∈ [1.5, 3]
```

Constraints: `step < killRadius < attractionRadius`. Too few attractors or a
small attraction radius leave unreached points; a node attracted by two
opposite points oscillates unless the random nudge is present. Complexity is
attractors × nodes per iteration; a grid on the nodes makes it linear.

Feeding it in: build `LSkeleton` nodes/segments directly (parent index <
child index, widths from the thickening pass), add `L` markers at leaf nodes,
then the same `PlantMeshBuilder` and baker apply. Deterministic if the
attractor sampler uses `LRandom(worldSeed, instanceId)`.

## Self-organising tree models (Palubicki et al. 2009)

Buds compete for light or space each growth cycle; a bud that wins resources
extends, laterals form by apical control, weak shoots are shed. Produces
convincing whole trees and bushes across species from a handful of
parameters (light sensitivity, apical dominance, branch angle, shedding
threshold) and supports brushes and pruning as artist controls. It is a
simulation over cycles rather than a derivation, so it is a bake-time tool,
never a runtime one; the output is again a skeleton.

## When a grammar is still right

- The structure has a *pattern* (phyllotaxis, fronds, corals, crystals).
- You want textbook-verifiable behaviour and cheap determinism.
- You need it evaluated per plot on a worker thread at runtime (the grove
  field): derivation is fast and allocation-free after warm-up; space
  colonization is not.

## When to switch

- A tree crown looks regular no matter how much `rand()` you add.
- The shape must fit a volume or avoid obstacles (colonization takes the
  target volume as input; a grammar cannot see it).
- Roots, veins, lightning: colonization or DLA, not a grammar.

## Sources

- Runions, Lane, Prusinkiewicz, *Modeling Trees with a Space Colonization Algorithm* (EG NPH 2007).
- Palubicki et al., *Self-organizing tree models for image synthesis* (SIGGRAPH 2009).
- ciphrd, *Generating a 3D growing tree using a space colonization algorithm* (implementation notes).
