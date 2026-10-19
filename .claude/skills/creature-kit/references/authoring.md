# Authoring a species

> Kit in progress. **Today (until Phase 2) a species is a legacy `CreatureSpecies` asset**: follow
> `creature-module` `references/new-species.md` for every field. The kit form below is the target
> (design §2-§3) and is filled in as Phases 2-3 land.

## Today: legacy fields

1. Copy the nearest asset in `Assets/TerrainGen/Config/Creatures/` (monitor, snake, beetle, daddy-longlegs,
   tarantula, winged serpent; `TestSnake`/`TestHexapod` are fixtures). Author at scale 1, in metres.
2. Edit the YAML or the Inspector: spine joints, legs (two-bone, or arthropod `segments[]`), wings +
   flight, look, climb, `scale` and `look.sizeJitter`.
3. `creature_kit.py species` - it loads, `Validate` is ok, no unknown keys.
4. `creature_kit.py check <Species>` - the 12 generic checks. Fix findings in the data first.
5. Species-specific tests (copy `CreatureDesertSpeciesTests` / `CreatureSpiderTests`), then the lab.

Heads: Spine bodies have a rigid head by default (`SpineBody.rigidHeadJoints` -1 = auto from the profile's neck, a step >= 5 % narrower in the front half; N overrides, 0 = off). Soft bodies (`SoftBody`, octopus) always deform. General fixes like this become defaults for the body type they suit, not universal rules.

What derives from size: lengths x `sizeScale`, times x sqrt(`sizeScale`), rates / sqrt; accelerations are
size-invariant (Froude). The kit's `Size` check proves it for the species.

## Target (Phase 2+): parts and modules

A species = body plan + **parts** (what it is: SpineBody, SoftBody, Leg2Bone, ArthropodLeg, Wing, Tentacle,
FinStrip, RigidCone, Eyes, Antenna) + **modules** (what it does / how it looks: Walk, Slither, Climb, Fly,
Wander, Flee, Ambush, Skin, Chitin, Membrane, Cloak) + scale, as `[SerializeReference]` lists in the asset
with `mirror: 1` and `Repeat {count, fromJoint, toJoint, lastScale, template}` sugar expanded at load into a
`CompiledSpecies`. Unknown YAML keys are errors. Gait groups come from `Walk.pattern` (Diagonal, Tripod,
Tetrapod, Alternate, Wave). Command to come: `creature_kit.py new <Name> --from <Species>`.

## Hand-off note (every new animal)

The scene and play-mode setup, then "what to look at" per part (e.g. "fins ripple with the body, no
crease on the tightest S-bend"), and the 0.9x / 1.1x individuals side by side.
