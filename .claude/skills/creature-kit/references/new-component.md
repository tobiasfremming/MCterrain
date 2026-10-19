# Adding a component type

The kit's contracts are in (Phases 1-4 on `feat/creature-kit`): part/module base types
(`Scripts/Creatures/Kit/CreaturePart.cs`, `CreatureModule.cs`, `KitAttributes.cs`, `PartSocket.cs`), the bone
layout (`CreatureBoneLayout`), mesh emission (`PartMeshEmitter`), part runtimes and locomotion modes
(`Kit/PartRuntime.cs`), behaviours (`Kit/Brains.cs`), the lab roster (`CreatureLabRoster.asset`) and the
look-layer table (`Kit/PartLayers.cs`). Worked examples to copy: **FinStrip** (mesh only), **Antenna**
(runtime with bones), **Shimmer** (a look module), **Layers** (look rows).

## First: does something fit?

`Config/Creatures/CATALOGUE.md` (generated; `creature_kit.py catalogue`): every part and module, its
parameters with unit and size rule, who uses it, the material-layer registry. Reuse with new parameters,
`Repeat`, `mirror` or a `Layers` row before adding a type. A new type is justified only when data cannot
express it; never edit `CreatureSim`, `CreatureLegs`, the mesh builders or the renderer for one species.

## The recipe

New files under `Scripts/Creatures/Kit/` (fewer merge conflicts); namespace `CreatureKit`; `[Serializable]`.

1. **Data.** `[Part("Name", PartKind.X, Summary=, System=, Bones=, MaterialLayers=new[]{..}, UseWhen=)]` on
   a `sealed partial class : CreaturePart` (or `[Module("Name", CreatureModule.Locomotion|Behaviour|Look)]`
   on a `CreatureModule`). **Every field** gets `[Param(unit, meaning, Min/Max, Example)]`
   (`KitAttributes_EveryPublicFieldHasParam`). Units carry the size rule: Metres x s; Seconds and
   MetresPerSecond x sqrt s; Hz and DegPerSecond / sqrt s; angles, fractions, counts size-free. Author
   at scale 1; the runtime scales by the individual's `sizeScale` (`PartCtx.Size.L`, `.T`).
2. **Bones and validation.** `BoneCount(in SpeciesCtx)` asks the layout for a contiguous range (block order
   spine: Body, Limb, Wing, Sense, then Chain, Fin, Rigid - a new kind appends after every shipped bone, so
   existing layouts and goldens stay put). Find your bones with `c.Species.Layout.Start(c.Index)`; never
   compute `N + 3 * leg`. `Validate` returns null or the first problem naming `id`;
   `CollectReferences` lists the part ids it names (compose checks they exist). Copy arrays in
   `CopyArrays` (compose clones parts before it edits them).
