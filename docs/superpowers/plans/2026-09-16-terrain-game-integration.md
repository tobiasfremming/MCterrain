# Terrain → Game Integration (Physics + NavMesh, Flat and Globe) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the streamed marching-cubes terrain a drop-in ground for the game: Rigidbody players/NPCs stand on it wherever they are, NavMeshAgents path over it, and the same code works on the flat world now and on the globe later.

**Architecture:** Rendering stays exactly as it is (clipmap around one target). Collision and navigation become **anchor-driven**: anything that needs ground (player, active NPCs) carries a `TerrainAnchor`. Collision *tiles* (collider-only LOD0 meshes, no renderer) are streamed around anchors the clipmap doesn't already cover, and NavMesh is baked at runtime from all terrain collider meshes inside **nav patches** planned around anchor clusters. A nav patch is `(centre, rotation, size)`: on the flat world the rotation is identity and the patch origin never moves (so updates stay incremental); on the globe the rotation is the radial up at the patch centre and patches are re-planted as clusters move. One planner, one baker, two modes.

**Tech Stack:** Unity 6000.2.6f2, URP, `com.unity.ai.navigation` 2.0.9 (already in `Packages/manifest.json`), PhysX (`Physics.BakeMesh`), Unity Test Framework 1.6.0 (EditMode tests), Unity MCP for play-mode verification.

**Spec:** No separate spec. The requirements are the user's request of 2026-09-16, restated in "Requirements" below.

## Requirements (from the request)

1. The terrain is going into the user's game as a preliminary version.
2. The game has Rigidbody-driven elements (player, NPCs) — they must collide with the terrain reliably.
3. The game uses NavMeshAgents — the terrain must produce a NavMesh at runtime ("bake navmesh and such").
4. The game is flat-world for now; the globe must be planned for too.

## Global Constraints

- Unity **6000.2.6f2**. Verify the MCP instance is `MarchingCubes@…` before any MCP call (see `CLAUDE.md`); use the `marchingcubes-workflow` skill before the first MCP call of a session.
- All terrain code lives in the **`Assets/TerrainGen` git submodule**. Commit code there (`git -C Assets/TerrainGen …`), then commit the submodule pointer bump in the parent repo.
- **Terrain geometry is never authored by hand or through MCP** — only through `DensityField` code and `Assets/TerrainGen/Config/*.asset`.
- Density convention: **positive = solid, negative = air**. Point queries pass `filterWidth = 0`.
- Nothing off the main thread may touch a Unity object except `Physics.BakeMesh(instanceId, convex)`. Short `Task.Run` jobs are fine; long-lived blocking workers must be dedicated `Thread`s with `IsBackground = true` (Mono threadpool crash, see memory `unity-mcp-routing`).
- Do not change mesher output, Transvoxel seams or LOD selection. Collision tiles use LOD0 resolution with no transition faces, which is exactly what a clipmap LOD0 chunk builds.
- The terrain package must not assume project layers exist: the game has its own `TagManager.asset`. Layers are **config fields**, default `0` (Default).
- Demo-only behaviour (`PlayerBootstrap`, `DesertAtmosphere`) must be switchable off from config so it cannot hijack the game's player, fog or camera.
- `Assets/TerrainGen/Config/WorldConfig.asset` currently has `useGlobe: 1`. Flat-world tasks are verified with a WorldConfig that has `useGlobe: 0` (Task 1 creates one); do not flip the shared asset.
- Compile gate when the Editor is unavailable: Roslyn offline compile (memory `offline-compile-check`). It never replaces a play-mode check.

---

## Phase map

| Phase | Tasks | Delivers | Works on |
|---|---|---|---|
| A. Package hygiene | 1–3 | asmdefs + tests, demo switches, terrain layer, collider events | both |
| B. Rigidbody ground | 4–6 | ground query API, rigidbody guard, wake-on-edit | both |
| C. Collision for distant NPCs | 7–8 | `TerrainAnchor`, collision tiles | both |
| D. NavMesh | 9–11 | patch planner, runtime baker, agent guard | flat (globe-ready math) |
| E. Globe navigation | 12–13 | spike + radial patches | globe |
| F. Flora obstacles | 14 | trees block bodies and carve NavMesh | both |
| G. Game handoff | 15 | integration guide + demo scene | both |

Phases A–D are what the game needs now. E and F can be scheduled later without rework in A–D.

## Why this shape (read before implementing)

Facts from the current code that drive the design:

- **Only clipmap LOD0 chunks get colliders** (`MCChunkManager.ApplyLevelSettings`: `chunk.generateCollider = key.level == 0`). LOD0 chunks are `cellsPerChunk.x * cellSize` = 32 × 0.5 = **16 m**; the LOD0 box is `chunksPerLevel` (6) chunks = **96 m** wide around the manager's single `target`. An NPC ~40 m from the player has no collider under it and falls through the world. That is the #1 Rigidbody problem.
- **Colliders appear asynchronously** (`MarchingChunk.ApplyBuild` → `Physics.BakeMesh` on a task → `FinishColliderBake` a frame or more later). Anything spawned before its ground cooks falls. `CharacterGravity` already solves this for the demo CharacterController by holding position; Rigidbodies need the same.
- **Physical edits re-cook colliders** (`TerrainModificationSystem.RegionModified` with `affectsPhysics`). A sleeping Rigidbody over a freshly dug hole does not wake up by itself and floats.
- **Render meshes of LOD1+ may live only on the GPU** (`gpuMeshDirectUpload`), but collider meshes are CPU-side (`"Collider chunks cannot direct-upload: PhysX cooks from CPU-side data"`). So NavMesh sources must be **collider meshes**, never render meshes.
- **A NavMesh instance has one fixed rotation** (`NavMeshBuilder.BuildNavMeshData(settings, sources, bounds, position, rotation)`), and separate instances do not connect without links. The package's *Sliding Window Terrain* sample confirms the flat pattern (fixed origin, moving bounds, `UpdateNavMeshDataAsync`), and *Free Orientation* confirms agents walk on a rotated instance. A sphere therefore needs several rotated instances; planning patches around anchor clusters, and merging clusters whose patches would overlap, avoids needing links at all.
- All terrain scripts except `Scripts/LSystem` are in **Assembly-CSharp**. A game using asmdefs cannot reference Assembly-CSharp, and a test asmdef cannot either. Task 1 fixes both.

---

## File structure

New files (all under `Assets/TerrainGen/`):

| File | Responsibility |
|---|---|
| `Scripts/TerrainGen.Runtime.asmdef` | Runtime assembly for everything in `Scripts/` except `LSystem/` |
| `Editor/TerrainGen.Editor.asmdef` | Editor assembly |
| `Tests/EditMode/TerrainGen.Tests.asmdef` | EditMode tests |
| `Tests/EditMode/TestFields.cs` | Synthetic `DensityField`s for tests (plane, sphere) |
| `Scripts/Integration/TerrainQuery.cs` | Static ground/up queries over a `DensityField` (pure, testable) |
| `Scripts/Integration/TerrainRigidbodyGuard.cs` | Holds a Rigidbody kinematic until ground exists; rescues it if it ends up inside rock |
| `Scripts/Integration/TerrainPhysicsWaker.cs` | Wakes sleeping Rigidbodies when terrain collision changes under them |
| `Scripts/Integration/TerrainAnchor.cs` | "I need ground/nav here" registry component |
| `Scripts/Integration/CollisionTilePlanner.cs` | Pure: anchors + clipmap LOD0 box → wanted tile coords |
| `Scripts/Integration/TerrainCollisionStreamer.cs` | Builds/pools collider-only tiles for the planned coords |
| `Scripts/Integration/NavPatchPlanner.cs` | Pure: anchors → nav patches (flat and radial), clustering + hysteresis |
| `Scripts/Integration/TerrainNavMesh.cs` | Per-patch `NavMeshData`, sources from terrain colliders, async updates |
| `Scripts/Integration/TerrainNavAgentGuard.cs` | Keeps a `NavMeshAgent` (+ optional Rigidbody) valid across patch swaps and unbuilt ground |
| `Tests/EditMode/*Tests.cs` | One test file per pure class |
| `INTEGRATION.md` | How the game wires it up (Task 15) |

Modified files:

| File | Change |
|---|---|
| `Scripts/WorldConfig.cs` | `demoBootstrap`, `terrainLayer`, `navAgentTypeIds`, collision/nav tuning fields |
| `Scripts/Player/PlayerBootstrap.cs`, `Scripts/Player/DesertAtmosphere.cs` | Early-out when `demoBootstrap` is off |
| `Scripts/MarchingCubes/MarchingChunk.cs` | `ColliderChanged` static event, `ColliderMesh` property |
| `Scripts/MarchingCubes/MCChunkManager.cs` | Apply terrain layer; expose `PhysicsField`, `Level0ChunkSize`, `IsInLevel0Box`, `IsLevel0ColliderReady`, `Instance` |

---

## Phase A — Package hygiene

### Task 1: Assembly definitions, test assembly, flat test config

**Files:**
- Create: `Assets/TerrainGen/Scripts/TerrainGen.Runtime.asmdef`
- Create: `Assets/TerrainGen/Editor/TerrainGen.Editor.asmdef`
- Create: `Assets/TerrainGen/Tests/EditMode/TerrainGen.Tests.asmdef`
- Create: `Assets/TerrainGen/Tests/EditMode/TestFields.cs`
- Create: `Assets/TerrainGen/Tests/EditMode/AssemblySmokeTests.cs`
- Create (in Editor, by duplicating): `Assets/TerrainGen/Config/Test/WorldConfig_Flat.asset`

**Interfaces:**
- Produces: assembly `TerrainGen.Runtime` (references `TerrainGen.LSystem`, `Unity.AI.Navigation`); `PlaneField` (`height` field, density `height - y`) and `SphereField` (`center`, `radius`, density `radius - |p - center|`) in namespace `TerrainGen.Tests`.

- [ ] **Step 1: Write the smoke test and test fields**

`Assets/TerrainGen/Tests/EditMode/TestFields.cs`:
```csharp
using UnityEngine;

namespace TerrainGen.Tests
{
    // Flat ground at y = height. Positive (solid) below.
    public class PlaneField : DensityField
    {
        public float height;
        public override float Sample(Vector3 p, float filterWidth) => height - p.y;
        public override bool TryGetHeightBounds(out float minH, out float maxH) { minH = maxH = height; return true; }
        protected override void OnValidate() { } // don't ping TerrainTuning from tests
    }

    // Solid ball; stands in for a smooth planet.
    public class SphereField : DensityField
    {
        public Vector3 center;
        public float radius = 100f;
        public override float Sample(Vector3 p, float filterWidth) => radius - Vector3.Distance(p, center);
        protected override void OnValidate() { }
    }
}
```

`Assets/TerrainGen/Tests/EditMode/AssemblySmokeTests.cs`:
```csharp
using NUnit.Framework;
using UnityEngine;

namespace TerrainGen.Tests
{
    public class AssemblySmokeTests
    {
        [Test]
        public void RuntimeTypesAreVisibleFromTests()
        {
            var f = ScriptableObject.CreateInstance<PlaneField>();
            f.height = 3f;
            Assert.That(f.Sample(new Vector3(0, 0, 0)), Is.EqualTo(3f));
            Assert.That(typeof(MCChunkManager).Assembly.GetName().Name, Is.EqualTo("TerrainGen.Runtime"));
            Object.DestroyImmediate(f);
        }
    }
}
```

- [ ] **Step 2: Create the asmdefs**

`Assets/TerrainGen/Scripts/TerrainGen.Runtime.asmdef`:
```json
{
    "name": "TerrainGen.Runtime",
    "rootNamespace": "",
    "references": ["TerrainGen.LSystem", "Unity.AI.Navigation"],
    "includePlatforms": [],
    "excludePlatforms": [],
    "allowUnsafeCode": false,
    "overrideReferences": false,
    "autoReferenced": true,
    "defineConstraints": [],
    "noEngineReferences": false
}
```

`Assets/TerrainGen/Editor/TerrainGen.Editor.asmdef`:
```json
{
    "name": "TerrainGen.Editor",
    "references": ["TerrainGen.Runtime", "TerrainGen.LSystem"],
    "includePlatforms": ["Editor"],
    "excludePlatforms": [],
    "allowUnsafeCode": false,
    "overrideReferences": false,
    "autoReferenced": true,
    "defineConstraints": [],
    "noEngineReferences": false
}
```

`Assets/TerrainGen/Tests/EditMode/TerrainGen.Tests.asmdef`:
```json
{
    "name": "TerrainGen.Tests",
    "rootNamespace": "TerrainGen.Tests",
    "references": ["TerrainGen.Runtime", "UnityEngine.TestRunner", "UnityEditor.TestRunner", "Unity.AI.Navigation"],
    "includePlatforms": ["Editor"],
    "excludePlatforms": [],
    "allowUnsafeCode": false,
    "overrideReferences": true,
    "precompiledReferences": ["nunit.framework.dll"],
    "autoReferenced": false,
    "defineConstraints": ["UNITY_INCLUDE_TESTS"],
    "noEngineReferences": false
}
```

