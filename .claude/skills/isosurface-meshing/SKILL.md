---
name: isosurface-meshing
description: Work on the voxel/isosurface side of this project — marching cubes, Transvoxel LOD transition cells, the clipmap of nested chunk rings, watertightness at LOD seams, vertex normals from field gradients, chunk streaming and budgets, GPU compute meshing and readback, terrain edit caches and colliders — in Assets/TerrainGen/Scripts/MarchingCubes and Scripts/Terrain (ChunkMesher, MCChunkManager, MarchingChunk, TransVoxelTables, TerrainGpuMesher, TerrainModificationCache). Use for cracks or seams between LOD rings, holes, floating shelves, chunks that never appear or appear late, "the terrain pops when I move", meshing performance, collider cooking stalls, or any change to chunk size, LOD levels or the streaming queue. Trigger on "marching cubes", "transvoxel", "chunk", "LOD ring", "seam", "watertight".
---

# Isosurface meshing

The terrain mesh is the zero level set of a density field, extracted per
chunk by marching cubes, with Transvoxel transition cells stitching a
**clipmap** of rings whose cells double in size per level. Every part of this
exists to keep one property: **the union of all chunks is watertight while
the player moves**. Read `references/transvoxel-clipmap.md` for the verified
conventions before touching tables, corner orders or the ring logic.

## Invariants

1. **Same field, same spacing, same value.** A vertex on a shared face is
   computed by two chunks; both must sample the identical field at the
   identical filter width and get identical corner densities, or the edge
   crossings disagree and the seam opens. Band-limiting is a function of
   spacing only; Transvoxel transition cells sample their full-res corners at
   the fine spacing and their half-res corners at the coarse spacing, and weld
   each set against its own side.
2. **`Gradient` overrides return exactly the central-difference value.**
   Normals feed the Transvoxel secondary-offset projection; a cheaper formula
   that differs by 1e-4 nudges seam vertices apart.
3. **Exact 2:1 between adjacent levels.** Resolution per level =
   `cellsPerChunk >> level` is gone; the clipmap keeps the cell *count* and
   doubles the cell *size*. Boxes are built bottom-up, even-aligned, with at
   least one chunk of margin, so every LOD interface lies on whole chunk faces
   of both levels. `chunksPerLevel` must be even and ≥ 6; 4 is provably
   impossible.
4. **Coarse owns the transition.** The coarse chunk generates transition
   cells on faces that border a finer level; the fine side is untouched. Case
   bits, vertex decode and winding conventions are in the reference; they
   were wrong four different ways once and were verified watertight by a
   Python prototype that parsed the real C# tables.
5. **Visibility is monotone.** Chunks replaced by another level are *retired*
   (kept rendering) until every replacement covering them is generated, then
   swapped atomically. Never depth-guard the covering resolution; truncated
   lists produced visible overlaps.
6. **Meshing is pure and off-thread.** `ChunkMesher.Build(ChunkMeshJob)` runs
   on `Task.Run` workers with per-job buffers; the main thread only uploads.
   Stale results (boxes or transition needs changed mid-build) are dropped and
   re-queued at the front.

## Where the time goes, and the knobs

| stage | cost driver | knob |
|---|---|---|
| density fill | field samples per chunk (33³ + transition faces) | GPU compute (`TerrainDensity.compute`) when every biome is a GPU leaf; `TryGetEmptySkip` culls ~80 % of a cubic clipmap |
| marching | cells with sign changes | GPU mesher (`TerrainMesh.compute`, direct buffer upload) or CPU with edge-keyed vertex dedup |
| upload | `SetVertexBufferData` + bounds | pre-packed vertex layout, `DontValidateIndices`, `generationBudgetMs` (6 ms) |
| colliders | PhysX cook per LOD0 chunk | `Physics.BakeMesh` off-thread, chained per chunk; LOD0 only; share the render mesh unless visual edits overlap |
| streaming order | nearest-first, `_priorityKeys` for player-adjacent swaps | job order affects latency only, never correctness |

Throughput is frame-rate bound by design (one GPU batch per `Update`, budget
per frame), so anything that lowers fps slows *generation*. Two known
external causes: thousands of baked chunk meshes serialised in the scene, and
GPU batches collapsing to one chunk when retiring keys fragment homogeneous
runs.

## Edits

`TerrainModificationCache` holds sparse trilinear voxel deltas (short-term
dict → persistent after idle), region occupancy for cheap rejection, a lock
for worker reads. `ModifiedDensityField` = base + visual + physical caches
for rendering, base + physical for colliders, so footprints never re-cook
physics. Deltas are **not** band-limited (authored size). `CarveSphere`
forces density to a sphere SDF for clean cavities. Edits dirty every level in
the padded AABB; dirty jobs are capped to half the worker slots so a sprint's
footprint stream cannot starve streaming, and visual-only re-dirties coalesce
over `visualEditRebuildInterval`.

## Diagnosing

- **Hairline cracks at ring boundaries** → band-limit disagreement or a
  `Gradient` override that is not exactly central differences. Toggle
  `TerrainNoise.kBandLimit` off (with the GPU twin) as the A/B: if cracks
  survive, the transition-cell code is at fault.
- **Whole faces missing** → transition needs mask stale; check `_generatedNeeds`
  versus `ComputeNeeds`.
- **Terrain changes shape per ring** → an octave above the band limit; widen
  the fade band, not the ring.
- **Chunks never appear / appear late** → `TryGetHeightBounds` too tight,
  admission cap, or a batch stuck needing readback.
- **Holes while moving fast** → covering resolution truncated or retire
  bookkeeping; the 1D state-machine simulation in the notes reproduces it.
- **Falls through the floor after a regenerate** → collider assigned before its
  bake landed; keep the old cooked mesh bound until `FinishColliderBake`.

Prototype every topology change in Python against the real tables (sphere
field, closed-mesh test: 0 open edges, 0 non-manifold, all six faces, corners,
mixed-LOD junctions) before touching C#. That test is the definition of done.
