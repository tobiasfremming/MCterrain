# Gotchas, each of which cost real time

## Editor and MCP

- **Verify the instance, not the port.** `CLAUDE.md` says 8040; for the whole
  creature work the Editor actually served on **8080**, and SpaceGame moves between
  8080 and 8082. Read `mcpforunity://instances` and confirm `MarchingCubes@…` on
  `6000.2.6f2`. If the session's `mcp__unityMCP__*` tools point at a dead port, use
  `python .claude/skills/marchingcubes-workflow/scripts/mcpcall.py <port> resource mcpforunity://instances`
  and call tools with env `UNITY_INSTANCE=MarchingCubes@<hash>`. Do not edit the MCP
  config or press "Register with Claude Code".
- **The first `run_tests` after play mode may time out** (domain reload still
  running). Re-read the instances and run it again rather than assuming failure. Run
  one test class per job (`workflow.md`).
- **The Editor hangs** ("Reloading Domain (busy for 48 min)", ~1 GB free RAM). Agents
  then stall too. Stop, tell the user, continue offline.
- **Shader cache poisoning.** The creature once rendered magenta: the on-demand
  Forward compile failed with a bogus "Couldn't open include … Filtering.hlsl" that had
  lost its drive letter, while the batch compile passed. Fix: close the Editor, delete
  `Library/ShaderCache/shader/Creature*`. Guard: `CreatureShader_EditorRuntimeCompile_NoErrors`
  (interactive Editor only). The look of that bug became the cloak.
- **bee_backend crash** (0xC0000005), Editor stuck on "importing": close it, delete `Library/Bee`.
- **Play mode in an unfocused Editor** sits on frame 1: set
  `Application.runInBackground = true` via execute_code. The bridge drops 10–30 s after
  entering play mode. execute_code is CodeDom C# 6 (no `out _`).