- [ ] **Step 3: Refresh and read the console**

Over MCP: `refresh_unity`, then `read_console` (errors only). Expected: no errors.
Likely failures and fixes:
- `The type or namespace 'X' could not be found` in `Scripts/` → the type lives outside `Assets/TerrainGen/Scripts` (e.g. `Assets/TutorialInfo` is unrelated and fine). Add the missing assembly to `references`; do not move game files.
- A runtime script using `UnityEditor` without `#if UNITY_EDITOR` (5 `UNITY_EDITOR` blocks exist today; any unguarded use now errors) → wrap it in `#if UNITY_EDITOR`.
- `Scripts/LSystem/Demo` or `LSystem/Tests` keep their own asmdef; nested asmdefs win, no change needed.

- [ ] **Step 4: Run the smoke test**

MCP `run_tests` with mode `EditMode`, filter `TerrainGen.Tests.AssemblySmokeTests`. Expected: 1 passed.

- [ ] **Step 5: Create the flat test config**

In the Editor, duplicate `Config/WorldConfig.asset` to `Config/Test/WorldConfig_Flat.asset` and set `Use Globe` off (MCP `manage_asset` duplicate + `manage_scriptable_object` set `useGlobe=false`). Confirm with `find_in_file` that the new asset has `useGlobe: 0` and the original still has `useGlobe: 1`.

- [ ] **Step 6: Play-mode regression check**

Open `Assets/Scenes/SampleScene.unity`, enter play mode for ~10 s, read the console. Expected: same logs as before (`[PlayerBootstrap] Player ready …`), no new errors. Take one screenshot and compare to intuition: terrain renders, player stands.

- [ ] **Step 7: Commit**

```bash
git -C Assets/TerrainGen add Scripts/TerrainGen.Runtime.asmdef* Editor/TerrainGen.Editor.asmdef* Tests Config/Test/WorldConfig_Flat.asset*
git -C Assets/TerrainGen commit -m "build: runtime/editor/test assemblies and flat test config"
```

---

### Task 2: Demo switch and terrain layer

**Files:**
- Modify: `Assets/TerrainGen/Scripts/WorldConfig.cs`
- Modify: `Assets/TerrainGen/Scripts/Player/PlayerBootstrap.cs` (top of `EnsurePlayer`)
- Modify: `Assets/TerrainGen/Scripts/Player/DesertAtmosphere.cs` (top of `Setup`)
- Modify: `Assets/TerrainGen/Scripts/MarchingCubes/MCChunkManager.cs` (`ApplyLevelSettings`)
- Test: `Assets/TerrainGen/Tests/EditMode/WorldConfigTests.cs`

**Interfaces:**
- Produces: `WorldConfig.demoBootstrap` (bool, default `true`), `WorldConfig.terrainLayer` (int 0..31, default `0`), `int WorldConfig.TerrainLayerMask` (`1 << terrainLayer`).

- [ ] **Step 1: Write the failing test**

```csharp
using NUnit.Framework;
using UnityEngine;

namespace TerrainGen.Tests
{
    public class WorldConfigTests
    {
        [Test]
        public void TerrainLayerMaskMatchesLayer()
        {
            var c = ScriptableObject.CreateInstance<WorldConfig>();
            c.terrainLayer = 9;
            Assert.That(c.TerrainLayerMask, Is.EqualTo(1 << 9));
            Assert.That(c.demoBootstrap, Is.True, "existing scenes keep the demo player by default");
            Object.DestroyImmediate(c);
        }
    }
}
```

- [ ] **Step 2: Run it — expect a compile failure** (`WorldConfig` has no `terrainLayer`). MCP `run_tests` EditMode filter `WorldConfigTests`, or read the console.

- [ ] **Step 3: Implement**

In `WorldConfig.cs`, directly under the `[Header("Defaults")]` block add:
```csharp
    [Header("Game Integration")]
    [Tooltip("On: PlayerBootstrap spawns the demo capsule player and DesertAtmosphere sets fog/far plane at play start. Turn OFF in the game, which brings its own player, camera and lighting.")]
    public bool demoBootstrap = true;
    [Tooltip("Layer every terrain chunk and collision tile is put on. The terrain package cannot add layers to the game's TagManager: create a 'Terrain' layer in the game and select its index here. NavMesh, ground probes and Rigidbody guards all use this.")]
    [Range(0, 31)] public int terrainLayer = 0;

    public int TerrainLayerMask => 1 << terrainLayer;
```

In `PlayerBootstrap.EnsurePlayer`, after `var manager = Object.FindFirstObjectByType<MCChunkManager>(); if (manager == null) return;` — move that line to the top of the method and add right after it:
```csharp
        if (manager.worldConfig != null && !manager.worldConfig.demoBootstrap) return;
```
(Keep the two existing `SimplePlayerController`/`TerrainTarget` early-outs after it.)

In `DesertAtmosphere.Setup`, after `if (manager == null) return;` add the same line.

In `MCChunkManager.ApplyLevelSettings`, after `chunk.generateCollider = key.level == 0;` add:
```csharp
        chunk.gameObject.layer = worldConfig ? worldConfig.terrainLayer : 0;
```

- [ ] **Step 4: Run tests.** Expected: `WorldConfigTests` passes, smoke test still passes.

- [ ] **Step 5: Play-mode check.** SampleScene with default config: demo player still spawns. Then set `demoBootstrap` off on `WorldConfig_Flat`, point the scene's manager at it, play: no `[PlayerBootstrap]` log, fog unchanged. Revert the scene's manager reference (do not save the scene with the test config unless the user asks).

- [ ] **Step 6: Commit**

```bash
git -C Assets/TerrainGen add Scripts/WorldConfig.cs Scripts/Player/PlayerBootstrap.cs Scripts/Player/DesertAtmosphere.cs Scripts/MarchingCubes/MCChunkManager.cs Tests/EditMode/WorldConfigTests.cs*
git -C Assets/TerrainGen commit -m "feat: demoBootstrap switch and configurable terrain layer"
```

---

### Task 3: Collider change events and manager accessors

**Files:**
- Modify: `Assets/TerrainGen/Scripts/MarchingCubes/MarchingChunk.cs`
- Modify: `Assets/TerrainGen/Scripts/MarchingCubes/MCChunkManager.cs`
- Test: play-mode probe over MCP (this is Unity-object plumbing; no pure logic to unit test)

**Interfaces:**
- Produces:
  - `public static event System.Action<MarchingChunk> MarchingChunk.ColliderChanged` — raised on the main thread whenever a chunk's collider becomes enabled with new geometry or becomes disabled.
  - `public Mesh MarchingChunk.ColliderMesh` — the mesh the enabled `MeshCollider` uses, or `null`.
  - `public Bounds MarchingChunk.WorldBounds` — `new Bounds(transform.position + size/2, size)`, size = `cells * cellSize`.
  - `public static MCChunkManager MCChunkManager.Instance` (set in `OnEnable`, cleared in `OnDisable` if it is this).
  - `public DensityField MCChunkManager.PhysicsField` (calls `EnsureField()`, returns `_physicsField`).
  - `public float MCChunkManager.Level0ChunkSize => LevelChunkSize(0);`
  - `public Vector3Int MCChunkManager.Level0Coord(Vector3 worldPos)` → `FloorCoord(worldPos, LevelChunkSize(0))`.
  - `public bool MCChunkManager.IsInLevel0Box(Vector3Int coord)` — false when `!_boxesValid`.
  - `public bool MCChunkManager.IsLevel0ColliderReady(Vector3Int coord)` — the LOD0 chunk exists, is generated, and has no bake pending.
  - `public event System.Action MCChunkManager.Level0BoxChanged` — raised after `RecomputeTargets()` in `Update`.

- [ ] **Step 1: Implement `MarchingChunk` events**

Add next to `public static readonly List<MarchingChunk> Active = new();`:
```csharp
    // Raised (main thread) when this chunk's collision changes: a new cooked
    // collider bound, or the collider turned off. Collision tiles, the
    // NavMesh baker and the Rigidbody waker listen; nothing in the mesher does.
    public static event System.Action<MarchingChunk> ColliderChanged;

    public Mesh ColliderMesh => _collider != null && _collider.enabled ? _collider.sharedMesh : null;

    public Bounds WorldBounds
    {
        get
        {
            var size = Vector3.Scale((Vector3)cells, new Vector3(cellSize, cellSize, cellSize));
            return new Bounds(transform.position + size * 0.5f, size);
        }
    }
```

Raise it at every place the collider's bound state changes. In `ApplyBuild`:
- after `_collider.enabled = false; _pendingColliderMesh = null;` in the `colliderMesh == null` branch, before `return;` → `ColliderChanged?.Invoke(this);`
- after `_collider.enabled = true; _pendingColliderMesh = null;` in the `!job.deferColliderBake` branch, before `return;` → `ColliderChanged?.Invoke(this);`

In `FinishColliderBake`, inside the `if (_collider != null && _pendingColliderMesh != null && generateCollider)` block after `_collider.enabled = true;` → `ColliderChanged?.Invoke(this);`

In `DisableCollider`, inside `if (_collider != null)` after `_collider.enabled = false;` → `ColliderChanged?.Invoke(this);`

In `OnDisable` (pooling releases chunks by deactivating them): change to
```csharp
    void OnDisable()
    {
        Active.Remove(this);
        if (_collider != null && _collider.enabled) ColliderChanged?.Invoke(this); // collision leaves with the chunk
    }
```

- [ ] **Step 2: Implement manager accessors**

In `MCChunkManager`, near `public TerrainModificationSystem Modifications`:
```csharp
    public static MCChunkManager Instance { get; private set; }

    // The field colliders are meshed from: base terrain + physical edits only.
    public DensityField PhysicsField { get { EnsureField(); return _physicsField; } }

    public float Level0ChunkSize => LevelChunkSize(0);
    public Vector3Int Level0Coord(Vector3 worldPos) => FloorCoord(worldPos, LevelChunkSize(0));

    public event Action Level0BoxChanged;

    public bool IsInLevel0Box(Vector3Int coord)
    {
        if (!_boxesValid || _boxMin == null || _boxMin.Length == 0) return false;
        Vector3Int d = coord - _boxMin[0];
        int E = Extent;
        return d.x >= 0 && d.y >= 0 && d.z >= 0 && d.x < E && d.y < E && d.z < E;
    }

    public bool IsLevel0ColliderReady(Vector3Int coord)
    {
        var key = new ChunkKey { level = 0, coord = coord };
        return IsReady(key) && _chunks.TryGetValue(key, out var ch) && ch != null && !ch.ColliderBakePending;
    }
```
In the existing `OnEnable` add `Instance = this;` as its first line. Add (or extend, if present) `OnDisable` with `if (Instance == this) Instance = null;`.

In `Update`, change
```csharp
        if (BoxesChanged())
            RecomputeTargets(); // only when the player crosses a clipmap boundary
```
to
```csharp
        if (BoxesChanged())
        {
            RecomputeTargets(); // only when the player crosses a clipmap boundary
            Level0BoxChanged?.Invoke();
        }
```

Note: `IsReady` treats an **empty** chunk (all air) as ready with no collider. That is correct — there is nothing to stand on there.

- [ ] **Step 3: Verify in play mode**

Enter play mode in SampleScene, wait 10 s, then MCP `execute_code`:
```csharp
MarchingChunk.ColliderChanged += c => Debug.Log($"[ColliderChanged] {c.name} mesh={(c.ColliderMesh != null)}");
var m = MCChunkManager.Instance;
var c = m.Level0Coord(m.target.position);
return $"inBox={m.IsInLevel0Box(c)} ready={m.IsLevel0ColliderReady(c)} farInBox={m.IsInLevel0Box(c + new Vector3Int(50,0,0))}";
```
Expected: `inBox=True ready=True farInBox=False`. Then move the player 40 m (MCP: set player position), wait 3 s and `read_console`: expect several `[ColliderChanged]` lines, both `mesh=True` (new ring) and `mesh=False` (released chunks).

- [ ] **Step 4: Commit**

```bash
git -C Assets/TerrainGen add Scripts/MarchingCubes/MarchingChunk.cs Scripts/MarchingCubes/MCChunkManager.cs
git -C Assets/TerrainGen commit -m "feat: collider change events and LOD0 box accessors"
```

---

## Phase B — Rigidbody ground

### Task 4: `TerrainQuery` — ground and up from the density field

Ground queries that do not depend on colliders existing: spawn placement, rescue, far NPC simulation. Works on flat and globe because "up" is passed in (callers use `PlanetGravity.UpAt`).

**Files:**
- Create: `Assets/TerrainGen/Scripts/Integration/TerrainQuery.cs`
- Test: `Assets/TerrainGen/Tests/EditMode/TerrainQueryTests.cs`

