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

## Apex parts recipe (feat/apex-v3, 2026-10-21)

The Apex (`Tools~/SpeciesGen/Apex.py`, scale 3.5) is built from seven kit parts and nothing legacy. Copy its generator;
numbers below are at scale 1. Reasons and measurements: `.superpowers/sdd/2026-10-20-apex-redesign/` reports.

| part | use when | proven numbers (Apex) |
|---|---|---|
| **FlowBody** | a body drawn as ONE surface: raised neck, hump, keel, ribbon tail (no rings per part) | 26 joints x 0.1; clearances 0.93 / 0.83 / 0.69 / 0.52 at joints 0 / 2.5 / 4.5 / 7; chest key hump 0.06 (sharpness 8), keel 0.08, flank 0.02; tail `blade 1` from joint 12.5; `rigidHeadJoints 2`; `restAtStance 1` |
| **CrestBeakHead** | a long beaked head with crest pair, teeth, gape, on joint 0 | defaults (skull 0.26 x 0.055 x 0.067, V pair splay 30, sickle `flare` 2.6, teeth 16, fangs 2, rest gape 7, call 62); Apex deepens the jaw: `jawDepth 1.1`, `chinDepth 0.65`, `throatDepth 0.8` |
| **PitRow** | breathing holes / spiracles on a FlowBody | 5 per side, `fromU 0.08` `toU 0.16`, `angleDeg -35`, slits `aspect 2.2` `slantDeg 50`, growing toward the head |
| **Dewlap** | a throat sail on its own swinging chain | joints 1..7, 5 stations x 3 links, `depthAt {0.14,0.24,0.28,0.25,0.17}`, `edgeStraightness 0.45`, rest = part defaults (25 deg, damping 0.35, coupling 0.6) |
| **DrakeLeg** | slim digitigrade hind leg: raised hock, toes, talons | upper 0.24 / lower 0.26, `ankleHeight 0.14`, 3 toes + hallux, `restOffset (0.18,0,-0.1)` |
| **FleshWing** | thick soft folding wing walked on a club (rides a `Leg2Bone` arm, named by id) | fingers {1.75..0.85}, spread {36..84}, fold {160..168}, `bindFold 0.3`, `spanMaxDeg 20`, `groundLiftDeg 82`; see traps |
| **TailFlourish** | decorative tail: loop standing, roll + curl in the air; never steers the sim | `fromJoint` = tail root, `groundLoopDeg 12` (13 joints turn >= 141 deg; an 11-segment tail only ~70), air roll 70 / curl 9 |

Wiring:
- Arm `Leg2Bone` at the shoulder joint, DrakeLeg at the hips; FleshWing `arm` = the arm's id.
- `Fly` flags, all four (else the steep-neck body flips in flight): `airNeckStance` (0.2-0.9 clean; Apex 0.3),
  `launchHeadOnNeck`, `touchdownAtStance`, `launchTailBySegment`. Head steadiness: `headStabilise 0.6`.
- A heavy flyer that must bob: `kLift 0.1`, `kGrip 1`, `demandFloor 0.12`, `glideDemand 0.14`, `airLevel 0.8`,
  `avoidLookahead 2.4`, `flareDistance 1.6` (girdle 12.9 % of body p-p, head 0.20 x). `kLift 0.75` just glides: 0 beats.

Safe ranges and traps (measured; more in the parts' `[Param]` text):
- **FleshWing: steep side-by-side blades come from the arm, not a flag.** Arm upper 0.2 / lower 0.5 (upper << lower), wrist
  `restOffset (0.06,0,-0.22)`, `pole (0.2,1,-0.4)` (`pole.x` 0 drifts the club 10 %). `bindFold` 0.2-0.45 passes the fold
  sweep (0 and >= 0.6 invert); `spanMaxDeg` 20 (12 saturates, no visible lag). A raised neck pitches the chest up and leans the
  blades in: raise `groundLiftDeg` (68 -> 82) until the tips stand on their own side and never cross. Test the species with
  `CreatureFleshWingTests.SteepProblem` / `BroadProblem`.
- **Dewlap:** `rearSweep` >= ~0.5, `links` <= 3 (0.35 / 4 fold under a heavy bob), `rootThickness` < ~0.02 (wider leaves the
  throat's quads). The 0.25 rear cap is a small sliver at the chest end.
- **Stance segments <= ~65 deg** (a walking frame rolls 180 deg past 90; the guard fails at 85). Apex steepest: 47.6.
- **FlowBody `Section` is the drawn surface, not `halfHeight`** (a blade-0 oval is capped at `ovalMaxAspect` 2). Parts that sit
  on the body query `Section` / `SurfaceAt`.
- **Material slots: 6 kit slots (10..15).** Apex named kinds: crest, pit, dewlap, wingfan, wingstripe, mouth. Share with
  `FlowBody.tailKind` / `dorsalStripeKind` (Apex: both `wingfan`). Teeth: `ivory-teeth` costs a slot; legacy `"teeth"` row 13
  IS a kit slot (no saving); the Apex uses legacy `"band"` row 9 + a Layers row (fragile: anything else drawing row 9 turns
  ivory). Talons: Layers row 2.
- **TailFlourish must be the LAST part** (as Tuck, Burrow: they cannot share a species). Parts reading the tail's `sim.Joints`
  do not follow the posed tail.
- **Mesh budget:** the surface parts replay their rest mesh from `RestMeshCache` (testing.md); the Apex builds in ~2 ms offline.
- Non-default skulls (jawFraction 0.3, bigger) can leave pinched edges: run `Head_Solids_AreClosed`-style checks on yours.

## Groups (kit services)

A species the lab keeps as a group (roster `count` > 1) gets check 14 (no member touches another). Behaviours that
need their group use `CreatureKit.KitGroup.For(species, area)` (join once, `Live`, `Nearest(me, d, visibleOnly)`,
`Neighbours`, `CountConcealed`, `Shared<T>()` for group state such as a school's waypoint) and `Separation`
(`ClosestApproach` within a horizon, `Weight`). School runs on it; the Delver's `CreatureGroup` (frame-fresh,
cross-species per enclosure) is still its own. `LabGroup` is how the lab places, seeds and sizes a group.

## Hand-off note (every new animal)

The scene and play-mode setup, then "what to look at" per part (e.g. "fins ripple with the body, no
crease on the tightest S-bend"), and the 0.9x / 1.1x individuals side by side.
