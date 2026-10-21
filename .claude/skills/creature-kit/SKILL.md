---
name: creature-kit
description: Create new and exotic animals for the MarchingCubes creature module from reusable components (bodies, legs, wings, fins, tentacles, behaviours, looks) and prove them offline before Unity - the creature kit. Covers the authoring loop (check what exists, copy the nearest species, compose, check, lab, Unity once, hand-off), the checked-in offline harness Assets/TerrainGen/Tools~/CreatureHarness with scripts/creature_kit.py (check <Species>, test <Class>, unity-compile, --real-unity), the generic kit fixture CreatureKitTests that every species asset must pass (12 checks), adding a new component type, and the lab habitat. KIT IN PROGRESS - until Phase 2 a species is still authored with the legacy CreatureSpecies fields (creature-module skill). Trigger on new animal, exotic creature, creature kit, compose a species, reusable part, fins, centipede, hexadrake, sand eel, tentacle crab, creature_kit.py, CreatureKitTests, offline harness, Tools~/CreatureHarness.
---

# Creature kit

> **Status 2026-10-19: kit in progress** on `feat/creature-kit` (design
> `docs/superpowers/specs/2026-10-18-creature-kit-design.md`, plan `docs/superpowers/plans/2026-10-18-creature-kit.md`).
> In: harness + generic kit (Phase 0), bone layout (1), parts/modules/`CompiledSpecies`/catalogue (2),
> part runtimes, mesh emitter, one renderer path, `ModularBrain`, lab roster (3), look-layer table (4,
> offline; its Unity pixel guard not yet run). Phase 5 (new parts, exotic animals) offline on `feat/kit-animals`:
> FinnedSandEel, GiantCentipede (Walk.pattern Wave), Hexadrake (LimbRole.Folded), TentacleCrab (Tendril). Shipped
> species are still legacy assets behind the adapter (decision 4: convert later, `kit-convert`).

Goal (user): agents make new, exotic animals from reusable components. **Check what exists and reuse it
first; add a new component type only when nothing fits.** Prototypes live in the Creature Lab. The user
judges the look (R32): hand Unity over with a "what to look at" note, no screenshots.

Non-negotiables (design §0): looks first, speed second; every size-dependent value derives from
`sizeScale` (lengths x s, times x sqrt s); zero GC per frame; main thread; climbing contact from real
geometry only; legacy species bit-identical (golden hashes).

## The loop

1. **Catalogue first.** What parts and behaviours exist, who uses them, the material-layer registry:
   `Config/Creatures/CATALOGUE.md` (`creature_kit.py catalogue` says fresh or stale; `--write` regenerates).
2. **Start from an archetype** (spiders, crabs: one `ArthropodPlan` part + overrides) or **copy the nearest species** in `Assets/TerrainGen/Config/Creatures/` and edit it (`references/authoring.md`).
3. **Check offline**: `creature_kit.py check <Species>` until green (`references/testing.md`).
4. **New component** only if data cannot express it (`references/new-component.md`).
5. **Lab**: its habitat and enclosure (`references/lab.md`).
6. **Gates**: `creature_kit.py unity-compile`, `compile_check.py`, the harness suite.
7. **Unity once** per finished animal (one test class per `run_tests` job), then the user hand-off.

## The harness, in short

`Assets/TerrainGen/Tools~/CreatureHarness/` (Unity ignores `~` folders): a net8 console app that compiles
the real `Scripts/Creatures/**/*.cs` and the creature EditMode tests against stubbed `UnityEngine`
(default) or the real 6000.2.6f2 CoreModule (`--real-unity`). Species load straight from their `.asset`
YAML. Driver: `scripts/creature_kit.py`.

```
python .claude/skills/creature-kit/scripts/creature_kit.py check DesertMonitor --tg <worktree>/Assets/TerrainGen
python .claude/skills/creature-kit/scripts/creature_kit.py test CreatureLegTests LegacyLegsGoldenTests
python .claude/skills/creature-kit/scripts/creature_kit.py unity-compile      # Scripts + Tests vs real Unity DLLs
python .claude/skills/creature-kit/scripts/creature_kit.py catalogue --write  # regenerate CATALOGUE.md + catalogue.json
python .claude/skills/creature-kit/scripts/creature_kit.py kit-convert DesertSnake KitSnake   # legacy -> kit asset
python .claude/skills/creature-kit/scripts/creature_kit.py new StoneCrab --from arthropod.crab   # or --from <Species>
python .claude/skills/creature-kit/scripts/creature_kit.py render Apex --phase wing-walk,beat,glide   # the look loop
python .claude/skills/creature-kit/scripts/creature_kit.py stats Tarantula     # gait / stance / cost numbers
python .claude/skills/creature-kit/scripts/creature_kit.py trace Apex --phase touchdown --part neck   # bone trace CSV
```

Kit services (2026-10-20, feat/kit-services; `references/testing.md`, `references/authoring.md`): checks 13 **PoseSweep**
(the mesh through every phase the species' own brain and modules reach: launch, beats, glide, stoop, flare, touchdown,
wing-walk, burrow, tuck, display - inverted triangles, flipped normals, kinks, with phase, part and position) and 14
**Group** (a roster group of `count` never touches, capsules fitted to the real mesh); `Gait` also checks the drawn feet.
One YAML library for generators: `scripts/kityaml.py` (never copy a writer again). Groups: `KitGroup` / `Separation`.

Apex redesign (2026-10-21, `feat/apex-v3`, spec `docs/superpowers/specs/2026-10-20-apex-redesign-design.md`): seven new parts, recipe in
`references/authoring.md` ("Apex parts recipe"): **FlowBody** (one drawn-surface chain, head to tail tip), **CrestBeakHead**,
**PitRow**, **Dewlap**, **DrakeLeg**, **FleshWing**, **TailFlourish**. Four opt-in `FlightSpec` flags (off = shipped flyers
bit-identical): `airNeckStance`, `launchHeadOnNeck`, `touchdownAtStance`, `launchTailBySegment`; plus
`CreatureSpecies.restAtSpacing` (set by `FlowBody.restAtStance`) for a bind that keeps a raised neck's stance. Generator:
`Tools~/SpeciesGen/Apex.py`. Lessons: `references/testing.md` ("Apex redesign lessons").

Offline is not Unity: .NET MathF rounds differently from Mono, so goldens differ per runtime and long or
chaotic runs can drift. Known cases are listed in the harness (`kKnown` in `Program.cs`, "offline" vs
"finding") and reported XFAIL; a pass there reports XPASS so the entry is removed.

## Rules

- A failing kit check is a **finding**: fix the species or the code, never loosen the check. Record it in
  `kKnown` as a finding until fixed (it fails in Unity too).
- Skips are about the species (`CreatureKitAssets.SkipReason`: cephalopod, legless), never "it fails".
- Never edit core files (`CreatureSim`, `CreatureLegs`, the mesh builders, the renderer) for one species.
- Never edit shared test files to make the harness run them: exclude in the csproj with the reason.
- Small commits; scratch in your own folder; worktrees outside `Assets/` (`creature-module` workflow).