**Interfaces:**
- Produces:
  - `public static bool TerrainQuery.TryFindGround(DensityField field, Vector3 from, Vector3 up, float searchUp, float searchDown, out Vector3 point, out Vector3 normal)` — scans from `from + up*searchUp` toward `from - up*searchDown`, returns the **first** air→solid crossing (the highest ground under an overhang-free column; under an overhang it returns the overhang top, which is correct for dropping things from above).
  - `public static bool TerrainQuery.IsInsideSolid(DensityField field, Vector3 p)` → `field.Sample(p) > 0`.
  - `public static bool TerrainQuery.TryFindGround(Vector3 from, float searchUp, float searchDown, out Vector3 point, out Vector3 normal)` — convenience using `MCChunkManager.Instance.PhysicsField` and `PlanetGravity.UpAt(from)`; false if no manager.

- [ ] **Step 1: Write the failing tests**

```csharp
using NUnit.Framework;
using UnityEngine;

namespace TerrainGen.Tests
{
    public class TerrainQueryTests
    {
        [Test]
        public void FindsFlatGroundBelow()
        {
            var f = ScriptableObject.CreateInstance<PlaneField>(); f.height = 12.3f;
            Assert.That(TerrainQuery.TryFindGround(f, new Vector3(5, 40, -7), Vector3.up, 10, 100, out var p, out var n), Is.True);
            Assert.That(p.y, Is.EqualTo(12.3f).Within(0.01f));
            Assert.That(p.x, Is.EqualTo(5f)); Assert.That(p.z, Is.EqualTo(-7f));
            Assert.That(Vector3.Dot(n, Vector3.up), Is.GreaterThan(0.999f));
            Object.DestroyImmediate(f);
        }

        [Test]
        public void FindsGroundWhenStartingUnderground()
        {
            var f = ScriptableObject.CreateInstance<PlaneField>(); f.height = 0f;
            Assert.That(TerrainQuery.TryFindGround(f, new Vector3(0, -5, 0), Vector3.up, 20, 20, out var p, out _), Is.True);
            Assert.That(p.y, Is.EqualTo(0f).Within(0.01f));
            Object.DestroyImmediate(f);
        }

        [Test]
        public void ReturnsFalseWhenNoCrossingInRange()
        {
            var f = ScriptableObject.CreateInstance<PlaneField>(); f.height = -500f;
            Assert.That(TerrainQuery.TryFindGround(f, Vector3.zero, Vector3.up, 10, 100, out _, out _), Is.False);
            Object.DestroyImmediate(f);
        }

        [Test]
        public void FindsSphereSurfaceAlongRadialUp()
        {
            var f = ScriptableObject.CreateInstance<SphereField>(); f.center = new Vector3(0, -1000, 0); f.radius = 1000f;
            Vector3 dir = new Vector3(1, 1, 0).normalized;
            Vector3 from = f.center + dir * 1030f;
            Assert.That(TerrainQuery.TryFindGround(f, from, dir, 5, 60, out var p, out var n), Is.True);
            Assert.That(Vector3.Distance(p, f.center), Is.EqualTo(1000f).Within(0.02f));
            Assert.That(Vector3.Dot(n, dir), Is.GreaterThan(0.999f));
            Object.DestroyImmediate(f);
        }
    }
}
```

- [ ] **Step 2: Run — expect compile failure** (`TerrainQuery` missing).

- [ ] **Step 3: Implement**

```csharp
using UnityEngine;

// Ground queries straight from a density field -- no colliders required, so
// they work for spawn points and for bodies whose ground has not cooked yet.
// Positive density = solid. "Up" is supplied by the caller (PlanetGravity.UpAt
// for anything that must work on the globe too).
public static class TerrainQuery
{
    const float kStep = 0.5f;      // coarse scan step; below the 0.5 m LOD0 cell, so thin ledges are not skipped
    const int kRefine = 14;        // bisection steps: 0.5 m / 2^14 ≈ 0.04 mm

    public static bool TryFindGround(DensityField field, Vector3 from, Vector3 up, float searchUp, float searchDown,
                                     out Vector3 point, out Vector3 normal)
    {
        point = default; normal = up;
        if (field == null || up.sqrMagnitude < 1e-8f) return false;
        up.Normalize();

        float total = searchUp + searchDown;
        Vector3 top = from + up * searchUp;
        float prevT = 0f;
        bool prevSolid = field.Sample(top) > 0f;

        for (float t = kStep; t <= total + 1e-4f; t += kStep)
        {
            float tt = Mathf.Min(t, total);
            bool solid = field.Sample(top - up * tt) > 0f;
            if (solid && !prevSolid)
            {
                float lo = prevT, hi = tt; // lo air, hi solid
                for (int i = 0; i < kRefine; i++)
                {
                    float mid = 0.5f * (lo + hi);
                    if (field.Sample(top - up * mid) > 0f) hi = mid; else lo = mid;
                }
                point = top - up * (0.5f * (lo + hi));
                Vector3 g = field.Gradient(point, 0.05f, 0f);
                normal = g.sqrMagnitude > 1e-12f ? -g.normalized : up; // density rises into rock, so the outward normal is -grad
                return true;
            }
            prevSolid = solid;
            prevT = tt;
        }
        return false;
    }

    public static bool IsInsideSolid(DensityField field, Vector3 p) => field != null && field.Sample(p) > 0f;

    public static bool TryFindGround(Vector3 from, float searchUp, float searchDown, out Vector3 point, out Vector3 normal)
    {
        var m = MCChunkManager.Instance;
        if (m == null) { point = default; normal = Vector3.up; return false; }
        return TryFindGround(m.PhysicsField, from, PlanetGravity.UpAt(from), searchUp, searchDown, out point, out normal);
    }
}
```

Note on "starting underground": the scan starts at `from + up*searchUp`, so a body buried less than `searchUp` deep still finds the surface above it. If the top sample is already solid (buried deeper than `searchUp`), the loop keeps scanning down and may find a cave floor — callers that rescue buried bodies pass a generous `searchUp` (Task 5 uses 50 m).

- [ ] **Step 4: Run tests.** Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
git -C Assets/TerrainGen add Scripts/Integration Tests/EditMode/TerrainQueryTests.cs*
git -C Assets/TerrainGen commit -m "feat: TerrainQuery ground search over density fields"
```

---

### Task 5: `TerrainRigidbodyGuard`

Rigidbody equivalent of `CharacterGravity`'s safety net: a body with no cooked collider below it is held kinematic (not falling), and a body found inside solid rock is lifted to the surface.

**Files:**
- Create: `Assets/TerrainGen/Scripts/Integration/TerrainRigidbodyGuard.cs`
- Test: `Assets/TerrainGen/Tests/EditMode/RigidbodyGuardLogicTests.cs`

**Interfaces:**
- Consumes: `TerrainQuery.TryFindGround(Vector3, float, float, out Vector3, out Vector3)`, `TerrainQuery.IsInsideSolid`, `MCChunkManager.Instance.PhysicsField`, `WorldConfig.TerrainLayerMask`, `PlanetGravity.UpAt`.
- Produces:
  - `public enum GuardState { Free, HeldNoGround, Rescued }`
  - `public static GuardState TerrainRigidbodyGuard.Decide(bool colliderBelow, bool insideSolid, bool wasHeld)` — pure decision.
  - `public bool TerrainRigidbodyGuard.IsHeld` — other code (Task 11) reads this.

- [ ] **Step 1: Write the failing test**

```csharp
using NUnit.Framework;

namespace TerrainGen.Tests
{
    public class RigidbodyGuardLogicTests
    {
        [Test] public void InsideSolidAlwaysRescues() =>
            Assert.That(TerrainRigidbodyGuard.Decide(colliderBelow: true, insideSolid: true, wasHeld: false), Is.EqualTo(GuardState.Rescued));
        [Test] public void NoColliderBelowHolds() =>
            Assert.That(TerrainRigidbodyGuard.Decide(false, false, false), Is.EqualTo(GuardState.HeldNoGround));
        [Test] public void ColliderBelowFrees() =>
            Assert.That(TerrainRigidbodyGuard.Decide(true, false, true), Is.EqualTo(GuardState.Free));
    }
}
```

- [ ] **Step 2: Run — expect compile failure.**

- [ ] **Step 3: Implement**

```csharp
using UnityEngine;

public enum GuardState { Free, HeldNoGround, Rescued }

// Keeps a Rigidbody from falling through terrain that has not cooked yet, and
// pulls it out if an edit or a streaming gap ever leaves it inside rock.
// Checks at a low rate (every `checkInterval` s, staggered per instance): a
// held body is not moving, and a free body over cooked ground does not need
// per-step probing.
[RequireComponent(typeof(Rigidbody))]
public class TerrainRigidbodyGuard : MonoBehaviour
{
    [Tooltip("How far below the body to look for a terrain collider before deciding the ground has not streamed in yet.")]
    public float probeDistance = 60f;
    public float checkInterval = 0.25f;
    [Tooltip("Height above the found surface a rescued body is placed at (its pivot).")]
    public float rescueLift = 1f;

    Rigidbody _rb;
    bool _heldByUs;
    bool _wasKinematic;
    float _nextCheck;

    public bool IsHeld => _heldByUs;

    public static GuardState Decide(bool colliderBelow, bool insideSolid, bool wasHeld)
    {
        if (insideSolid) return GuardState.Rescued;
        return colliderBelow ? GuardState.Free : GuardState.HeldNoGround;
    }

    void Awake()
    {
        _rb = GetComponent<Rigidbody>();
        _nextCheck = Time.time + Random.value * checkInterval;
    }

    void FixedUpdate()
    {
        if (Time.time < _nextCheck) return;
        _nextCheck = Time.time + checkInterval;

        var m = MCChunkManager.Instance;
        if (m == null) return;

        Vector3 p = _rb.position;
        Vector3 up = PlanetGravity.UpAt(p);
        int mask = m.worldConfig ? m.worldConfig.TerrainLayerMask : ~0;
        bool below = Physics.Raycast(p + up * 0.5f, -up, probeDistance, mask, QueryTriggerInteraction.Ignore);
        bool inside = TerrainQuery.IsInsideSolid(m.PhysicsField, p);

        switch (Decide(below, inside, _heldByUs))
        {
            case GuardState.Rescued:
                if (TerrainQuery.TryFindGround(p, 50f, 10f, out Vector3 g, out _))
                {
                    _rb.position = g + up * rescueLift;
                    if (!_rb.isKinematic) _rb.linearVelocity = Vector3.zero;
                }
                break;
            case GuardState.HeldNoGround:
                if (!_heldByUs) { _wasKinematic = _rb.isKinematic; _rb.isKinematic = true; _heldByUs = true; }
                break;
            case GuardState.Free:
                if (_heldByUs) { _rb.isKinematic = _wasKinematic; _heldByUs = false; _rb.WakeUp(); }
                break;
        }
    }

    void OnDisable()
    {
        if (_heldByUs && _rb != null) { _rb.isKinematic = _wasKinematic; _heldByUs = false; }
    }
}
```

- [ ] **Step 4: Run tests.** Expected: 3 passed.

- [ ] **Step 5: Play-mode check.** In SampleScene (flat config), via MCP `execute_code` spawn a cube with `Rigidbody` + `TerrainRigidbodyGuard` 70 m from the player and 30 m above ground (from `TerrainQuery.TryFindGround`). Read after 3 s: `IsHeld == true`, `position` unchanged. Move the player next to it (`target.position` → cube position), wait 5 s: `IsHeld == false`, cube resting on terrain (distance to `TryFindGround` point < 1 m). Spawn a second cube 2 m **below** ground: after 1 s it sits above ground.

- [ ] **Step 6: Commit**

```bash
git -C Assets/TerrainGen add Scripts/Integration/TerrainRigidbodyGuard.cs* Tests/EditMode/RigidbodyGuardLogicTests.cs*
git -C Assets/TerrainGen commit -m "feat: TerrainRigidbodyGuard holds bodies until ground cooks"
```

---

### Task 6: `TerrainPhysicsWaker`

**Files:**
- Create: `Assets/TerrainGen/Scripts/Integration/TerrainPhysicsWaker.cs`

**Interfaces:**
- Consumes: `MarchingChunk.ColliderChanged`, `MarchingChunk.WorldBounds`, `MCChunkManager.Instance.Modifications.RegionModified`.
- Produces: nothing public; self-installs via `RuntimeInitializeOnLoadMethod`.

- [ ] **Step 1: Implement**

```csharp
using System.Collections.Generic;
using UnityEngine;

// PhysX does not wake sleeping bodies when a static MeshCollider's mesh is
// swapped, so a crate resting on ground that was just dug away floats. Wake
// everything whose bounds touch a region whose collision changed.
public static class TerrainPhysicsWaker
{
    static readonly Collider[] s_hits = new Collider[256];
    static readonly HashSet<Rigidbody> s_woken = new();

