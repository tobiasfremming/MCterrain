# L-system techniques

Vocabulary from Prusinkiewicz & Lindenmayer, *The Algorithmic Beauty of
Plants* (ABOP), and what came after. Fragments use this repo's cpfg syntax.

## Production types

**Context-free (D0L)** — one symbol, one rule. Fractal, regular, fine for
crystals and reference shapes:

```
#axiom: F
F -> F [ +(25) F ] F [ -(25) F ] F
```

**Parametric** — modules carry numbers; rules compute with them and guard on
them. This is the workhorse; everything realistic uses it:

```
#define SH 0.94   // segment shrink
#define TP 0.90   // width taper
A(l,w) : l >= 0.1 -> F(l) !(w*TP) [ &(30) /(137.5) B(l*0.6, w*0.7) ] A(l*SH, w*TP)
A(l,w) : l <  0.1 -> F(l) L(l*2)
```

**Stochastic** — several rules for one predecessor with relative weights.
Randomise *rules*, not the interpretation, so structure varies and not just
angles:

```
B(l,w) : l >= 0.1 : 0.55 -> F(l) [ +(35) B(l*0.7,w*0.7) ] B(l*0.85,w*0.8)
B(l,w) : l >= 0.1 : 0.30 -> F(l) B(l*0.9,w*0.85)
B(l,w) : l >= 0.1 : 0.15 -> F(l) [ -(35) B(l*0.7,w*0.7) ] [ +(35) B(l*0.7,w*0.7) ]
B(l,w) : l <  0.1 -> F(l) L(0.3)
```

Every variant needs its own guard, or the terminal rule never wins the draw.

**Context-sensitive (IL)** — the rule sees neighbours: `A < B > C -> …`.
Models signals travelling along the plant: flowering waves, acropetal
(base → tip) hormone propagation, basipetal die-back. `#ignore: + - [ ]` lets
matching look through turtle symbols. Use sparingly; it is what makes
derivation O(n·context) and it is rarely needed for static meshes.

**Environmentally sensitive / open L-systems** — a query module (`?P(x,y,z)`
in cpfg) is filled in by the environment each step: the plant can test
light, obstacles, ground, and react (prune, bend, stop). This repo has no
query modules; the equivalent is to decide per *instance* at bake or scatter
time (species by biome, lean by slope) and keep the grammar closed.

## Turtle geometry that reads as a plant

| Effect | Command pattern |
|---|---|
| Sibling spread out of plane | `/(137.5)` between successive laterals (golden angle, phyllotaxis) |
| Droop under weight | `&(ARCH)` per segment, ARCH 3–6°, along a frond or a hanging branch |
| Reach for light | `^(k)` per segment on the main axis, `$` to roll upright after twisting |
| Wind/lean whole plant | one `&(a)` after the axiom, before the trunk |
| Zig-zag twigs | alternate `+(a)` / `-(a)` per segment (sympodial look) |
| Crown / rosette | `C(n) -> [ /(137.5*n) &(OUT) A(...) ] C(n-1)` shedding one frond per step |
| Terminal cluster | `K(w)` marker; consumer draws a bud, flower or cap |

Tropism in ABOP is a vector `T` and a bend `α = e·|H × T|` applied per
segment; the per-segment pitch above is the discrete version and is
sufficient.

## Growth control

- **Apical dominance**: keep the apex's `(l, w)` decay gentler than the
  laterals'. Laterals at 45–60° for young shoots, relaxing to 20–30° higher
  up gives a natural crown taper.
- **Pipe model (Murray's law)**: `w_p^n = Σ w_c^n`. With two equal children
  and n = 2, each child is `w_p / √2 ≈ 0.707 w_p`. Use 0.7 for symmetric
  forks; asymmetric forks (0.9 / 0.5) look more natural.
- **Segment length decay** `SH` 0.9–0.96 with a `MIN` cut is what fixes
  iteration count: steps = `log(MIN / l0) / log(SH)`; set `#iterations` to
  that plus one.
- **Delay modules**: `D(n) : n > 0 -> D(n-1)` / `D(0) -> A(...)` stagger
  laterals so they are younger than the apex — sympodial trees need it.

## Variation without new grammars

Vary per instance at bake time (`seed`), per species with `#define`
overrides (fork angle, droop, taper), and per placement at scatter time
(scale 0.8–1.25, lean, yaw). Eight baked variants plus scatter jitter reads
as endless; eight identical variants reads as a field of clones.

## Level of detail

1. **Mesh pruning by width quantile** (`keepFraction`): keep the thickest X %
   of nodes; a pruned node drops its subtree. Leaves stay (they *are* the
   silhouette); thin only where leaf cards dominate triangle count.
2. **Ring segments** 6 → 4 → 3 on tubes.
3. **Impostor card** beyond ~120 m: an atlas of the baked mesh from 12 angles
   (`vegetation-scatter`).
4. **Grammar-level LOD** (derive fewer iterations for far instances) changes
   the plant; avoid it for meshes, fine for SDF spires that are re-evaluated
   per LOD anyway if the derivation is shared.

## Converting a skeleton

- **Tubes**: one ring per *node* (not per segment) so forks connect;
  rotation-minimising frames transported from parent to child stop barber-pole
  twist; wind stiffness = `1 - depth / maxDepth` baked into UV2.
- **Leaf cards**: markers → quads oriented by the marker's turtle frame,
  optional `eulerOffset`, size from parameter or turtle width.
- **SDF**: capsules per segment, radius = `0.5 · width · scale`, smooth union
  (`smin`, k ≈ blend radius) with each other and with the ground, tip blobs
  on `K` markers. Bucket capsules in a 2D grid so a sample tests a few, and
  keep the structure inside its plot (scale down to fit) so neighbours never
  need to be consulted and `TryGetHeightBounds` stays true.

## Classic grammars to start from (ABOP figures)

- Fig 1.24 (a–f): 2D bracketed trees; (d) `X -> F[+X]F[-X]+X`, `F -> FF`, 20°.
- Fig 2.6: 3D bush with `!`, `'`, `/`: `A -> [&FL!A]/////'[&FL!A]///////'[&FL!A]`.
- Fig 2.8: monopodial "Honda" tree, parametric: `A(l,w) -> !(w)F(l)[&(a0)B(l*r2,w*wr)]/(d)A(l*r1,w*wr)`.
- Fig 2.7: sympodial tree; Fig 2.9: ternary branching with tropism.

They paste in verbatim (single-character symbols) and are the fastest way to
sanity-check the engine and your eye.

## Sources

- Prusinkiewicz & Lindenmayer, *The Algorithmic Beauty of Plants* (1990; free at algorithmicbotany.org).
- Prusinkiewicz et al., *L-systems in Geometric Modeling* (arXiv 1008.1664).
- Dave Mount, CMSC 425 lecture 13, *Procedural Generation: L-Systems*.
- A. Pike, *Modeling plants with Lindenmayer systems* (practical tuning notes).
