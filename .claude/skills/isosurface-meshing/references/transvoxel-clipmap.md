# Transvoxel and clipmap conventions (verified)

These were established 2026-07 by prototyping against the project's own
tables and are the ones the code uses. Verify against the code before
asserting a line number; the conventions themselves have not changed.

## Marching cubes

- Density convention: `Sample − iso < 0` is *air* (the corner bit is set when
  negative); positive is solid. Heightfields return `h − y`.
- Vertices are deduplicated by an edge-keyed cache (≈4× fewer vertices and
  gradient calls than naive per-cell emission). Normals come from
  `DensityField.Gradient` at the vertex position at the chunk's spacing.
- Vertex colour: `.rgb` biome weights (sharpened in the shader), `.a` baked
  ambient occlusion `0.25 + 0.75·clamp01(−Sample(p + n·2.5·step) / 2.5·step)`.
  Colours stay Float32 — 8-bit quantisation banded the biome blend.
- Winding: front face outward; the geometric normal from
  `Cross(v1−v0, v2−v0)` must agree with the vertex normals, or the surface
  reads as hollow under backface culling.

## Transvoxel transition cells (Lengyel)

- Case index bits per full-resolution corner 0..8 (fig. 4.17):
  `{0x01, 0x02, 0x04, 0x80, 0x100, 0x08, 0x40, 0x20, 0x10}`, bit set when the
  density is negative.
- `TransitionVertexData`: both corner indices live in the **low byte**:
  `c0 = (v >> 4) & 0xF`, `c1 = v & 0xF`. The high byte is reuse data (unused).
- The **coarse** chunk owns transition cells. The full-res boundary face is
  left untouched; half-res vertices and the regular-mesh boundary vertices
  get the secondary offset (eq. 4.2: `w = cell/4`, linear falloff over one
  cell; eq. 4.3 tangent projection). Force the primary position (no offset)
  for any vertex within one cell of a face *without* a transition.
- Face bases must satisfy `U × V = outward normal`; then the table's invert
  bit is the only winding flip needed.
- Residual limitation: the case code comes from the nine full-res corners, so
  the coarse side's topology follows the fine field's signs. Under
  band-limiting the two fields can disagree in sign within the faded
  amplitude; keeping the fade band wide keeps that amplitude, and the risk,
  small.
- Corner sampling under band-limiting: full-res corners at spacing `s`,
  half-res corners at `2s`, welded against their own side
  (`GenerateTransitionFace`'s coarse corner sample).

## Clipmap

- Level-k chunks keep the cell count and cover `2^k` × the base size.
- Level-0 box tracks the player snapped to 2-chunk alignment; each parent
  box wraps its child, even-aligned, with ≥ 1-chunk margin. The window
  `[c − E/2 + 1, c − 1]` always holds an even slot for extent `E ≥ 6`; `E = 4`
  has zero slack against 2-step parity moves (verified by random search).
- A coarse face bordering four (2×2) fine chunks is watertight (verified).
- `IsDesired(key) = InBox(level, coord) && !CoveredByFiner(level, coord)`.
- Neighbour LOD difference is at most one level; chunks regenerate when
  `(level, needsMask)` changes.

## Staged swap

- A chunk whose key stops being desired is retired: kept rendering, removed
  from `_chunks`, its required covering set resolved by walking up (parent
  box) or down (eight children). No depth guard.
- Replacements generate with the renderer disabled while `_showBlockers`
  counts the retiring chunks over them; `SweepRetiring` releases a retiring
  chunk and reveals its covering set atomically once all of it exists.
- Retiring entries re-resolve against fresh boxes every recompute; same-key
  resurrection restores the old chunk.
- `_priorityKeys`: required keys of retiring chunks within 1.5 chunk sizes of
  the player sort to the front of the queue (player-adjacent swaps < 1 s).
- Verified: 0 holes / 0 overlaps at 180 m/s and under flip-flop movement,
  3 M+ probes.

## Async pipeline (`MCChunkManager`)

`_gpuPending → _gpuInFlightBatches (AsyncGPUReadback, ≤ 3) → _readyForMeshing
→ _inFlight (Task.Run)`; admission cap 64; `_gpuGeneration` drops stale
readbacks after a config change. Dirty (edit) jobs claim their flag at
dispatch, so stamps during a build re-queue. Apply order is FIFO (a backwards
iteration once starved the oldest build). Errored builds re-queue via the
dirty path so their claim is not lost. Per-chunk raw base density is cached
so edit-only rebuilds never re-dispatch to the GPU.

## Colliders

LOD0 only. `Physics.BakeMesh` on a task chained per chunk; the previous
cooked mesh stays bound until the bake lands (a full regenerate can hit the
chunk the player stands on). Procedural meshes are `DontSaveInEditor` and
destroyed in `OnDestroy`; unmarked chunk meshes once serialised 2 859 of them
into a 203 MB scene.

## Domain reload

`ModifiedDensityField` instances (`HideAndDontSave`) survive a reload with
their plain-C# `caches` array nulled. `IsValid` + rebuild in `EnsureField`,
null guards elsewhere. Any runtime-created ScriptableObject holding plain
C# references needs the same pattern.