    [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.AfterSceneLoad)]
    static void Install()
    {
        MarchingChunk.ColliderChanged -= OnChunk;
        MarchingChunk.ColliderChanged += OnChunk;
        var m = MCChunkManager.Instance ?? Object.FindFirstObjectByType<MCChunkManager>();
        if (m != null)
        {
            m.Modifications.RegionModified -= OnEdit;
            m.Modifications.RegionModified += OnEdit;
        }
    }

    static void OnChunk(MarchingChunk c) => Wake(c.WorldBounds);
    static void OnEdit(Bounds b, bool affectsPhysics) { if (affectsPhysics) Wake(b); }

    public static void Wake(Bounds b)
    {
        b.Expand(1f);
        int n = Physics.OverlapBoxNonAlloc(b.center, b.extents, s_hits, Quaternion.identity, ~0, QueryTriggerInteraction.Ignore);
        s_woken.Clear();
        for (int i = 0; i < n; i++)
        {
            var rb = s_hits[i].attachedRigidbody;
            if (rb != null && !rb.isKinematic && rb.IsSleeping() && s_woken.Add(rb)) rb.WakeUp();
        }
    }
}
```

- [ ] **Step 2: Play-mode check.** Drop a Rigidbody crate near the player, wait until `IsSleeping()` is true (MCP `execute_code`), then call `MCChunkManager.Instance.Modifications.CarveSphere(cratePos - up*1f, 2.5f, true)`. After 1 s: crate position has dropped by > 0.5 m.

- [ ] **Step 3: Commit**

```bash
git -C Assets/TerrainGen add Scripts/Integration/TerrainPhysicsWaker.cs*
git -C Assets/TerrainGen commit -m "feat: wake sleeping rigidbodies when terrain collision changes"
```

---

## Phase C — Collision for distant NPCs

### Task 7: `TerrainAnchor` and `CollisionTilePlanner`

**Files:**
- Create: `Assets/TerrainGen/Scripts/Integration/TerrainAnchor.cs`
- Create: `Assets/TerrainGen/Scripts/Integration/CollisionTilePlanner.cs`
- Test: `Assets/TerrainGen/Tests/EditMode/CollisionTilePlannerTests.cs`

**Interfaces:**
- Produces:
  - `public class TerrainAnchor : MonoBehaviour` with `public float physicsRadius = 20f;`, `public float navRadius = 40f;`, `public static IReadOnlyList<TerrainAnchor> All`, `public Vector3 Position => transform.position`.
  - `public struct AnchorSphere { public Vector3 position; public float radius; }`
  - `public static void CollisionTilePlanner.Plan(IReadOnlyList<AnchorSphere> anchors, float tileSize, System.Func<Vector3Int, bool> coveredByClipmap, HashSet<Vector3Int> result)` — fills `result` with every tile coord whose AABB intersects any anchor sphere and is not covered by the clipmap. Tile coord = `floor(pos / tileSize)` per axis (same as `FloorCoord`).

- [ ] **Step 1: Write the failing tests**

```csharp
using System.Collections.Generic;
using NUnit.Framework;
using UnityEngine;

namespace TerrainGen.Tests
{
    public class CollisionTilePlannerTests
    {
        static HashSet<Vector3Int> Plan(float r, Vector3 p, System.Func<Vector3Int, bool> covered = null)
        {
            var set = new HashSet<Vector3Int>();
            CollisionTilePlanner.Plan(new List<AnchorSphere> { new() { position = p, radius = r } }, 16f, covered ?? (_ => false), set);
            return set;
        }

        [Test]
        public void SmallRadiusInsideOneTileGivesOneTile()
        {
            var s = Plan(1f, new Vector3(8, 8, 8));
            Assert.That(s, Is.EquivalentTo(new[] { new Vector3Int(0, 0, 0) }));
        }

        [Test]
        public void RadiusCrossingFacesIncludesNeighboursButNotFarCorners()
        {
            var s = Plan(3f, new Vector3(1, 8, 8)); // 1 m from the x=0 face
            Assert.That(s, Does.Contain(new Vector3Int(-1, 0, 0)));
            Assert.That(s, Does.Contain(new Vector3Int(0, 0, 0)));
            Assert.That(s.Count, Is.EqualTo(2));
        }

        [Test]
        public void NegativeCoordinatesFloorCorrectly()
        {
            var s = Plan(0.5f, new Vector3(-0.25f, -15.9f, -16.1f));
            Assert.That(s, Is.EquivalentTo(new[] { new Vector3Int(-1, -1, -2) }));
        }

        [Test]
        public void ClipmapCoveredTilesAreExcluded()
        {
            var s = Plan(20f, new Vector3(8, 8, 8), c => c == new Vector3Int(0, 0, 0));
            Assert.That(s, Does.Not.Contain(new Vector3Int(0, 0, 0)));
            Assert.That(s, Does.Contain(new Vector3Int(1, 0, 0)));
        }
    }
}
```

- [ ] **Step 2: Run — expect compile failure.**

- [ ] **Step 3: Implement**

`TerrainAnchor.cs`:
```csharp
using System.Collections.Generic;
using UnityEngine;

// "Something that needs ground here." Put it on the player and on every NPC
// that should keep simulating physically/navigating while away from the
// player. Collision tiles are built within physicsRadius; NavMesh within
// navRadius. NPCs without an anchor only have ground inside the clipmap's
// LOD0 box around the player -- pair them with TerrainRigidbodyGuard.
public class TerrainAnchor : MonoBehaviour
{
    public float physicsRadius = 20f;
    public float navRadius = 40f;

    static readonly List<TerrainAnchor> s_all = new();
    public static IReadOnlyList<TerrainAnchor> All => s_all;

    public Vector3 Position => transform.position;

    void OnEnable() => s_all.Add(this);
    void OnDisable() => s_all.Remove(this);
}
```

`CollisionTilePlanner.cs`:
```csharp
using System;
using System.Collections.Generic;
using UnityEngine;

public struct AnchorSphere { public Vector3 position; public float radius; }

public static class CollisionTilePlanner
{
    public static void Plan(IReadOnlyList<AnchorSphere> anchors, float tileSize, Func<Vector3Int, bool> coveredByClipmap, HashSet<Vector3Int> result)
    {
        result.Clear();
        for (int a = 0; a < anchors.Count; a++)
        {
            Vector3 p = anchors[a].position;
            float r = anchors[a].radius;
            Vector3Int lo = Floor((p - Vector3.one * r) / tileSize);
            Vector3Int hi = Floor((p + Vector3.one * r) / tileSize);
            for (int z = lo.z; z <= hi.z; z++)
            for (int y = lo.y; y <= hi.y; y++)
            for (int x = lo.x; x <= hi.x; x++)
            {
                var c = new Vector3Int(x, y, z);
                if (result.Contains(c)) continue;
                Vector3 min = (Vector3)c * tileSize;
                Vector3 closest = Vector3.Max(min, Vector3.Min(p, min + Vector3.one * tileSize));
                if ((closest - p).sqrMagnitude > r * r) continue;
                if (coveredByClipmap(c)) continue;
                result.Add(c);
            }
        }
    }

    static Vector3Int Floor(Vector3 v) => new(Mathf.FloorToInt(v.x), Mathf.FloorToInt(v.y), Mathf.FloorToInt(v.z));
}
```

The streamer also skips tiles the density field proves empty (Task 8), so vertical over-coverage costs nothing.

- [ ] **Step 4: Run tests.** Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
git -C Assets/TerrainGen add Scripts/Integration/TerrainAnchor.cs* Scripts/Integration/CollisionTilePlanner.cs* Tests/EditMode/CollisionTilePlannerTests.cs*
git -C Assets/TerrainGen commit -m "feat: TerrainAnchor and collision tile planner"
```

---

### Task 8: `TerrainCollisionStreamer`

Collider-only LOD0 tiles around anchors outside the clipmap's LOD0 box. Built with the existing `ChunkMesher.Build` (no transition faces, render field = physics field, so the mesh equals what a LOD0 chunk would collide with), cooked with `Physics.BakeMesh` off-thread.

**Hand-off rule (no gap frames):** a streamer tile inside the clipmap LOD0 box is released only once `IsLevel0ColliderReady(coord)` is true. The two coincident static colliders co-exist for a frame or two; that is harmless.

**Files:**
- Create: `Assets/TerrainGen/Scripts/Integration/TerrainCollisionStreamer.cs`
- Modify: `Assets/TerrainGen/Scripts/WorldConfig.cs` (tuning fields)

**Interfaces:**
- Consumes: `TerrainAnchor.All`, `CollisionTilePlanner.Plan`, `MCChunkManager.Instance` (`PhysicsField`, `Level0ChunkSize`, `IsInLevel0Box`, `IsLevel0ColliderReady`, `worldConfig`), `ChunkMeshJob`, `ChunkMesher.Build`, `MCChunkManager.Modifications.RegionModified`.
- Produces:
  - `public static event Action<Bounds, Mesh, Matrix4x4, bool> TerrainCollisionStreamer.TileChanged` — `(worldBounds, mesh or null, localToWorld, added)`; raised on the main thread when a tile's collider is bound (`added=true`) or released (`added=false`).
  - `public static IEnumerable<(Mesh mesh, Matrix4x4 localToWorld, Bounds bounds)> TerrainCollisionStreamer.ActiveTiles`
  - `WorldConfig.maxTileBuildsPerFrame` (int, default 2), `WorldConfig.maxCollisionTiles` (int, default 512).

- [ ] **Step 1: Add config fields** under `[Header("Game Integration")]` in `WorldConfig.cs`:
```csharp
    [Tooltip("Collision tiles (collider-only LOD0 meshes around TerrainAnchors outside the player's LOD0 ring) started per frame.")]
    [Range(1, 16)] public int maxTileBuildsPerFrame = 2;
    [Tooltip("Hard cap on live collision tiles; the nearest-to-an-anchor win when exceeded.")]
    public int maxCollisionTiles = 512;
```

- [ ] **Step 2: Implement the streamer**