3. **Mesh: `EmitMesh(PartMeshEmitter m, in PartCtx c)`.** Draw in the rest pose (`m.Rest` is a fresh sim on
   flat ground, `m.Bones` its rest bone worlds) from the emitter's primitives: `Vertex`, `Tri`, `Ring`, `Pole`,
   `Stitch`, `Grid`, `Ellipsoid`, `Tube`, `Horn`, `SpineAt` (the rest spine's sections); skins `Rigid(bone)`, `Blend(b0, b1, w1)`. Vertex layout: uv0 = (arc m, angle/2pi),
   uv1 = (**part id**, dorsal -1..1), uv2 = (bone0, bone1, w0, w1), w0 the heavier. **`MeshOrder`**: keep the
   default 100 for a new type - it appends after every existing vertex, so every shipped mesh stays
   byte-equal (`CreatureMeshEmitterTests.Mesh_Bytes_EqualLegacy`). Shipped classes: body 0, limbs 1,
   eyes 2, cones 3, fins 4, antennae 5, wings 6. Runs once per species: it may allocate.
4. **Runtime, only if it moves: `CreateRuntime(in PartCtx c)` -> `IPartRuntime`.** Built in the sim's
   constructor (the only place a part may allocate; `c.Sim` is null when there is no sim: return null).
   **`PartStage`**: `AfterChain` (walking sub-step, after the chain step), `AfterGround` (after grounding,
   the length restore and the climb up field), `AfterLimbs` (every sub-step of every mode: antennae),
   `Late` (once per tick), `None` (bones only: eyes). `Step` / `WriteBones(dst, offset)` (write
   `dst[offset + yourBone]`; the rest pose's call makes your bind poses) / `EncapsulateBounds` /
   `DrawDebug` (F3) must not allocate (`CreaturePartRuntimeTests.Kit_NoGC`). One runtime for all parts
   of a type is fine (Antenna: the first owns a flat-array system for every strand).
5. **Locomotion module: `CreateMode(CreatureSim, in ModeCtx)` -> `ILocomotionMode`** (Priority, highest
   first; `SubStep` returns true when it moved the body, otherwise Walk runs; Fly is the example). Climb
   stays a Walk modifier, not a mode.
6. **Behaviour module: `CreateBehaviour(in BehaviourCtx)` -> `IBehaviour`** (`Utility`, `Enter`, `Tick` ->
   `BrainOutput.target`). Any behaviour the shipped brains do not cover makes `BrainFactory` build a
   `ModularBrain` over all the species' behaviours (minimum hold x sqrt size, switch margin). Utilities:
   `Wander.BaseUtility` 0.1 is the idle default to beat. Containment is structural (the sim clamps the
   head to the safe disc): clamp your own target into the area too, so it does not grind the wall.
7. **Look: pick a layer row, not a shader edit.** The shader shades a part id by its row in the species'
   `_PartLayers` table: a **shading model** (Skin, Chitin, Membrane, Eye, Claw) + layers (pattern body /
   limb / none, scale grain normal / fine / none, sheen, shimmer) + a tint (own colour, or a palette
   colour: Pattern, Band, Dorsal, Belly, Membrane). Either reuse an id (a fin is membrane, 8) or take the
   next free id (`PartLayers.NextFree`, in the catalogue) and add its row to `PartLayers.Registry`; a
   species can restyle any row with the `Layers` look module. Colours in a row are sRGB in the asset,
   decoded with `.linear` once in C# (`SetVectorArray` does not decode). **A new shading model** is the
   only shader edit: `ShadingModel` + `CreatureLayers.hlsl` + its branch in `Creature.shader`, the CPU
   proof in `CreaturePartLayerTests` and the Unity pixel guard `CreatureShaderLayerTests`. Never reuse
   an id. The octopus (4-bone, `CreatureOctopus.shader`) is its own family and ignores the table.
8. **Tests, RED first.** Part tests in `Tests/EditMode/Creature<Name>Tests.cs` (copy
   `CreatureFinStripTests`, `CreatureAntennaTests`): its invariants (no flips over the bend sweep, size
   rule at 0.9x / 1.1x, settles without jitter), a RED proof that each test bites. Add the part to an
   example species, `creature_kit.py check <Species>` green (the 12 generic checks), regenerate the
   catalogue (`creature_kit.py catalogue --write`; `Catalogue_IsFresh` fails otherwise), the full
   harness suite, `unity-compile`, `compile_check.py`; Unity once.

## Rules

- Spine bodies have a rigid head by default (`SpineBody.rigidHeadJoints` -1 = auto from the profile's neck,
  a step >= 5 % narrower in the front half; N overrides, 0 = off). Soft bodies (`SoftBody`, octopus) always
  deform. General fixes like this become defaults for the body type they suit, not universal rules.
- Systems, not one virtual call per bone (limbs stay typed arrays inside `CreatureLegs`;
  `Perf_100Lizards` is at its bound).
- Zero GC per frame, main thread, no new packages; every size-dependent value from `sizeScale`.
- New source files are picked up by the harness automatically; one that needs Unity-only API goes in
  `UnityOnlySources` (or a test in `UnityOnlyTests`) of `CreatureHarness.csproj`, with the reason.
- Shader edits stay additive (other branches touch these files; expect merges).
