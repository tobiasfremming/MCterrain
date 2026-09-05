# LOD and impostors

## Tiers

| tier | what | when |
|---|---|---|
| LOD0 mesh | full grammar sweep (tree ≈ 9.5 k tris) | near |
| LOD1/2 mesh | `keepFraction` width-quantile pruning, fewer ring segments | mid; swaps change the silhouette, keep them far or off (`useLod`) |
| impostor card | one quad, 12-frame atlas, camera-facing about the plant's up | beyond `impostorDistance` to `cullDistance` |
| nothing | | beyond `cullDistance` |

A card costs 2 triangles and one atlas fetch (two, blended). Trees can be
visible to 700 m for less than one LOD0 tree costs.

## Baking (`PlantPrototypeBaker.BakeImpostors`)

- Render each variant's LOD0 mesh from `N = 12` angles around its up axis into
  one RGBA atlas: row per variant, column per frame, 128 px frames
  (1536 × 1024 for 8 variants). Written as a PNG next to the set (text
  serialisation would make a sub-asset texture 16 MB of YAML).
- Camera at angle `θ_i = 2πi/N`, direction `(sin θ, 0, cos θ)`, orthographic,
  half-width = farthest bounds corner from the plant axis (+4 %), height =
  bounds (+2 %). Draw through a `CommandBuffer` (`SetViewport`,
  `SetViewProjectionMatrices`, `DrawMesh`) — a real camera would render the
  open scene too.
- Flat bark/leaf colours matching the runtime `_BaseColor`s, mild form term
  `ambient + (1-ambient)·|n·L|`, `Cull Off` (leaf cards face random ways).
  Background = leaf colour at alpha 0 so filtering never darkens edges.
- Importer: alpha is transparency, mips on, clamp, trilinear, NPOT none.
- Card mesh per variant: `x ∈ [-r, r]`, `y ∈ [ymin, ymax]`, `uv.x ∈ [0, 1/N]`,
  `uv.y` = the variant's row; bounds = the cylinder it sweeps.
- Material `MarchingCubes/Plant Impostor` with `_Frames`, `_Cutoff` 0.4,
  `_Ambient` 0.3; instancing on.

**The render-target flip.** On D3D11/Metal/Vulkan (`SystemInfo.graphicsUVStartsAtTop`)
frames come back upside down while viewport rows stay in order. Flip the
projection's vertical axis (`Ortho(-r, r, +h, -h, …)`) on those APIs. Verified
with a tip-up triangle drawn into row 0 and its width profile read back; do
the same test if the bake path changes.

## Shader (`Shaders/PlantImpostor.shader`)

- Object-space camera `mul(UNITY_MATRIX_I_M, _WorldSpaceCameraPos)`, flattened
  to the plant's ground plane → view direction `vd`; card right =
  `cross(vd, up)` (matches the bake camera's right); position = `right·x +
  up·y`, transformed by the instance matrix (so the card stays upright on a
  globe and inherits lean and scale).
- Frame index `f = atan2(vd.x, vd.z) / 2π · N`, blend the two bracketing
  frames by `frac(f)`.
- Lit as one up-facing surface: `sun · lerp(NdotL, 1, ambient) + SH(L0+L1)`,
  fog applied. **Do not include `Lighting.hlsl`**: the full URP lighting stack
  in this tiny shader made the d3d11 compiler fail with "out of memory while
  parsing" in Shadows.hlsl on the `FOG_EXP2 INSTANCING_ON` fragment variant,
  and a card needs only `_MainLightPosition`, `_MainLightColor` and
  `unity_SHAr/g/b` from Core.hlsl. Check `ShaderUtil.ShaderHasError` after any
  shader edit; an errored material draws nothing, silently.
- `DepthOnly` pass with the same clip so depth-prepass features see the card;
  no shadow caster (cards are drawn with shadows off; a card's shadow is a
  wall).

## Draw calls and budgets

Draw calls = species × variants × LOD tiers in view × submeshes; ~130–160 at
the spawn. `RenderMeshInstanced` costs ~15 µs per call in the Editor, less in
a player; it is the dominant steady-state cost after the gather was
optimised. Reduce by fewer variants per LOD tier or by merging bark and leaf
into one submesh with a vertex-colour shader (not done; the materials are
placeholders). Per-call limit 1023 instances.

Budget rule of thumb: `PlantPrototypeBaker.kTriangleBudget` 20 k tris per
LOD0 variant. Tree 9.5 k, bramble 13.7 k, herb 1.5 k, fern 1.8 k.

## Pitfalls that cost time

- Cards render, but only from the main camera and not from a positioned
  capture? They were not rendering at all: check the shader error first.
- Card brighter than the mesh: the mesh trunk is mostly sky-lit; lower
  `_Ambient` (0.3 matched at a low sun).
- Editing `impostorDistance` in play mode persists in the asset; restore it.
- `execute_code` in the Editor is CodeDom C# 6: no `out _`, no interpolated
  strings with `:R` format on expressions, retry once right after entering
  play mode (it fails transiently).