```csharp
using System;
using System.Collections.Generic;
using System.Threading.Tasks;
using UnityEngine;
using UnityEngine.Rendering;

// Collider-only terrain tiles around TerrainAnchors that the clipmap's LOD0
// box does not cover. See the integration plan, Phase C.
public class TerrainCollisionStreamer : MonoBehaviour
{
    public static event Action<Bounds, Mesh, Matrix4x4, bool> TileChanged;

    sealed class Tile
    {
        public Vector3Int coord;
        public GameObject go;
        public MeshCollider collider;
        public Mesh mesh;
        public Task task;          // build + bake
        public ChunkMeshJob job;
        public bool dirty;         // a physical edit landed while building
        public bool bound;         // has completed at least one build
        public int phase;          // 0 idle, 1 meshing, 2 baking
    }

    static readonly Dictionary<Vector3Int, Tile> s_tiles = new();
    public static IEnumerable<(Mesh mesh, Matrix4x4 localToWorld, Bounds bounds)> ActiveTiles
    {
        get
        {
            foreach (var t in s_tiles.Values)
                if (t.bound && t.collider.sharedMesh != null)
                    yield return (t.mesh, t.go.transform.localToWorldMatrix, TileBounds(t.coord));
        }
    }

    static float s_tileSize = 16f;
    static Bounds TileBounds(Vector3Int c) => new((Vector3)c * s_tileSize + Vector3.one * (s_tileSize * 0.5f), Vector3.one * s_tileSize);

    [Tooltip("Debug only: build tiles even where the clipmap's LOD0 box already has colliders (used to compare tile and chunk geometry).")]
    public bool ignoreClipmapCoverage;

    readonly List<AnchorSphere> _anchors = new();
    readonly HashSet<Vector3Int> _wanted = new();
    readonly List<Vector3Int> _scratch = new();
    readonly Stack<Tile> _pool = new();
    MCChunkManager _m;

    static readonly VertexAttributeDescriptor[] kLayout = { new(VertexAttribute.Position, VertexAttributeFormat.Float32, 3) };

    void OnEnable()
    {
        _m = MCChunkManager.Instance ?? FindFirstObjectByType<MCChunkManager>();
        if (_m != null) _m.Modifications.RegionModified += OnEdit;
    }

    void OnDisable()
    {
        if (_m != null) _m.Modifications.RegionModified -= OnEdit;
        foreach (var t in s_tiles.Values) DestroyTile(t);
        s_tiles.Clear();
    }

    void Update()
    {
        if (_m == null || _m.worldConfig == null) return;
        var cfg = _m.worldConfig;
        s_tileSize = _m.Level0ChunkSize;

        // 1. plan
        _anchors.Clear();
        foreach (var a in TerrainAnchor.All)
            if (a.physicsRadius > 0f) _anchors.Add(new AnchorSphere { position = a.Position, radius = a.physicsRadius });
        CollisionTilePlanner.Plan(_anchors, s_tileSize, ignoreClipmapCoverage ? (_ => false) : _m.IsInLevel0Box, _wanted);

        // 2. release tiles no longer wanted (clipmap-covered ones only once the clipmap's own collider is ready)
        _scratch.Clear();
        foreach (var kv in s_tiles)
        {
            if (_wanted.Contains(kv.Key)) continue;
            bool handedToClipmap = _m.IsInLevel0Box(kv.Key);
            if (handedToClipmap && !_m.IsLevel0ColliderReady(kv.Key)) continue;
            if (kv.Value.task != null && !kv.Value.task.IsCompleted) continue; // let the build finish first
            _scratch.Add(kv.Key);
        }
        foreach (var c in _scratch) { Release(s_tiles[c]); s_tiles.Remove(c); }

        // 3. finish completed builds
        foreach (var t in s_tiles.Values)
            if (t.task != null && t.task.IsCompleted) Bind(t);

        // 4. start new builds, nearest to any anchor first, within budget and cap
        _scratch.Clear();
        foreach (var c in _wanted)
            if (!s_tiles.TryGetValue(c, out var t) || (t.dirty && t.task == null)) _scratch.Add(c);
        _scratch.Sort((a, b) => NearestAnchorSq(a).CompareTo(NearestAnchorSq(b)));
        int started = 0;
        foreach (var c in _scratch)
        {
            if (started >= cfg.maxTileBuildsPerFrame) break;
            if (!s_tiles.ContainsKey(c) && s_tiles.Count >= cfg.maxCollisionTiles) break;
            StartBuild(c, cfg);
            started++;
        }
    }

    float NearestAnchorSq(Vector3Int c)
    {
        Vector3 centre = TileBounds(c).center;
        float best = float.MaxValue;
        foreach (var a in _anchors) best = Mathf.Min(best, (a.position - centre).sqrMagnitude);
        return best;
    }

    void StartBuild(Vector3Int c, WorldConfig cfg)
    {
        if (!s_tiles.TryGetValue(c, out var t))
        {
            t = _pool.Count > 0 ? _pool.Pop() : NewTile();
            t.coord = c;
            t.go.name = $"CollisionTile_{c.x}_{c.y}_{c.z}";
            t.go.layer = cfg.terrainLayer;
            t.go.transform.position = (Vector3)c * s_tileSize;
            s_tiles[c] = t;
        }
        t.dirty = false;

        var job = t.job ??= new ChunkMeshJob();
        job.origin = (Vector3)c * s_tileSize;
        job.cells = cfg.cellsPerChunk;
        job.cellSize = s_tileSize / cfg.cellsPerChunk.x;
        job.isoLevel = cfg.isoLevel;
        job.densitySampling = 1;
        job.renderField = _m.PhysicsField;
        job.physicsField = null;
        job.needs = default;
        job.buildCollider = false;
        job.refreshCollider = false;
        job.modsOverlapChunk = _m.Modifications.physical.OverlapsBounds(job.origin, job.origin + Vector3.one * s_tileSize);

        // Phase 1 (worker): mesh. Bind() then uploads on the main thread and
        // starts phase 2 (worker): Physics.BakeMesh. Mesh APIs are main-thread
        // only, and assigning sharedMesh before the bake would cook inline --
        // the exact main-thread cost MarchingChunk's deferred bake avoids.
        // The previously bound collider stays active until phase 2 lands.
        t.phase = 1;
        t.task = Task.Run(() => ChunkMesher.Build(job));
    }

    void Bind(Tile t)
    {
        var job = t.job;
        var finished = t.task;
        t.task = null;
        if (finished.IsFaulted || job.error != null) { Debug.LogException(job.error ?? finished.Exception); t.phase = 0; return; }

        if (t.phase == 1)
        {
            if (job.indexCount == 0)
            {
                bool wasBound = t.bound && t.collider.enabled;
                t.collider.sharedMesh = null;
                t.collider.enabled = false;
                t.mesh.Clear();
                t.bound = true; // "built", just empty (all air / all rock)
                t.phase = 0;
                if (wasBound) TileChanged?.Invoke(TileBounds(t.coord), null, Matrix4x4.identity, false);
                return;
            }
            var verts = new Vector3[job.vertexCount];
            for (int i = 0; i < job.vertexCount; i++) verts[i] = job.packedVerts[i].position;
            // The collider may still reference this mesh from the previous build;
            // detach it first so the upload cannot trigger an inline re-cook.
            t.collider.sharedMesh = null;
            t.mesh.Clear();
            t.mesh.SetVertexBufferParams(job.vertexCount, kLayout);
            t.mesh.SetVertexBufferData(verts, 0, 0, job.vertexCount);
            t.mesh.SetIndexBufferParams(job.indexCount, IndexFormat.UInt32);
            t.mesh.SetIndexBufferData(job.packedIndices, 0, 0, job.indexCount);
            t.mesh.subMeshCount = 1;
            t.mesh.SetSubMesh(0, new SubMeshDescriptor(0, job.indexCount, MeshTopology.Triangles));
            t.mesh.RecalculateBounds();
            int id = t.mesh.GetInstanceID();
            t.phase = 2;
            t.task = Task.Run(() => Physics.BakeMesh(id, false));
            return;
        }

        // phase 2: the cook is cached, binding is cheap
        t.phase = 0;
        t.collider.sharedMesh = t.mesh;
        t.collider.enabled = true;
        t.bound = true;
        TileChanged?.Invoke(TileBounds(t.coord), t.mesh, t.go.transform.localToWorldMatrix, true);
        TerrainPhysicsWaker.Wake(TileBounds(t.coord));
    }

    void OnEdit(Bounds b, bool affectsPhysics)
    {
        if (!affectsPhysics) return;
        b.Expand(1f);
        foreach (var t in s_tiles.Values)
            if (TileBounds(t.coord).Intersects(b)) t.dirty = true;
    }

    Tile NewTile()
    {
        var go = new GameObject("CollisionTile") { hideFlags = HideFlags.DontSaveInEditor };
        go.transform.SetParent(transform, false);
        var col = go.AddComponent<MeshCollider>();
        col.enabled = false;
        var mesh = new Mesh { indexFormat = IndexFormat.UInt32, name = "MC_CollisionTile", hideFlags = HideFlags.DontSaveInEditor };
        mesh.MarkDynamic();
        return new Tile { go = go, collider = col, mesh = mesh };
    }

    void Release(Tile t)
    {
        if (t.bound && t.collider.enabled)
            TileChanged?.Invoke(TileBounds(t.coord), null, Matrix4x4.identity, false);
        t.collider.sharedMesh = null;
        t.collider.enabled = false;
        t.bound = false;
        t.dirty = false;
        t.go.SetActive(true);
        if (_pool.Count < 256) _pool.Push(t); else DestroyTile(t);
    }

    static void DestroyTile(Tile t)
    {
        try { t.task?.Wait(); } catch { }
        if (t.mesh != null) Destroy(t.mesh);
        if (t.go != null) Destroy(t.go);
    }
}
```

Implementation notes for the engineer:
- Check that `TerrainModificationCache.OverlapsBounds(Vector3 min, Vector3 max)` is the signature used in `MCChunkManager` (`_modSystem.visual.OverlapsBounds(bMin, bMax)`). If it differs, match it.
- **Verify vertex space.** Clipmap chunks put `transform.position = coord * S` and use the job's vertices as mesh-local. Step 3's comparison proves the streamer matches; if tile colliders come out offset by `origin`, the mesher emits world-space vertices and the tile's `transform.position` must be `Vector3.zero` instead.
- A tile whose edit arrives mid-build is marked `dirty` and rebuilt on a later frame (step 4 of `Update`).

- [ ] **Step 3: Verify geometry parity in play mode**

Put a `TerrainAnchor` on the player, add `TerrainCollisionStreamer` to the `Terrain` object and tick `ignoreClipmapCoverage`. For one coord under the player (covered by both a clipmap chunk and a tile), compare `MeshCollider.bounds` of the clipmap chunk and the tile: centres within 0.01 m, sizes within 0.01 m. Raycast down at 20 random points in that tile against each collider (`Collider.Raycast`) — hit distances equal within 0.001 m. Untick `ignoreClipmapCoverage` afterwards.

- [ ] **Step 4: Verify distant NPC**

Spawn a capsule with `Rigidbody`, `TerrainRigidbodyGuard`, `TerrainAnchor (physicsRadius 12)` 200 m from the player, dropped from 20 m above `TerrainQuery` ground. Within 3 s it must be resting within 1.2 m of the ground point (not held, not fallen). Console: no exceptions. Profiler (MCP `manage_profiler`): no frame over 33 ms attributable to `TerrainCollisionStreamer.Update`.

- [ ] **Step 5: Verify hand-off**

Walk the player (teleport in 8 m steps, 0.5 s apart) to the NPC. Sample the NPC's y every 0.1 s: it must never drop more than 0.1 m in one sample.

- [ ] **Step 6: Commit**

```bash
git -C Assets/TerrainGen add Scripts/Integration/TerrainCollisionStreamer.cs* Scripts/WorldConfig.cs
git -C Assets/TerrainGen commit -m "feat: collision tiles around terrain anchors outside the LOD0 ring"
```

---

## Phase D — NavMesh

### Task 9: `NavPatchPlanner`

Pure planning of where NavMesh instances live.

