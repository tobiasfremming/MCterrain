---
name: creature-kit
description: Create new and exotic animals for the MarchingCubes creature module from reusable components (bodies, legs, wings, fins, tentacles, behaviours, looks) and prove them offline before Unity - the creature kit. Covers the authoring loop (check what exists, copy the nearest species, compose, check, lab, Unity once, hand-off), the checked-in offline harness Assets/TerrainGen/Tools~/CreatureHarness with scripts/creature_kit.py (check <Species>, test <Class>, unity-compile, --real-unity), the generic kit fixture CreatureKitTests that every species asset must pass (12 checks), adding a new component type, and the lab habitat. KIT IN PROGRESS - until Phase 2 a species is still authored with the legacy CreatureSpecies fields (creature-module skill). Trigger on new animal, exotic creature, creature kit, compose a species, reusable part, fins, centipede, hexadrake, sand eel, tentacle crab, creature_kit.py, CreatureKitTests, offline harness, Tools~/CreatureHarness.
---

# Creature kit

> **Status 2026-10-18: kit in progress.** Phase 0 is in (offline harness, generic kit fixture over the
> legacy fields, this skeleton). Parts, modules, `CompiledSpecies`, the catalogue and the lab roster come
> in Phases 1-3 (design `docs/superpowers/specs/2026-10-18-creature-kit-design.md`, plan
> `docs/superpowers/plans/2026-10-18-creature-kit.md`). **Until Phase 2, author a
> species with the legacy `CreatureSpecies` fields** (`creature-module` skill, its new-species.md
> reference) and use this skill for the loop, the harness and the checks.

Goal (user): agents make new, exotic animals from reusable components. **Check what exists and reuse it
first; add a new component type only when nothing fits.** Prototypes live in the Creature Lab. The user
judges the look (R32): hand Unity over with a "what to look at" note, no screenshots.

Non-negotiables (design §0): looks first, speed second; every size-dependent value derives from
`sizeScale` (lengths x s, times x sqrt s); zero GC per frame; main thread; climbing contact from real
geometry only; legacy species bit-identical (golden hashes).

## The loop

1. **Catalogue first.** What parts and behaviours exist, who uses them (Phase 2 generates
   `Config/Creatures/CATALOGUE.md`; until then: `creature-module` SKILL.md "What exists" and the assets).
2. **Copy the nearest species** in `Assets/TerrainGen/Config/Creatures/` and edit it (`references/authoring.md`).
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
```

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
