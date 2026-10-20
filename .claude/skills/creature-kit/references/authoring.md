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
Tetrapod, Alternate, Wave).

### Scaffold and generate (kit services, 2026-10-20)

- `creature_kit.py new <Name> --from <Species|archetype>` writes `Config/Creatures/<Name>.asset` (+ `.meta`, fresh
  guid; a legacy source is kit-converted first) and its generator `Tools~/SpeciesGen/<Name>.py` (`--gen-dir` for your
  scratch folder): the asset as Python data (`sp.add_part('ArthropodLeg', {...})`) that rebuilds it byte for byte.
  Archetypes: `arthropod.spider`, `arthropod.crab` (the plan with every number 0 = form default).
- Edit the generator, run `python <Name>.py <Assets/TerrainGen>`, then `check`. Or patch an asset in place:
  `K = kityaml; sp = K.load(path); sp.part('plan')['legLength'] = 0.8; sp.save(path)` - only what you touch changes
  (every shipped asset round-trips: `creature_kit.py yaml-selftest`).
- **One YAML library**: `scripts/kityaml.py` (this skill). Never copy a writer into a scratch folder; an old generator
  switches by `import kityaml as kitgen` (its `write`, `f`, `v3`, `col`, `sock`, `key`, `profile_joints`; its `emit` is
  `emit_lines`) or as the kit5 `kityaml` (`num`, `V`, `C`, `Ref`, `emit`, `at`, `asset`, `meta`) - same bytes. Floats
  you set are written as Unity writes a float32 (shortest round trip). `.meta` files: `write_asset_meta`,
  `write_script_meta`.
- The look loop: `creature_kit.py render <Name> --phase walk,launch,glide`; numbers: `stats`; poses that fold:
  `trace --phase P --part ID` (testing.md, debugging tools).

## Start from an archetype (feat/arthropod-archetype, 2026-10-20)