- **Flat mode:** exactly one patch, `rotation = identity`, `origin = Vector3.zero` forever (tile grid never shifts → `UpdateNavMeshDataAsync` stays incremental). Its bounds are the union of anchor nav spheres, snapped outward to `quantum` (default 32 m), capped at `maxFlatExtent` (default 1024 m) around the **primary** anchor (the manager target). Anchors outside the cap get no NavMesh (their guard, Task 11, parks them).
- **Radial mode (globe):** anchors are clustered greedily (an anchor joins a cluster if within `patchSize * 0.5 - navRadius` of the cluster's centre); each cluster is one patch whose `rotation = FromToRotation(up, radial)` at a **quantised** centre point, so small moves don't re-plant it. A patch is re-planted only when some member anchor is within `edgeMargin` of its edge (hysteresis). Two patches whose boxes overlap are merged into one at their mean centre. Because no two patches overlap, there is never an ambiguous NavMesh under an agent and no NavMeshLinks are needed.

**Files:**
- Create: `Assets/TerrainGen/Scripts/Integration/NavPatchPlanner.cs`
- Test: `Assets/TerrainGen/Tests/EditMode/NavPatchPlannerTests.cs`

**Interfaces:**
- Produces:
  - `public struct NavPatch { public int id; public Vector3 origin; public Quaternion rotation; public Bounds localBounds; }` — `localBounds` is in the patch frame (`origin`, `rotation`), exactly what `NavMeshBuilder` takes.
  - `public struct NavAnchor { public Vector3 position; public float radius; public bool primary; }`
  - `public sealed class NavPatchPlanner` with fields `public float quantum = 32f, maxFlatExtent = 1024f, patchSize = 256f, edgeMargin = 32f, verticalHalfExtent = 256f;`, `public bool radial;`, `public Vector3 planetCenter;`, and
    `public IReadOnlyList<NavPatch> Plan(IReadOnlyList<NavAnchor> anchors)` — returns patches; a patch keeps its `id` across calls while it is not re-planted (the baker uses the id to decide update vs rebuild).

- [ ] **Step 1: Write the failing tests**

```csharp
using System.Collections.Generic;
using NUnit.Framework;
using UnityEngine;

namespace TerrainGen.Tests
{
    public class NavPatchPlannerTests
    {
        static List<NavAnchor> A(params (Vector3 p, float r)[] xs)
        {
            var l = new List<NavAnchor>();
            for (int i = 0; i < xs.Length; i++) l.Add(new NavAnchor { position = xs[i].p, radius = xs[i].r, primary = i == 0 });
            return l;
        }

        [Test]
        public void FlatIsOnePatchAtOriginWithIdentityRotation()
        {
            var p = new NavPatchPlanner();
            var r = p.Plan(A((new Vector3(100, 5, 40), 40), (new Vector3(300, 0, 40), 40)));
            Assert.That(r.Count, Is.EqualTo(1));
            Assert.That(r[0].origin, Is.EqualTo(Vector3.zero));
            Assert.That(r[0].rotation, Is.EqualTo(Quaternion.identity));
            Assert.That(r[0].localBounds.Contains(new Vector3(100 - 39, 5, 40)), Is.True);
            Assert.That(r[0].localBounds.Contains(new Vector3(300 + 39, 0, 40)), Is.True);
        }

        [Test]
        public void FlatBoundsAreQuantisedSoSmallMovesDoNotChangeThem()
        {
            var p = new NavPatchPlanner();
            var b1 = p.Plan(A((new Vector3(100, 0, 0), 40)))[0].localBounds;
            var b2 = p.Plan(A((new Vector3(103, 0, 0), 40)))[0].localBounds;
            Assert.That(b2, Is.EqualTo(b1));
        }

        [Test]
        public void FlatExtentIsCappedAroundPrimary()
        {
            var p = new NavPatchPlanner { maxFlatExtent = 512 };
            var b = p.Plan(A((Vector3.zero, 40), (new Vector3(5000, 0, 0), 40)))[0].localBounds;
            Assert.That(b.size.x, Is.LessThanOrEqualTo(512f + 1e-3f));
            Assert.That(b.Contains(new Vector3(5000, 0, 0)), Is.False);
        }

        [Test]
        public void RadialPatchUpMatchesRadialDirection()
        {
            var p = new NavPatchPlanner { radial = true, planetCenter = Vector3.zero };
            Vector3 pos = new Vector3(0, 0, 1000);
            var r = p.Plan(A((pos, 40)));
            Assert.That(r.Count, Is.EqualTo(1));
            Assert.That(Vector3.Dot(r[0].rotation * Vector3.up, Vector3.forward), Is.GreaterThan(0.999f));
            Vector3 local = Quaternion.Inverse(r[0].rotation) * (pos - r[0].origin);
            Assert.That(r[0].localBounds.Contains(local), Is.True);
        }

        [Test]
        public void RadialFarApartAnchorsGetSeparateNonOverlappingPatches()
        {
            var p = new NavPatchPlanner { radial = true };
            var r = p.Plan(A((new Vector3(0, 0, 1000), 40), (new Vector3(0, 1000, 0), 40)));
            Assert.That(r.Count, Is.EqualTo(2));
        }

        [Test]
        public void RadialCloseAnchorsShareOnePatch()
        {
            var p = new NavPatchPlanner { radial = true };
            var r = p.Plan(A((new Vector3(0, 0, 1000), 40), (new Vector3(30, 0, 1000), 40)));
            Assert.That(r.Count, Is.EqualTo(1));
        }

        [Test]
        public void RadialPatchKeepsIdUntilAnchorNearsEdge()
        {
            var p = new NavPatchPlanner { radial = true, patchSize = 256, edgeMargin = 32 };
            int id = p.Plan(A((new Vector3(0, 0, 1000), 40)))[0].id;
            Assert.That(p.Plan(A((new Vector3(20, 0, 1000), 40)))[0].id, Is.EqualTo(id));
            Assert.That(p.Plan(A((new Vector3(110, 0, 995), 40)))[0].id, Is.Not.EqualTo(id));
        }
    }
}
```

- [ ] **Step 2: Run — expect compile failure.**

- [ ] **Step 3: Implement**

```csharp
using System.Collections.Generic;
using UnityEngine;

public struct NavAnchor { public Vector3 position; public float radius; public bool primary; }

public struct NavPatch
{
    public int id;
    public Vector3 origin;
    public Quaternion rotation;
    public Bounds localBounds;
}

// Decides where NavMesh instances live. See the integration plan, Task 9.
public sealed class NavPatchPlanner
{
    public float quantum = 32f;
    public float maxFlatExtent = 1024f;
    public float patchSize = 256f;
    public float edgeMargin = 32f;
    public float verticalHalfExtent = 256f;
    public bool radial;
    public Vector3 planetCenter;

    readonly List<NavPatch> _patches = new();
    const int kFlatId = 1;
    int _nextId = kFlatId + 1; // radial ids never collide with the flat patch if the mode flips

    public IReadOnlyList<NavPatch> Plan(IReadOnlyList<NavAnchor> anchors)
    {
        if (!radial) PlanFlat(anchors); else PlanRadial(anchors);
        return _patches;
    }

    void PlanFlat(IReadOnlyList<NavAnchor> anchors)
    {
        _patches.Clear();
        if (anchors.Count == 0) return;

        Vector3 primary = anchors[0].position;
        for (int i = 0; i < anchors.Count; i++) if (anchors[i].primary) { primary = anchors[i].position; break; }
        float half = maxFlatExtent * 0.5f;

        bool any = false;
        Vector3 min = default, max = default;
        foreach (var a in anchors)
        {
            Vector3 lo = a.position - Vector3.one * a.radius, hi = a.position + Vector3.one * a.radius;
            // cap: drop anchors whose sphere leaves the square around the primary
            if (Mathf.Abs(a.position.x - primary.x) + a.radius > half || Mathf.Abs(a.position.z - primary.z) + a.radius > half) continue;
            if (!any) { min = lo; max = hi; any = true; }
            else { min = Vector3.Min(min, lo); max = Vector3.Max(max, hi); }
        }
        if (!any) return;

        min.x = Mathf.Floor(min.x / quantum) * quantum; min.z = Mathf.Floor(min.z / quantum) * quantum;
        max.x = Mathf.Ceil(max.x / quantum) * quantum;  max.z = Mathf.Ceil(max.z / quantum) * quantum;
        float cy = Mathf.Round(primary.y / quantum) * quantum;
        min.y = cy - verticalHalfExtent; max.y = cy + verticalHalfExtent;

        var b = new Bounds((min + max) * 0.5f, max - min);
        _patches.Add(new NavPatch { id = kFlatId, origin = Vector3.zero, rotation = Quaternion.identity, localBounds = b });
    }

    void PlanRadial(IReadOnlyList<NavAnchor> anchors)
    {
        float half = patchSize * 0.5f;
        var next = new List<NavPatch>();
        var assigned = new bool[anchors.Count];

        // 1. keep an existing patch while it holds at least one anchor and none
        //    of its anchors has drifted into the edge margin (hysteresis)
        foreach (var patch in _patches)
        {
            bool holdsAny = false, nearEdge = false;
            var inv = Quaternion.Inverse(patch.rotation);
            for (int i = 0; i < anchors.Count; i++)
            {
                if (assigned[i]) continue;
                Vector3 local = inv * (anchors[i].position - patch.origin);
                float ax = Mathf.Abs(local.x), az = Mathf.Abs(local.z);
                if (ax > half || az > half) continue;           // not this patch's anchor
                holdsAny = true;
                if (ax > half - edgeMargin || az > half - edgeMargin) nearEdge = true;
            }
            if (!holdsAny || nearEdge) continue;                // dropped; its anchors get re-clustered below
            for (int i = 0; i < anchors.Count; i++)
            {
                if (assigned[i]) continue;
                Vector3 local = inv * (anchors[i].position - patch.origin);
                if (Mathf.Abs(local.x) <= half && Mathf.Abs(local.z) <= half) assigned[i] = true;
            }
            next.Add(patch);
        }

        // 2. greedy clusters for the rest
        for (int i = 0; i < anchors.Count; i++)
        {
            if (assigned[i]) continue;
            Vector3 sum = anchors[i].position; int n = 1; assigned[i] = true;
            for (int j = i + 1; j < anchors.Count; j++)
            {
                if (assigned[j]) continue;
                if (Vector3.Distance(anchors[j].position, sum / n) <= half - edgeMargin - anchors[j].radius)
                { sum += anchors[j].position; n++; assigned[j] = true; }
            }
            next.Add(MakeRadial(sum / n));
        }

        // 3. merge overlapping patches (their centres closer than patchSize along the surface)
        for (bool merged = true; merged;)
        {
            merged = false;
            for (int a = 0; a < next.Count && !merged; a++)
            for (int b = a + 1; b < next.Count && !merged; b++)
            {
                if (Vector3.Distance(next[a].origin, next[b].origin) >= patchSize) continue;
                var m = MakeRadial((next[a].origin + next[b].origin) * 0.5f);
                next.RemoveAt(b); next[a] = m; merged = true;
            }
        }

        _patches.Clear();
        _patches.AddRange(next);
    }

    NavPatch MakeRadial(Vector3 worldPoint)
    {
        Vector3 rel = worldPoint - planetCenter;
        float r = rel.magnitude;
        Vector3 up = r > 1e-4f ? rel / r : Vector3.up;
        // quantise the direction so tiny moves reproduce the same frame
        float q = quantum / Mathf.Max(r, 1f);
        Vector3 qUp = new Vector3(Mathf.Round(up.x / q) * q, Mathf.Round(up.y / q) * q, Mathf.Round(up.z / q) * q).normalized;
        Vector3 origin = planetCenter + qUp * Mathf.Round(r / quantum) * quantum;
        var rot = Quaternion.FromToRotation(Vector3.up, qUp);
        // curvature: a patch of half-width h on radius R drops by h^2 / 2R at its edge
        float sag = (patchSize * 0.5f) * (patchSize * 0.5f) / (2f * Mathf.Max(r, 1f));
        var b = new Bounds(Vector3.zero, new Vector3(patchSize, 2f * (verticalHalfExtent + sag), patchSize));
        return new NavPatch { id = _nextId++, origin = origin, rotation = rot, localBounds = b };
    }
}
```

- [ ] **Step 4: Run tests.** Expected: 7 passed. If `RadialPatchKeepsIdUntilAnchorNearsEdge` fails on the third assertion, check that `(110, 0, 995)` projects to `|local.x| > 96` in the kept patch's frame; adjust only the test point, not `edgeMargin`.

- [ ] **Step 5: Commit**

```bash
git -C Assets/TerrainGen add Scripts/Integration/NavPatchPlanner.cs* Tests/EditMode/NavPatchPlannerTests.cs*
git -C Assets/TerrainGen commit -m "feat: NavPatchPlanner for flat and radial nav patches"
```

---

### Task 10: `TerrainNavMesh` runtime baker

**Files:**
- Create: `Assets/TerrainGen/Scripts/Integration/TerrainNavMesh.cs`
- Modify: `Assets/TerrainGen/Scripts/WorldConfig.cs`

**Interfaces:**
- Consumes: `NavPatchPlanner`, `TerrainAnchor.All`, `MarchingChunk.Active`, `MarchingChunk.ColliderMesh`, `MarchingChunk.ColliderChanged`, `MarchingChunk.WorldBounds`, `TerrainCollisionStreamer.ActiveTiles`, `TerrainCollisionStreamer.TileChanged`, `MCChunkManager.Instance` (`target`, `TryGetPlanetCenter`, `worldConfig`).
- Produces:
  - `public class TerrainNavMesh : MonoBehaviour` with `public static TerrainNavMesh Instance`, `public int PatchVersion` (bumped whenever a patch is added/removed/replaced — agents re-validate on change), `public bool IsBuilding`.
  - `public static event Action<List<NavMeshBuildSource>, Bounds> TerrainNavMesh.CollectExtraSources` — `(sources, patchWorldBounds)`; game code and flora (Task 14) append obstacles/buildings here.
  - `WorldConfig.navAgentTypeIds` (`int[]`, default `{ 0 }` = Humanoid), `WorldConfig.navUpdateInterval` (float, default 0.5), `WorldConfig.navBuildHeightMesh` (bool, default true), `WorldConfig.navGameLayers` (`LayerMask`, default nothing) — extra physics-collider layers (buildings, props) collected into the NavMesh.

- [ ] **Step 1: Add config fields** under `[Header("Game Integration")]`:
```csharp
    [Tooltip("NavMesh agent type ids (Navigation window > Agents) to bake for. 0 = Humanoid.")]
    public int[] navAgentTypeIds = { 0 };
    [Tooltip("Minimum seconds between NavMesh updates while terrain collision keeps changing.")]
    public float navUpdateInterval = 0.5f;
    [Tooltip("Bake a height mesh so agents' feet follow bumpy marching-cubes ground instead of the simplified nav polygons.")]
    public bool navBuildHeightMesh = true;
    [Tooltip("Game layers whose physics colliders (buildings, props) are included in the terrain NavMesh.")]
    public LayerMask navGameLayers = 0;
```

- [ ] **Step 2: Implement**

```csharp
using System;
using System.Collections.Generic;
using UnityEngine;
using UnityEngine.AI;

// Runtime NavMesh over the streamed terrain. Sources are terrain COLLIDER
// meshes (clipmap LOD0 chunks + collision tiles): render meshes of coarser
// rings may exist only on the GPU. See the integration plan, Task 10.
public class TerrainNavMesh : MonoBehaviour
{
    public static TerrainNavMesh Instance { get; private set; }
    public static event Action<List<NavMeshBuildSource>, Bounds> CollectExtraSources;

    public int PatchVersion { get; private set; }
    public bool IsBuilding => _ops.Count > 0;

    sealed class Live
    {
        public NavPatch patch;
        public readonly List<NavMeshData> data = new();          // one per agent type
        public readonly List<NavMeshDataInstance> instances = new();
        public readonly List<AsyncOperation> ops = new();
        public bool dirty = true;
        public bool built;   // at least one build finished -- replacements must be built before what they replace is retired
    }

    readonly NavPatchPlanner _planner = new();
    readonly Dictionary<int, Live> _live = new();
    readonly List<AsyncOperation> _ops = new();
    readonly List<NavAnchor> _anchors = new();
    readonly List<NavMeshBuildSource> _sources = new();
    readonly List<NavMeshBuildMarkup> _noMarkups = new();
    readonly List<NavMeshBuildSource> _gameSources = new();
    float _lastUpdate;
    bool _anyDirty = true;
    MCChunkManager _m;

    void OnEnable()
    {
        Instance = this;
        _m = MCChunkManager.Instance ?? FindFirstObjectByType<MCChunkManager>();
        MarchingChunk.ColliderChanged += OnChunk;
        TerrainCollisionStreamer.TileChanged += OnTile;
    }

    void OnDisable()
    {
        MarchingChunk.ColliderChanged -= OnChunk;
        TerrainCollisionStreamer.TileChanged -= OnTile;
        foreach (var l in _live.Values) RemoveLive(l);
        _live.Clear();
        if (Instance == this) Instance = null;
    }

    void OnChunk(MarchingChunk c) => MarkDirty(c.WorldBounds);
    void OnTile(Bounds b, Mesh m, Matrix4x4 t, bool added) => MarkDirty(b);

    void MarkDirty(Bounds world)
    {
        foreach (var l in _live.Values)
            if (WorldBounds(l.patch).Intersects(world)) { l.dirty = true; _anyDirty = true; }
    }

    void Update()
    {
        if (_m == null || _m.worldConfig == null) return;
        var cfg = _m.worldConfig;
        _ops.RemoveAll(o => o.isDone);
        foreach (var l in _live.Values)
            if (l.ops.Count > 0 && l.ops.TrueForAll(o => o.isDone)) { l.ops.Clear(); if (!l.built) { l.built = true; PatchVersion++; } }

        // 1. anchors -> patches
        _anchors.Clear();
        if (_m.target) _anchors.Add(new NavAnchor { position = _m.target.position, radius = 40f, primary = true });
        foreach (var a in TerrainAnchor.All)
            if (a.navRadius > 0f && (!_m.target || a.transform != _m.target))
                _anchors.Add(new NavAnchor { position = a.Position, radius = a.navRadius });

        _planner.radial = _m.TryGetPlanetCenter(out Vector3 pc, out _);
        _planner.planetCenter = pc;
        var patches = _planner.Plan(_anchors);

        // 2. reconcile: ids that disappeared are removed AFTER their replacements exist
        var keep = new HashSet<int>();
        bool changed = false;
        foreach (var p in patches)
        {
            keep.Add(p.id);
            if (_live.TryGetValue(p.id, out var l))
            {
                if (l.patch.localBounds != p.localBounds) { l.patch = p; l.dirty = true; _anyDirty = true; }
            }
            else { _live[p.id] = new Live { patch = p }; _anyDirty = true; changed = true; }
        }

        // 3. build/update dirty patches, throttled, one async batch at a time
        if (_anyDirty && _ops.Count == 0 && Time.time - _lastUpdate >= cfg.navUpdateInterval)
        {
            _lastUpdate = Time.time;
            _anyDirty = false;
            foreach (var l in _live.Values)
            {
                if (!keep.Contains(l.patch.id) || !l.dirty) continue;
                l.dirty = false;
                Build(l, cfg);
            }
        }

        // 4. retire patches the planner dropped, but only once every kept patch
        //    overlapping them has finished a build (no NavMesh gap under agents)
        var dead = new List<int>();
        foreach (var kv in _live)
        {
            if (keep.Contains(kv.Key)) continue;
            Bounds wb = WorldBounds(kv.Value.patch);
            bool covered = true;
            foreach (var other in _live.Values)
                if (keep.Contains(other.patch.id) && !other.built && WorldBounds(other.patch).Intersects(wb)) { covered = false; break; }
            if (covered) dead.Add(kv.Key);
        }
        foreach (var id in dead) { RemoveLive(_live[id]); _live.Remove(id); changed = true; }

        if (changed) PatchVersion++;
    }

    void Build(Live l, WorldConfig cfg)
    {
        Bounds world = WorldBounds(l.patch);
        CollectSources(world, cfg);

        for (int i = 0; i < cfg.navAgentTypeIds.Length; i++)
        {
            var settings = NavMesh.GetSettingsByID(cfg.navAgentTypeIds[i]);
            settings.buildHeightMesh = cfg.navBuildHeightMesh;
            if (l.data.Count <= i)
            {
                var d = new NavMeshData(settings.agentTypeID) { position = l.patch.origin, rotation = l.patch.rotation };
                l.data.Add(d);
                l.instances.Add(NavMesh.AddNavMeshData(d, l.patch.origin, l.patch.rotation));
            }
            var op = NavMeshBuilder.UpdateNavMeshDataAsync(l.data[i], settings, _sources, l.patch.localBounds);
            _ops.Add(op);
            l.ops.Add(op);
        }
    }

    void CollectSources(Bounds world, WorldConfig cfg)
    {
        _sources.Clear();
        foreach (var c in MarchingChunk.Active)
        {
            var mesh = c.ColliderMesh;
            if (mesh == null || !c.WorldBounds.Intersects(world)) continue;
            _sources.Add(new NavMeshBuildSource { shape = NavMeshBuildSourceShape.Mesh, sourceObject = mesh, transform = c.transform.localToWorldMatrix, area = 0 });
        }
        foreach (var (mesh, l2w, b) in TerrainCollisionStreamer.ActiveTiles)
        {
            if (!b.Intersects(world)) continue;
            _sources.Add(new NavMeshBuildSource { shape = NavMeshBuildSourceShape.Mesh, sourceObject = mesh, transform = l2w, area = 0 });
        }
        if (cfg.navGameLayers.value != 0)
        {
            NavMeshBuilder.CollectSources(world, cfg.navGameLayers, NavMeshCollectGeometry.PhysicsColliders, 0, _noMarkups, _gameSources);
            _sources.AddRange(_gameSources);
        }
        CollectExtraSources?.Invoke(_sources, world);
    }

    static Bounds WorldBounds(NavPatch p)
    {
        // conservative world AABB of the rotated local box
        Vector3 c = p.origin + p.rotation * p.localBounds.center;
        Vector3 e = p.localBounds.extents;
        Matrix4x4 r = Matrix4x4.Rotate(p.rotation);
        Vector3 we = new(
            Mathf.Abs(r.m00) * e.x + Mathf.Abs(r.m01) * e.y + Mathf.Abs(r.m02) * e.z,
            Mathf.Abs(r.m10) * e.x + Mathf.Abs(r.m11) * e.y + Mathf.Abs(r.m12) * e.z,
            Mathf.Abs(r.m20) * e.x + Mathf.Abs(r.m21) * e.y + Mathf.Abs(r.m22) * e.z);
        return new Bounds(c, we * 2f);
    }

    static void RemoveLive(Live l)
    {
        foreach (var inst in l.instances) inst.Remove();
        l.instances.Clear();
        l.data.Clear();
    }
}
```

Engineer notes:
- `NavMeshBuilder.UpdateNavMeshDataAsync` reads source meshes when called (main thread). Chunk/tile meshes may be rebuilt later; the next `MarkDirty` rebuilds the affected tiles. **Verify** in Step 4 that the NavMesh update after a single chunk change only takes a fraction of the first build (incremental tiles). If it does not, shrink `localBounds` in the update call to the dirty region's bounds intersected with the patch (keep a per-patch accumulated dirty `Bounds`).
- On the globe, `NavMeshData.rotation`/`position` must be set before the first build; the planner gives each re-planted patch a new id, so rotation never changes on an existing `NavMeshData`.

- [ ] **Step 3: Play-mode check (flat)**

`WorldConfig_Flat` in SampleScene, `demoBootstrap` on, add `TerrainNavMesh` + `TerrainCollisionStreamer` to the `Terrain` object. Wait 10 s. MCP `execute_code`:
```csharp
var p = MCChunkManager.Instance.target.position;
bool near = UnityEngine.AI.NavMesh.SamplePosition(p, out var hit, 3f, UnityEngine.AI.NavMesh.AllAreas);
var tri = UnityEngine.AI.NavMesh.CalculateTriangulation();
return $"near={near} d={(hit.position-p).magnitude:F2} verts={tri.vertices.Length}";
```
Expected: `near=True`, `d < 2.1` (player pivot is 1 m above feet), `verts > 1000`. Screenshot with the NavMesh visualisation enabled (Scene view AI Navigation overlay) around the player.

- [ ] **Step 4: Incremental-update measurement**

Log `Time.realtimeSinceStartup` around first-build completion vs an update triggered by one `CarveSphere(..., affectsPhysics: true)` near the player. Record both numbers in the commit message. Expected: the edit update is < 25% of the first build.

- [ ] **Step 5: Path check**

Pick a point 60 m away on terrain via `TerrainQuery.TryFindGround`, compute `NavMesh.CalculatePath` from the player; expect `PathComplete` on gentle dunes. Try across a canyon wall in the Canyon biome scene (`Assets/Scenes/Biomes/`): expect `PathPartial` or a path around, never through rock.

- [ ] **Step 6: Commit**

```bash
git -C Assets/TerrainGen add Scripts/Integration/TerrainNavMesh.cs* Scripts/WorldConfig.cs
git -C Assets/TerrainGen commit -m "feat: runtime NavMesh over terrain colliders in planned patches"
```

---

### Task 11: `TerrainNavAgentGuard`

A NavMeshAgent placed before its NavMesh exists errors (`"SetDestination" can only be called on an active agent that has been placed on a NavMesh`), and an agent whose patch is swapped (globe re-plant) loses its NavMesh. This guard owns that lifecycle, and coordinates with a Rigidbody when present.

**Rigidbody + agent contract (document it in `INTEGRATION.md`):** while the agent drives, the Rigidbody is kinematic and the agent moves the transform (`updatePosition = true`). When game code wants physics (knockback, ragdoll), it calls `guard.SuspendForPhysics()`; the guard disables the agent and restores the Rigidbody; `guard.ResumeFromPhysics()` samples the NavMesh under the body and `Warp`s.

**Files:**
- Create: `Assets/TerrainGen/Scripts/Integration/TerrainNavAgentGuard.cs`

**Interfaces:**
- Consumes: `TerrainNavMesh.Instance.PatchVersion`, `TerrainRigidbodyGuard.IsHeld` (optional sibling), `PlanetGravity.UpAt`.
- Produces: `public bool Ready` (agent is enabled and on a NavMesh), `public event Action BecameReady`, `public void SuspendForPhysics()`, `public void ResumeFromPhysics()`, `public bool TrySetDestination(Vector3 worldPos)` (stores it while not ready, applies it on `BecameReady`).

- [ ] **Step 1: Implement**

```csharp
using System;
using UnityEngine;
using UnityEngine.AI;

[RequireComponent(typeof(NavMeshAgent))]
public class TerrainNavAgentGuard : MonoBehaviour
{
    public float sampleRadius = 4f;
    public float checkInterval = 0.25f;

    NavMeshAgent _agent;
    Rigidbody _rb;
    TerrainRigidbodyGuard _rbGuard;
    bool _suspended;
    int _seenVersion = -1;
    float _next;
    Vector3? _pendingDestination;

    public bool Ready => _agent.enabled && _agent.isOnNavMesh;
    public event Action BecameReady;

    void Awake()
    {
        _agent = GetComponent<NavMeshAgent>();
        _rb = GetComponent<Rigidbody>();
        _rbGuard = GetComponent<TerrainRigidbodyGuard>();
        _agent.enabled = false; // never let Unity place it before a NavMesh exists
    }

    void Update()
    {
        if (_suspended || Time.time < _next) return;
        _next = Time.time + checkInterval;

        var nav = TerrainNavMesh.Instance;
        int version = nav != null ? nav.PatchVersion : 0;
        bool patchesChanged = version != _seenVersion;
        _seenVersion = version;

        if (_agent.enabled && _agent.isOnNavMesh && !patchesChanged) return;

        if (NavMesh.SamplePosition(transform.position, out var hit, sampleRadius, _agent.areaMask))
        {
            Vector3? dest = _agent.enabled && _agent.hasPath ? _agent.destination : _pendingDestination;
            if (_rb != null) _rb.isKinematic = true;
            if (_rbGuard != null) _rbGuard.enabled = false; // the agent owns vertical placement now
            if (!_agent.enabled) _agent.enabled = true;
            _agent.Warp(hit.position);
            if (dest.HasValue) _agent.SetDestination(dest.Value);
            _pendingDestination = null;
            BecameReady?.Invoke();
        }
        else if (_agent.enabled && !_agent.isOnNavMesh)
        {
            // NavMesh vanished under us (patch retired / outside flat cap): park on physics
            _agent.enabled = false;
            if (_rbGuard != null) _rbGuard.enabled = true;
            if (_rb != null) _rb.isKinematic = false;
        }
    }

    public bool TrySetDestination(Vector3 worldPos)
    {
        if (Ready) return _agent.SetDestination(worldPos);
        _pendingDestination = worldPos;
        return false;
    }

    public void SuspendForPhysics()
    {
        _suspended = true;
        if (_agent.enabled) { _pendingDestination = _agent.hasPath ? _agent.destination : _pendingDestination; _agent.enabled = false; }
        if (_rb != null) _rb.isKinematic = false;
        if (_rbGuard != null) _rbGuard.enabled = true;
    }

    public void ResumeFromPhysics()
    {
        _suspended = false;
        _next = 0f;
        _seenVersion = -1; // force a re-sample + warp next Update
    }
}
```

- [ ] **Step 2: Play-mode check (flat)**

Spawn 10 NPC capsules (Rigidbody + `TerrainRigidbodyGuard` + `NavMeshAgent` + `TerrainNavAgentGuard` + `TerrainAnchor(physics 12, nav 30)`) at random points 30–150 m from the player **at play start** (before any NavMesh). Call `TrySetDestination` to the player's position on each. Expected within 15 s: every guard `Ready == true`, every agent `remainingDistance` decreasing, console has zero `"can only be called on an active agent"` errors. Call `SuspendForPhysics()` on one, `AddForce(up*8, VelocityChange)`, wait 2 s, `ResumeFromPhysics()`; it becomes `Ready` again and continues.

- [ ] **Step 3: Commit**

```bash
git -C Assets/TerrainGen add Scripts/Integration/TerrainNavAgentGuard.cs*
git -C Assets/TerrainGen commit -m "feat: TerrainNavAgentGuard handles NavMesh lifecycle and physics hand-off"
```

---

## Phase E — Globe navigation

Physics on the globe needs no extra work beyond A–C: colliders are world-space, `PlanetGravityBody` already provides radial gravity for Rigidbodies, `TerrainQuery`/`TerrainRigidbodyGuard` take radial up. The collision streamer's tiles are world-axis boxes exactly like clipmap chunks, and `PlanetField.TryGetEmptySkip` keeps deep/sky tiles free.

The open question is Unity behaviour on rotated NavMesh instances. Task 12 settles it before Task 13 commits to the radial planner path.

### Task 12: Globe NavMesh spike (decision gate)

**Files:**
- Create (throwaway, not committed unless it passes): `Assets/TerrainGen/Scenes/Spikes/GlobeNavSpike.unity` via `Editor/BiomeTestScenes.cs`-style menu or MCP scene creation.

- [ ] **Step 1:** Scene with manager on `Config/WorldConfig.asset` (globe), demo player, `TerrainCollisionStreamer`, `TerrainNavMesh`. Teleport the player to a point ~45° between two cube-face axes (worst triplanar-blend zone) using `TryGetPlanetSpawnPoint`.
- [ ] **Step 2: Rotated instance works.** After 15 s, `NavMesh.SamplePosition(player, 3)` succeeds; the `NavMeshData.rotation` up is within 1° of `PlanetGravity.UpAt(player)`.
- [ ] **Step 3: Agent orientation.** Spawn an agent with `PlanetGravityBody (alignToSurface)` + guard; `agent.updateUpAxis` default. Walk it 100 m. Record: does the transform stay upright relative to radial up (angle < 10° at 100 m on radius 1000)? If `updateUpAxis` fights `PlanetGravityBody`, set `updateRotation = false` and let `PlanetGravityBody` + look-at-velocity own rotation; record which works.
- [ ] **Step 4: Re-plant hitch.** Walk the agent across a patch edge. Measure the frames the agent is not `Ready` (target ≤ 3 at 0.25 s check interval → reduce interval to 0.05 for this test) and the build time of the new 256 m patch.
- [ ] **Step 5: Curvature limits.** At `radius = 1000`, check the NavMesh covers the patch corners (sag = 16 m at 256 m patch). If slopes at corners exceed the agent's `maxSlope`, reduce `patchSize` to 160.
- [ ] **Step 6: Decision.** Write results into `Assets/TerrainGen/INTEGRATION.md` under "Globe NavMesh findings". Gate:
  - **Pass (Steps 2–4 all OK):** proceed to Task 13 as written.
  - **Fail on agent orientation:** Task 13 adds a custom mover: agent `updatePosition = false`, `updateRotation = false`, body moved by `Rigidbody.MovePosition(agent.nextPosition)` and rotated by `PlanetGravityBody`.
  - **Fail on rotated instances entirely:** drop NavMesh for the globe; Task 13 becomes a steering layer (`NavMesh`-free, density-field line-of-sight + local avoidance) — write a separate plan for it; do not improvise inside this one.

### Task 13: Radial patches in production

Assumes Task 12 passed.

**Files:**
- Modify: `Assets/TerrainGen/Scripts/Integration/TerrainNavMesh.cs`
- Modify: `Assets/TerrainGen/Scripts/WorldConfig.cs` (`navPatchSize` default 256, `navEdgeMargin` default 32)
- Modify: `Assets/TerrainGen/Tests/EditMode/NavPatchPlannerTests.cs`

- [ ] **Step 1: Failing test for re-plant ordering** — add to `NavPatchPlannerTests`:
```csharp
        [Test]
        public void RadialReplantProducesPatchContainingAnchorAwayFromEdge()
        {
            var p = new NavPatchPlanner { radial = true, patchSize = 256, edgeMargin = 32 };
            p.Plan(A((new Vector3(0, 0, 1000), 40)));
            var r = p.Plan(A((new Vector3(110, 0, 995), 40)));
            Assert.That(r.Count, Is.EqualTo(1));
            Vector3 local = Quaternion.Inverse(r[0].rotation) * (new Vector3(110, 0, 995) - r[0].origin);
            Assert.That(Mathf.Abs(local.x), Is.LessThan(128 - 32));
            Assert.That(Mathf.Abs(local.z), Is.LessThan(128 - 32));
        }
```
- [ ] **Step 2: Run** — expected to pass already if Task 9's `MakeRadial` quantisation keeps the re-planted origin near the anchor; if it fails, lower the direction quantum in `MakeRadial` from `quantum` to `quantum * 0.25f` and re-run all planner tests.
- [ ] **Step 3: Wire config** — in `TerrainNavMesh.Update` before `Plan`: `_planner.patchSize = cfg.navPatchSize; _planner.edgeMargin = cfg.navEdgeMargin;`.
- [ ] **Step 4: Swap without gaps** — Task 10 already retires a dropped patch only after overlapping replacements report `built`. Re-run the Task 12 Step 4 measurement; agents must be not-Ready for ≤ 1 check interval. If they are not, the gap is the guard's `checkInterval`: have `TerrainNavAgentGuard` subscribe to `PatchVersion` changes every frame (compare in `Update` before the interval gate).
- [ ] **Step 5: Apply the Task 12 orientation decision** (either nothing, or the custom mover path) and re-run Task 11 Step 2 on the globe.
- [ ] **Step 6: Commit**

```bash
git -C Assets/TerrainGen add Scripts/Integration Scripts/WorldConfig.cs Tests/EditMode/NavPatchPlannerTests.cs INTEGRATION.md
git -C Assets/TerrainGen commit -m "feat: radial nav patches for the globe"
```

---

## Phase F — Flora obstacles

### Task 14: Trees block bodies and carve the NavMesh

Today plants are GPU-instanced matrices only (`PlantScatter`, "NOTHING IS A GAMEOBJECT"), so bodies and agents walk through trunks. Plots are a pure function of `(PlantWorld, plot id)` and are built only around the scatter's target.

**Files:**
- Modify: `Assets/TerrainGen/Scripts/Flora/PlantWorld.cs` (`PlantSpecies.obstacleRadius`, `obstacleHeight`; 0 = no obstacle)
- Modify: `Assets/TerrainGen/Scripts/Flora/PlantScatter.cs` (public query)
- Create: `Assets/TerrainGen/Scripts/Integration/FloraObstacles.cs`
- Test: `Assets/TerrainGen/Tests/EditMode/FloraObstacleTests.cs`

**Interfaces:**
- Produces: `public void PlantScatter.GetObstacles(Bounds world, List<(Vector3 basePos, Vector3 up, float radius, float height)> result)` — returns obstacles from **already-built** plots intersecting `world`; `FloraObstacles` subscribes to `TerrainNavMesh.CollectExtraSources` (adds `NavMeshBuildSourceShape.Capsule` sources with `area = 1` (Not Walkable)) and keeps pooled `CapsuleCollider`s on the terrain layer within each `TerrainAnchor.physicsRadius`.

- [ ] **Step 1:** Use the `vegetation-scatter` and `plant-colonies` skills before touching `PlantScatter`.
- [ ] **Step 2: Failing test** — for a species with `obstacleRadius = 0.4`, `obstacleHeight = 3`, a built plot's `GetObstacles` returns one entry per instance with `basePos` equal to the instance translation and `radius = 0.4 * instanceScale`. (Build a plot synchronously through the scatter's existing editor/test path; read `PlantScatterEditor.cs` for how the editor forces a build.)
- [ ] **Step 3: Implement** `obstacleRadius/obstacleHeight` fields, `GetObstacles` (walk `Plot.items` for plots whose `centre ± reach` intersects `world`; scale from `trs.lossyScale.x`), and `FloraObstacles` (capsule source: `transform = Matrix4x4.TRS(basePos + up*height/2, FromToRotation(up, up), new Vector3(2r, height, 2r))`, `size = Vector3.one`).
- [ ] **Step 4: Gap to resolve during implementation** — plots are only built around `PlantScatter.target`. Distant anchors therefore get no tree obstacles. Acceptable for the first game version (distant NPCs walk through trees nobody sees). Record it in `INTEGRATION.md` "Known limitations"; do not extend plot building to anchors in this task.
- [ ] **Step 5: Play check** — a NavMesh path near a grove routes around trunks (screenshot with NavMesh overlay); a Rigidbody ball rolled at a trunk bounces.
- [ ] **Step 6: Commit**

