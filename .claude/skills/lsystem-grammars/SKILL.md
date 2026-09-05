---
name: lsystem-grammars
description: Author, tune and debug L-system grammars and their consumers — plants, trees, shrubs, ferns, coral, crystals, spires, cave and tunnel networks, rivers — using parametric, stochastic and context-sensitive productions, tropism, apical control, golden-angle phyllotaxy and skeleton-to-mesh or skeleton-to-SDF conversion, with this project's cpfg-style engine in Assets/TerrainGen/Scripts/LSystem (LSystemGrammarAsset, LSystemRewriter, TurtleInterpreter, LSkeleton, PlantProfile, PlantPrototypeBaker). Use for any request like "make a new plant", "the tree looks like a pin cushion", "add a fern/bramble/cactus", "the grammar doesn't terminate", "write a grammar for X", "grow caves with an L-system", or when choosing between L-systems and space colonization. Trigger even when the user just says "plant" or "tree" in this repo.
---

# L-system grammars

An L-system is a **shape with a topology**: it produces a skeleton (nodes,
segments, markers), and something else turns the skeleton into geometry. Reach
for one when the thing you want branches; reach for noise (`noise-terrain`)
when it has a height.

Read first, every time, before writing a grammar in this repo:

- `Assets/TerrainGen/Scripts/LSystem/README.md` — the syntax (cpfg notation,
  turtle commands, expressions, determinism).
- `Assets/TerrainGen/Scripts/LSystem/COOKBOOK.md` — the traps: termination one
  iteration early, arity, stochastic guards, `!(w)` *sets* width, `//` vs `/`,
  thread-safety, buffer ownership.

Then the references here when the task calls for them:

- `references/techniques.md` — the design vocabulary: parametric, stochastic
  and context-sensitive productions, tropism, apical dominance, phyllotaxis,
  pruning and environment, LOD and variation, with grammar fragments.
- `references/alternatives.md` — space colonization and self-organising tree
  models, when they beat a grammar, and how to feed their output into the same
  `LSkeleton` pipeline.

## The pipeline, and where you work

```
grammar text ──parse──▶ LSystemGrammar ──rewrite(seed)──▶ word ──turtle──▶ LSkeleton ──▶ consumer
   (asset)                                                              mesh (PlantMeshBuilder)
                                                                        SDF   (LSystemGroveField)
                                                                        props (markers)
```

- **Grammar** (`Config/**/*Grammar.asset`, edit the `source` text): shape only.
- **Profile** (`PlantProfile`): what symbols *mean* — stem radius scale,
  taper, which marker is a leaf quad, colours. Grammar and profile are
  separate assets on purpose; swapping one leaves the other valid.
- **Prototype set** (`PlantPrototypeBaker`): N seeds × 3 mesh LODs × an
  impostor atlas, baked once. Runtime never derives a grammar again.
- **Consumer of markers**: any symbol the turtle does not know becomes a
  marker carrying its parameters. A new decoration is one character in the
  grammar plus one `case` in the consumer, never a new turtle command.

## How to write a grammar that looks like a plant

1. **Start from the architecture, not the rules.** Decide the growth habit in
   words: monopodial (one trunk, side branches: conifers), sympodial (apex
   ends, laterals take over: most broadleaf trees), rosette/crown (ferns,
   palms), creeping (brambles). Each habit is a different axiom shape and a
   different place for `[ ]`.
2. **Parametrise length and width, carry them in the module.**
   `A(l,w) -> F(l) !(w*TP) [ +(a) A(l*SH, w*TP) ] ...` — taper and shrink
   come from the parameters, never from `!` or `"` alone (they *set*).
3. **Terminate by parameter, one generation early.** `A(l,w) : l < MIN -> F(l)
   K` plus `#iterations` = steps-to-threshold + 1. Count leftover apex symbols
   after deriving; it must be zero, or they become stray markers.
4. **Randomise everything that can vary**, with guards on every variant:
   angles `+(a + rand(-8, 8))`, lengths `l * rand(0.85, 1.05)`, and weighted
   alternatives `A(l,w) : l >= MIN : 0.7 -> …` / `: 0.3 -> …`. A deterministic
   grammar bakes eight identical variants; the first fern did exactly that.
5. **Golden angle between siblings**: `/(137.5)` (or `/(137.5 + rand(-10,10))`)
   keeps successive branches out of one plane. It is the single cheapest
   realism win. Roll (`/ \`) after every branch, pitch (`& ^`) for droop.
6. **Tropism** (bend toward a direction) is a small pitch per segment:
   gravity droop `&(ARCH)` on ferns and willow, phototropism `^(k)` on
   saplings. Accumulated over 15–20 segments it *is* the silhouette.
7. **Apical dominance**: the main apex keeps a longer step and larger width
   than laterals (`A(l*0.95, w*0.9)` vs `B(l*0.7, w*0.6)`), and laterals
   start at a wider angle that relaxes with age.
8. **Width follows the pipe model**: at a fork, children's widths satisfy
   `w_parent^n = Σ w_child^n` with `n ≈ 2–3`. Cheap version: `TP ≈ 0.7` per
   split on both children.
9. **Leaves go where twigs end**: emit `L(size)` markers on terminal rules and
   optionally along the last segments; size by parameter so `PlantProfile` can
   read it (`sizeFrom = MarkerParam`).

## Budget before beauty

`PlantPrototypeBaker.kTriangleBudget` is 20 k triangles per LOD0 variant for
anything scattered; a hero asset may exceed it deliberately. Branching grammars
grow exponentially: derivation length, not iteration count, is the budget
knob (`MaxModules` caps at 250 k and returns the last complete generation).
Baked assets serialise as text — a 3 LOD × 8 variant tree is ~10 MB, a
bramble 18 MB; `Config/Flora/Prototypes/` is gitignored for that reason.

Mesh LODs prune by `keepFraction` (a width *quantile*, so one number works on
a 10 m tree and a 0.3 m herb). Pruning deletes whole branches and changes the
silhouette, so LOD swaps are kept small and far; the far LOD is an impostor
card (`vegetation-scatter` skill).

## Beyond plants

- **Caves and tunnels**: grammar → skeleton → capsule SDFs unioned into a
  `ModifiedDensityField` (subtract) or a field of its own (add, as the grove
  does). The grove field is the reference: plots keyed by hash, structures
  scaled to fit half a plot so `TryGetHeightBounds` stays honest, CPU atlas of
  capsules uploaded for GPU evaluation.
- **Rivers, crevasses, lightning, blood vessels**: same skeleton, different
  consumer. Only the turtle settings change (heading along the ground plane,
  roll disabled).
- **Crystals, coral**: use markers (`K`, `C`) and let the consumer place
  primitives; keep the grammar shape-only.

## Debug checklist

| Symptom | Cause |
|---|---|
| Rule never fires | arity mismatch (`A` vs `A(1)`) or a guard that excludes it |
| Stray leaves at branch tips | apex symbols survived the last generation; raise `#iterations` by one |
| Every branch equally thick | `!(w)` used as a scale; carry width in the module |
| Fan in one plane / "pin cushion" | no roll between siblings; add `/(137.5)` |
| Identical variants | no `rand()` and no weighted productions |
| Runaway word / truncated | exponential rule with too many iterations; check `Truncated` |
| Grammar edits do nothing in play | prototypes are baked; rebake |
| Different plant each run | `UnityEngine.Random` sneaked in; use the rewriter's seeded stream |

## Report

Name the architecture chosen, the grammar file, how many iterations and why,
the LOD0 triangle count per variant, and which of the eight rules above you
skipped and why.