For a spider or a crab, **do not type legs**: list one `ArthropodPlan` part (`Kit/Archetypes/Arthropod/`) and set a
handful of anatomical numbers (0 = the form's default); compose expands it into the body, carapace, legs, palps or
chelipeds, eyes (crab: folding `EyeStalk`s), an optional rock `Tuck`, and default Walk / Wander / Skin / Chitin.
Shipped users: `RockCrab` (stone crab: compact, Oval, tuck), `TentacleCrab` (king crab: Pear, 3 long pairs).

- What it derives (the kit services, `Kit/Services/`): **RestStance** puts every foot where the leg's own rest pose
  puts it and sets the body height so the longest pair stands unbent (IK s = 0, pitch ~ 0: the leg you designed is
  the leg you see); **GaitDefaults** gives threshold 0.12 L, overshoot 0.07 L, lift 0.03 / 0.045 L, step time and
  cruise speed in Froude units; **LegFamilies** (arachnid 7 segments = the tarantula's, decapod 6) scaled per pair by
  a leg formula and fanned front..back; **CrabShell** outlines (Oval, Pear, with a flat belly: `LoftKey.belly`), legs
  on the shell's underside, chelipeds under the front margin; **CrabFold** derives the tuck (legs flat round the
  rim, claws across the face, stalks folded) - no FoldFit search.
- Crab defaults: sideways travel, posture 1.15 (arched legs with room to reach out and pull in sideways), coxa swing
  35 deg, speed 0.1 Froude, legs flattened 0.35 (`legFlatten`). Compose errors (never exceptions): legPairs 0..6, a
  legFormula per pair, posture 0 or 0.6..1.4, and "the legs hold the shell's belly X mm off the ground" (< 0.15 of the
  dome: lengthen `legLength` or lower `posture`).
- **Override path:** (1) plan numbers; (2) an explicit part with a generated id replaces it in its slot - a mirrored
  base id (`leg1`) both sides, a side id (`leg1.R`) that side, `crusherClaw` the claw, `tuck` the fold; an explicit
  module replaces the default of its type; (3) added parts layer on (SpineField on `carapace`, LimbSpines on `leg0`,
  Tendril, RigidCone). Generated ids: spider body, leg0..N-1, palp, chelicera, eyes; crab body, carapace, leg0..N-1,
  crusher, cutter, crusherClaw, cutterClaw, stalk, eyes, tuck. `CompiledSpecies.GeneratedBy(id)` tells which.
- The parity test (`CreatureArchetypeTests.SpiderForm_IsTheTarantula`) pins the spider form to the Tarantula (shape,
  rest stance, gait); change an archetype only with it and the shipped crabs' tests green.
- Look loop (one command, offline): `python Assets/TerrainGen/Tools~/SpikeLook/look.py --tg <TG> --out <dir> [--check]
  A,B C,D` - per species a 4-view sheet, a tucked sheet for a species with a Tuck (`<Species>_tuck.png`), rest-stance
  and gait metrics (`metrics.txt`), a side-by-side `compare.png`.

## Phase 5 recipes (feat/kit-animals)

- **Many legs:** `Repeat {count, fromJoint, toJoint, lastScale, template}` with a mirrored `ArthropodLeg`
  (GiantCentipede: 21 pairs on every other joint of a pinched body). **Wave gait:** `Walk.pattern Wave`,
  `waveGroups` G (legs per side in one wavelength; each foot is in the air 1/G of the time, duty 1 - 1/G),
  `waveTailToHead` for a millipede's direct wave. One group is in the air at a time, so the speed is
  stride-limited: cycle = G x stepDuration. Keep `turnRateDeg` low for a slow, long body (a fast turn in place
  whips a coil at its bend limits and drags planted feet) and `accel` high enough to brake inside the throttle
  ramp (braking distance < 6 % of the reach).
- **Six limbs (wings + four legs):** the Wing's arm `role: 3` (Folded); its `restOffset` is the folded wrist in
  the attach frame (not projected). Hexadrake: wrist (0.45, 0.10, 0.30), pole (0, 0.6, -1) on a 2.8 m dragon -
  the middle of the region where membrane and arm never flip; `groundTallStance 0`, `groundWristLift 0`.
- **Tentacles on a spine body:** `Tendril` (not `Tentacle`, which is the octopus' soft-body arm); `layer 9`
  shades it in the Chitin band colour. `reach 0` = a writhing feeler that never touches down.
- **Hide by folding up (rock mimic):** for a crab, `ArthropodPlan.tuck` (the folds derived, below is the manual way).
  A `Tuck` part LAST in the parts list; `LegFold` rows give each ArthropodLeg's
  fold (`yawDeg` of the fold plane, one `pitchDeg` per segment: 0 out level, 90 up, 180 back in, -90 down; a mirrored
  leg's base id folds both); `EyeStalk` parts fold to their `tuckDirection` (stalks first, and up first on the peek);
  `crouch` lowers the body. Fold the limbs INTO the shell (a closed RigidLoft hides them): RockCrab's walking legs
  [30, 168, 62, -12, -62], claws yaw -50 [15, 172, 60, -175]. Scares: `CreatureSim.Scare(intensity)` from any behaviour,
  or `randomScareSeconds` (per individual; a lab group's consecutive seeds start golden-ratio staggered).
  `CreatureTuckTests.Tuck_Curled_NothingPokesOut` measures every limb vertex against the lumpy shell - scan the fold
  numbers with it (a scratch `HarnessExtra` test) and keep the middle of a passing region. A boulder shell:
  `RigidLoft` with `lumpHeight` ~0.03 x its width, blunt `RigidCone` knobs (`radiusEnd` ~0.55 x `radiusStart`), Skin
  Spots in a pale lichen colour, `Layers` row 0 with `noGrain` (scale grain reads as reptile, not stone).
- Look: `Layers` rows turn the body into glossy cuticle (`model 1` Chitin), claws/horns/cones into keratin
  (`model 4` Claw, part 2 - note part 2 is also the Leg2Bone foot and every RigidCone).
- Writing kit YAML by hand is error-prone: a small generator (Python emitting the SerializeReference blocks,
  `template: {rid: N}` for a Repeat) keeps tuning sweeps fast; the asset stays the source of truth.

## Groups (kit services)

A species the lab keeps as a group (roster `count` > 1) gets check 14 (no member touches another). Behaviours that
need their group use `CreatureKit.KitGroup.For(species, area)` (join once, `Live`, `Nearest(me, d, visibleOnly)`,
`Neighbours`, `CountConcealed`, `Shared<T>()` for group state such as a school's waypoint) and `Separation`
(`ClosestApproach` within a horizon, `Weight`). School runs on it; the Delver's `CreatureGroup` (frame-fresh,
cross-species per enclosure) is still its own. `LabGroup` is how the lab places, seeds and sizes a group.

## Hand-off note (every new animal)

The scene and play-mode setup, then "what to look at" per part (e.g. "fins ripple with the body, no
crease on the tightest S-bend"), and the 0.9x / 1.1x individuals side by side.