```bash
git -C Assets/TerrainGen add Scripts/Flora/PlantWorld.cs Scripts/Flora/PlantScatter.cs Scripts/Integration/FloraObstacles.cs* Tests/EditMode/FloraObstacleTests.cs*
git -C Assets/TerrainGen commit -m "feat: tree trunks as physics and NavMesh obstacles"
```

---

## Phase G — Game handoff

### Task 15: Integration guide and reference scene

**Files:**
- Create: `Assets/TerrainGen/INTEGRATION.md`
- Create: `Assets/Scenes/GameIntegration.unity` (parent repo; demo only)

- [ ] **Step 1: Write `INTEGRATION.md`** with these sections, each filled from the implemented code:
  1. **Add the package** — add `Assets/TerrainGen` as a submodule; required packages (`com.unity.ai.navigation` 2.0.9, URP); game asmdefs reference `TerrainGen.Runtime`.
  2. **Scene setup** — one `MCChunkManager` (chunk prefab, `WorldConfig`, compute shaders), `TerrainCollisionStreamer` and `TerrainNavMesh` on the same object; `WorldConfig`: `demoBootstrap = false`, `terrainLayer = <game Terrain layer>`, `navAgentTypeIds` = the game's agent types, `navGameLayers` = building/prop layers.
  3. **Player** — `TerrainTarget` (drives the clipmap) + `TerrainAnchor`; flat: normal Rigidbody gravity; globe: `PlanetGravityBody` (set `Rigidbody.useGravity` off — it does so in `Awake`).
  4. **NPC prefab checklist** — `Rigidbody` (Interpolate, Continuous Speculative), `TerrainRigidbodyGuard`, `NavMeshAgent`, `TerrainNavAgentGuard`, `TerrainAnchor` for NPCs that must simulate away from the player; globe adds `PlanetGravityBody`. Use `TrySetDestination` instead of `agent.SetDestination`. Use `SuspendForPhysics`/`ResumeFromPhysics` around knockback.
  5. **Spawning** — `TerrainQuery.TryFindGround(pos, 50, 200, out p, out n)`; spawn at `p + n * halfHeight`; the guards handle "ground not cooked yet".
  6. **Edits** — `MCChunkManager.Instance.Modifications.CarveSphere/StampSphere(..., affectsPhysics: true)` for gameplay holes; NavMesh and sleeping bodies update automatically; `affectsPhysics: false` is visual only.
  7. **Budgets** — collision tiles per anchor ≈ `(2·physicsRadius/16)^2 × 2` (e.g. radius 20 → ~12 tiles); keep anchored NPCs count × tiles under `maxCollisionTiles`; NavMesh flat cap `maxFlatExtent`.
  8. **Known limitations** — flat NavMesh only within `maxFlatExtent` of the player; trees only obstruct near `PlantScatter.target`; unanchored NPCs outside the player's 96 m LOD0 box are held by `TerrainRigidbodyGuard` (frozen); globe findings from Task 12.
