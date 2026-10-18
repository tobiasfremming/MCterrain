# Adding a component type

> Kit in progress: the part/module base types (`Kit/CreaturePart.cs`, `CreatureModule.cs`,
> `KitAttributes.cs`, `PartSocket.cs`) arrive in T2.1, `PartMeshEmitter` in T3.1, part runtimes in T3.2.
> Until then a new capability is a **generic data-backed change** to the legacy model (as `ClimbSpec`,
> `LegSpec.segments`, `WingSpec` were), keeping every other species bit-identical.

## First: does something fit?

Check the catalogue (Phase 2: `Config/Creatures/CATALOGUE.md`; today the `creature-module` "What
exists" table and `references/body-plans.md` there). Reuse with new parameters before adding a type.

## The recipe (target, design §3e)

1. Data class with `[Part]` / `[Param]` (every parameter has a `Unit`: Metres x s, Seconds and
   MetresPerSecond x sqrt s, Hz and DegPerSecond / sqrt s).
2. `BoneCount(ctx)` (the registry assigns a contiguous range), `Validate`, `EmitMesh` through
   `PartMeshEmitter` primitives (Tube, Ring, Ellipsoid, Horn, MembraneStrip).
3. A runtime (`IPartRuntime`, stage AfterChain / AfterGround / AfterLimbs / Late) only if it moves; it
   is the only place allowed to allocate (at creation). `DrawDebug` for the F3 view.
4. A shading model (Skin, Chitin, Membrane, Eye, Claw); a new one takes the next part id (registry:
   0 body, 1 leg, 2 foot, 3 eye, 4-7 octopus, 8 membrane, 9 arthropod band) and a pixel guard.
5. `[PartTests(typeof(X))]` RED first; add it to an example species; regenerate the catalogue; harness
   green; Unity once.

## Rules

- Never edit core files for one species. Systems, not one virtual call per bone (limbs stay typed
  arrays inside `CreatureLegs`; `Perf_100Lizards` is at its bound).
- New runtime code: zero GC per frame, main thread, no new packages.
- New source files are picked up by the harness automatically; if one needs Unity-only API, add it to
  `UnityOnlySources` in `CreatureHarness.csproj` with the reason.