- **Memory is tight.** A test that loaded a heavy asset (Texture2D) crashed the Editor
  OOM. Tests load only light assets (the lab config test reads YAML text). Watch for
  other heavy processes (the user's music-gen pytest once took 3.4 GB).
- **Screenshots** (only when the user is away, R32): Game-view capture after moving
  the Player rig, controllers disabled. Positioned captures and execute_code cameras
  miss the instanced draw about 1 in 4; a `manage_camera` positioned capture moved the
  Player's camera and later gave blank frames. Retake empty shots. Delete the PNG +
  meta you created under `Assets/Screenshots`, never the user's.
- `Assets/_CreatureSpike/` is controller scratch: never commit it.

## Simulation and mesh

- **Quaternion TRS invalid.** "Quaternion To Matrix conversion failed … l=0.999988" at
  `CreatureSim.WriteBoneWorld`: `Basis(f, u)` built from near-orthonormal climb/roll
  frames drifted ~1e-5 from unit length, and `Matrix4x4.TRS` rejects that. Fix
  (4637176): renormalise only when |l² − 1| > 1e-6, so exact frames keep their bits
  (walking hashes stay). Any new body that builds rotations from slerped frames must
  do the same; the octopus and wyvern branches were told to audit their own TRS calls.
- **R25, ground through dug holes.** Answer the **nearest** surface, never the
  topmost; the surface choice must be continuous per creature (no lip/floor flip-flop
  between neighbouring joints); grounding must preserve length (`RestoreLengths`).
  Feet use the exact probe, the spine `cache.Smooth` (bicubic Hermite with a
  Fritsch–Carlson limiter on step edges since R28: rim overshoot 2.6 → 0 cm).
- **Climbing on the walking path breaks R25** (R30): terrain climbing must need a
  real wall (≥ ½ body length relief) and the pitch limiter runs only while climbing.
  See `climbing.md`.
- Remaining vertical fold at steep dug rims: worst bend 61° overhang / 54° bowl,
  guarded at 63° / 56°.
- **Terrain rebinding.** The chunk manager rebuilds `PhysicsField`/modifications as
  new objects; `CreatureWorld.RebindIfStale` → `BindTerrain` re-points the probe, clears
  caches, moves the `RegionModified` subscription.
- **Joint ranges before mesh hacks (R12)**; a mostly lateral pole folds the skin.
- **Tight turns** curl the trunk over the inner feet: the R28 keep-out (data-driven by
  the rest gap) fixes it. **Slowing the body** for it stalled the tight circle and broke
  other bounds: do not.
- **The drag chain low-passes travelling waves** (R27): long wavelengths for snakes.
- **Speed is the actual head speed** after the bounds clamp (R7).
- dt is clamped to 0.1 s and split into sub-steps; NaN dt is not guarded (deferred).
- Octopus: free-twist toward the body axis fed back into the curl (endless motion);
  breathing must shape only the soft-bone transforms, not the sim; lapsing contact
  planes make resting arms tremble.

## Colour space (Linear project)

Inspector colours are authored in **sRGB**. Decode exactly once where they enter shading:
- `MaterialPropertyBlock.SetColor` / `Material.SetColor` decode automatically: the
  creature palette is correct this way. Do not decode again in HLSL.
- `SetVector`, `SetVectorArray`, `Color32` vertex colours, packed RGB565 do **not**:
  - plants: `PlantColor.hlsl` decodes vertex colours in `Plant.shader` Forward and in
    `PlantImpostorBake.shader` (73d4795); impostor atlases must be re-baked (*Rebake
    Plant Impostor Atlases*; `Config/Flora/Prototypes` is gitignored, so once per machine);
  - terrain: `ShadingColor()` = `c.linear` at `MCChunkManager.PublishBiomeShadingGlobals`;
  - grass: decode in `Grass.shader` `BuildBlade` after the RGB565 unpack;
  - shared helper `Shaders/SrgbColor.hlsl`.
- After the fix the desert went rust; the user chose the old beige, so DesertBiome and
  DesertMountainBiome colours were re-encoded as linear→sRGB of the old values. If a
  colour "looks wrong" after such a fix, re-author the data, don't re-break the shader.
- The Baobab once rendered flat white (sRGB vertex colours as linear albedo); its bark
  still reads lavender-grey in the lab (authored taupe), a look item.

## Rendering

- Follow the `Grass.shader` template: target 4.5, `StructuredBuffer` + `SV_InstanceID`
  (0..n−1 for `RenderMeshPrimitives` on D3D11), uniform loop bounds, **never leave a
  StructuredBuffer unbound**, C#/HLSL structs match (16 B; 32 B on the octopus branch).
- Passes: Forward, ShadowCaster, DepthOnly and **DepthNormals** (R14, SSAO).
- `pow()` with a negative base warns: clamp the bases.
- Shaders cannot be compiled offline; check `ShaderUtil.ShaderHasError` after any edit.
  Shaders written offline (octopus, membrane, band/sheen) expect a fix round.
- Renderer bounds = joints + feet (+ knees, wing tips, arms) grown by 2 × reach × scale.

## Measuring

- **GC counter vacuous on Mono:** `GC.GetAllocatedBytesForCurrentThread` reads 0 on
  Unity's Boehm Mono even around 100 kB. Use `Tests/EditMode/GcAllocs.cs` (profiler
  `Recorder` on the `GC.Alloc` marker, current thread) and call `AssertCounterWorks()`
  (the positive control) first in every no-alloc test.
- **`Perf_100Lizards` sits near its 4 ms bound** (R23; despite the name `_Under3ms`).
  It measured 3.65–3.70 at Task 9, 3.98 on 2026-10-17 evening, 4.9–5.0 with several
  agents running, and fails under full-suite load. R29: do not re-rule on a loaded
  machine; A/B interleaved in one session to measure a change.
- Field sample ≈ 2.2–2.6 µs on DesertWorld. Measure the real field before choosing a
  probing strategy.
- `Build_Time_Under5ms` flakes under Editor load. execute_code perf reads higher than
  the test runner. .NET harness numbers are optimistic vs Mono (octopus: 0.35 ms .NET →
  1.1–1.8 ms Mono).