- [ ] **Step 2: Reference scene** — `GameIntegration.unity`: flat config with `demoBootstrap` off. Player wired by hand the way the game will (no new controller code): a capsule with `CharacterController`, `SimplePlayerController` (auto-adds `GravityAligner` + `CharacterGravity`), `TerrainTarget`, `TerrainAnchor`, camera child; in the Inspector set `GravityAligner.terrain` = the manager and `CharacterGravity.densityField` = the config's effective density. Add 20 NPCs as in Task 11 Step 2 and a stack of 10 Rigidbody crates. Play 60 s: no errors, all NPCs `Ready`, no NPC below `TerrainQuery` ground by > 1 m at any 1 s sample.
- [ ] **Step 3: Full test run** — MCP `run_tests` EditMode for `TerrainGen.Tests` and `TerrainGen.LSystem.Tests`. Expected: all pass.
- [ ] **Step 4: Commit** (submodule, then pointer bump in the parent)

```bash
git -C Assets/TerrainGen add INTEGRATION.md
git -C Assets/TerrainGen commit -m "docs: game integration guide"
git add Assets/TerrainGen Assets/Scenes/GameIntegration.unity Assets/Scenes/GameIntegration.unity.meta
git commit -m "chore: bump TerrainGen, add game integration scene"
```

---

## Risks to watch while executing

| Risk | Where it shows | Mitigation in plan |
|---|---|---|
| asmdef split surfaces hidden dependencies | Task 1 console | Fix references; never move game files |
| Collision tile vertices in a different space than clipmap chunks | Task 8 Step 3 parity check | Documented switch (`transform.position = zero`) |
| NavMesh update not incremental → hitches on every footprint-scale physical edit | Task 10 Step 4 | Shrink update bounds to the dirty region |
| Streamer + clipmap double work around the player | Profiler, Task 8 Step 4 | Planner excludes LOD0-box coords; only anchors outside build tiles |
| Many anchored NPCs spread widely | tile cap / nav cap | `maxCollisionTiles`, `maxFlatExtent`, guards park the rest |
| Agent orientation on rotated NavMesh | Task 12 | Decision gate with two concrete fallbacks |
