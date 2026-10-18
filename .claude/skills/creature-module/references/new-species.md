# Adding a species from data

Contents: recipe · size pipeline · spine · choosing the leg model · legacy legs ·
arthropod legs (in progress) · locomotion · climbing data · look · part-id registry ·
worked check.

All lengths are **authored at scale 1, in metres**. A body plan other than a spine
with legs (octopus, wyvern) is in `body-plans.md`.

## Recipe

1. **Start from the nearest shipped asset** in `Assets/TerrainGen/Config/Creatures/`
   (Create > Marching Cubes > Creature Species makes an empty one; copying is faster).

   | asset | branch | body | legs | scale |
   |---|---|---|---|---|
   | `DesertMonitor` | feat/creatures | 26 joints, 1.59 m | 4 legacy, diagonal pairs | 4 (≈ 6.4 m), `climb.canClimb` |
   | `DesertSnake` (viper) | feat/creatures | 32 joints @ 3 cm | none; undulation 45° @ 0.625 Hz | 2.5 |
   | `DesertBeetle` (darkling) | feat/creatures (legacy legs) | low body | 6 legacy at joints 2/3/5, tripods, splayed feet | 3, 2 sub-steps |
   | `TestSnake`, `TestHexapod` | feat/creatures | test fixtures (Task 10 extensibility proof) | | 1 |
   | `DaddyLongLegs`, `Tarantula`, beetle v2 | **feat/creature-legs, in progress** | spider bodies | 8 arthropod legs × 7 segments + palps | 1 (beetle 3) |
   | `TreeOctopus` | **feat/creature-octopus, in progress** | Cephalopod plan | 8 arms | being set for 4× |
   | `WingedSerpent` | **feat/creature-wyvern, in progress** | 32 joints @ 8 cm | wing arms + hind legs | 1 |

   For quick iteration build the species in code (`Tests/EditMode/CreatureTestSpecies.cs`:
   `Lizardish`, `Snake`, `Hexapod`) and run it in the offline harness (`workflow.md`).
2. **Sketch the body as numbers**: body length = `headCapLength + spacing·(N−1) +
   tailTipLength` (monitor 0.05 + 0.06·25 + 0.04 ≈ 1.59 m), a half-width profile,
   girdle positions, leg lengths relative to body width.
3. **Fill in spine, legs, locomotion.** `sp.Validate()` returns null or the first
   problem; `CreatureWorld.Spawn` throws on an invalid species.
4. **Write the tests before tuning** (`tuning-and-tests.md`), loading the asset with
   `AssetDatabase.LoadAssetAtPath<CreatureSpecies>` (light; never load heavy assets).
5. **Tune in the harness**, then run the species' tests in Unity once.
6. **Add to the lab**: `Assets/Scenes/CreatureLab.unity`, `Creatures` object,
   append to `CreatureLab.species` and a parallel `scaleOverrides` entry (0 = species
   scale). The scene is LFS; commit it only with the user's go-ahead.
   `Marching Cubes/Rebuild Creature Lab` regenerates the scene from `kSpeciesPaths`
   and drops hand wiring: extend `kSpeciesPaths` instead (the legs branch lists 5 species).
7. **Hand Unity to the user** with what to look at (R32).

## Size pipeline (R21, R22, user requirement 2026-10-18)

- `CreatureSpecies.scale` (top of the Inspector) sets the species' size.
- Each individual: `sizeScale = scale × (1 ± look.sizeJitter)`, drawn from the
  spawn seed. Individuals of one species **must** vary a little and still look right.
- `CreatureLab.scaleOverrides[k]` overrides `scale` per enclosure (0 = species).
  Editing either in play mode respawns that enclosure live
  (`CreatureSpecies.Changed` → `CreatureLab.ApplyScales`) and rebuilds the curb.
- `TimeScale = √sizeScale` (Froude): step duration, speed, turn rate, up rate, beat
  period scale by it.
- Enclosure radius = max(5 m, 2 × body length × max scale); enclosures, probe
  windows, ground cache, renderer bounds all follow `sizeScale`.

**The rule:** every size-dependent quantity in a sim, brain, mesh or lab derives
from `sizeScale` (lengths ×s, times ×√s). Never introduce a second size source (the
octopus's early "OctopusLab auto-fit" scale was dropped for this reason). Never
store a world-space constant that was tuned at one size. Add a size-variation test
(spawn at 0.9 × and 1.1 × scale; the species' acceptance bounds must hold at both).

Caveat: a live scale-up can grow an enclosure into its neighbour (not re-placed;
a deferred minor).

## Spine (`joints[]`, `SpineJoint`)

| field | meaning | guidance |
|---|---|---|
| `spacing` | segment length (m) | monitor 0.06, snake 0.03–0.05, wyvern 0.08 |
| `halfWidth`, `halfHeight` | elliptical cross-section semi-axes | wider than tall reads as a lizard; keep the profile smooth (Catmull-Rom in the mesh) |
| `clearance` | joint centre above ground | ≈ halfHeight + belly gap for walkers; = halfHeight for a snake; taper to the tail tip |
| `bendLimitDeg` | cone half-angle vs previous segment | monitor 20° trunk / 25° tail, snake 30°; larger = tighter coils, more crease risk |
| `rigid` | bend limit 0 | head joints (monitor 1–2, snake 1) |
| `headCapLength`, `tailTipLength` | snout cap, pointed tail tip | |
| `eyeJoint`, `eyeOffset`, `eyeRadius` | glossy eye spheres | spiders add `eyeCluster[]` (legs branch) |
| `ringSegments`, `ringsPerSegment` | mesh resolution | 16 × 3 walkers, 16 × 2 snake |

## Choosing the leg model

| choose | when | how |
|---|---|---|
| **legacy two-bone** | vertebrate limbs: lizards, monitors, the wyvern's wing arm and hind legs | `segments` empty; upper/lower lengths, pole, knee blend |
| **arthropod (synergy IK)** | insects, spiders, anything with visible segments, high knees, a flat tarsus | `segments[]` of 3–7 `LegSegment`s; **`feat/creature-legs` only until merged** |

The beetle on `feat/creatures` still uses legacy legs, which the user called
"questionable at best". Insects and spiders should use arthropod legs once the
branch lands; do not tune more insects on two-bone legs. Wings may not use
arthropod legs (Validate). Legacy legs must stay bit-identical:
`LegacyLegsGoldenTests` hashes 600 ticks of bone matrices + mesh for DesertMonitor,
TestHexapod, Lizardish and DesertSnake.

## Legacy legs (`legs[]`, `LegSpec`): any count, 0 for a snake

| field | meaning | guidance |
|---|---|---|
| `attachJoint`, `side` (−1 L, +1 R) | spine joint and side | a joint with legs on **both** sides is a girdle (drives sway) |
| `shoulderOffset` | shoulder, attach frame, x mirrored | x ≈ halfWidth so the shoulder blob sinks in |
| `restOffset` | foot rest point, attach frame (y ignored, projected) | x = splay; front z > 0 (monitor 0.095, rear 0.01); further out/forward = more reach (R16). Its x − girdle halfWidth is the **rest gap** that drives the trunk keep-out (R28) |
| `upperLength`, `lowerLength`, radii | limb bones | monitor 0.145/0.135, r 0.03/0.019; too short = slow choppy walk (stride-limited speed, R8) |
| `pole` | knee direction hint | **clear forward/back component**: front z < 0, rear z > 0; monitor (0.6, 0.6, ∓0.9). A mostly lateral pole folds the skin (700–950 inverted tri-frames) |
| `stepThreshold`, `stepDuration`, `stepLift`, `overshoot` | step trigger, time (× √scale), apex, landing lead | monitor 0.11 / 0.12–0.13 s / ⅓ threshold / 0.08 |
| `gaitGroup` (0..31) | **one group steps at a time** | quadruped diagonals FL+RR=0, FR+RL=1; tripods L1+R2+L3=0, R1+L2+R3=1 |
| `footLength`, `toeCount` | foot pad and toes | |
| `forwardSwingLimitDeg`, `backSwingLimitDeg` | upper-bone swing limits (R16; 0 = 55°) | monitor 75/50. Past: step; +2°: slow; +10°: stop |
| `kneeRangeDeg`, `kneeFlexDeg` | knee deviation from rest (0 = 35°); flexion side | monitor 50 / 18 |
| `kneeBlend` | mesh knee blend (R19; 0 = 0.45, max 0.49) | raise on MaxBend knee inversions |

Rest points slide outward uphill, and feet the trunk sweeps over step away (R28
keep-out, data-driven by the rest gap). Both are generic.

## Arthropod legs (in progress, `feat/creature-legs`)

Spec: `docs/superpowers/specs/2026-10-17-multi-segment-legs-spider-design.md`.
Each joint bend is `rest_i + s·κ_i + β·σ_i`: `s` (reach synergy) is solved for reach
by safeguarded Newton (~3 iterations), `β` (lift synergy) comes from the swing. Yaw
and pitch are closed form; the tarsus lies at the contact angle. Stateless, so
deterministic and pop-free; the authored silhouette holds at every reach.

`LegSegment` fields: `length`, `radiusStart/End`, `restBendDeg` (segment 0: elevation),
`min/maxBendDeg`, `flexWeight` κ (the knee ±1), `liftWeight` σ, `axisTiltDeg`,
`knuckle` (joint bulb ≥ 1.15 × radius hides sockets), `bandStart/End` (knee band
colour, part 9).

Per-leg arthropod fields: `contactAngleDeg` (0 = 20), `kneeLiftDeg`, **`swingRetract`**
(0..0.5; mid-swing pull of the foot toward the coxa: this is what lifts the knee,
because β alone is cancelled by the reach solve), `elevMin/MaxDeg`, `liftDelay`
(metachronal stagger, 0..0.5), `kneeJoint`, `legSides`, `feeler` (pedipalp: posed,
never plants, out of gait/throttle/grip/sway). Reinterpreted: forward/back swing
limits = coxa yaw, knee range/flex = s range. Species: `gaitBob {amplitude, hz,
damping}`, `eyeCluster[]`, `appendages[]` (chelicerae, fangs).

Validate needs: ≥ 3 segments, lengths > 0, min ≤ rest ≤ max, some κ ≠ 0, and a
**monotone reach run** containing rest ± stepThreshold (a non-monotone run flipped
0.56 m in the prototype). Comfort zone as fractions of reach length: rest ≈ 0.65
radial, threshold ≈ 0.25, overshoot ≈ 0.12; non-overlapping coxa yaw sectors stop
legs crossing. Spiders: alternating tetrapods (L1 R2 L3 R4 / R1 L2 R3 L4).

Shipped tunes (scale 1): pholcid 8 legs × 7 segments, leg I 1.19 m (≈ 2.4 m span),
speed 0.5, step 0.32 s, liftDelay 0.12, kneeLift 20°, bob 1.8 Hz ζ 0.25; tarantula
legs 0.36–0.45 m, speed 0.15, step 0.45 s, bob 1.2 Hz ζ 0.7, **sheen only, no
bristles**, near-black with muted orange knee bands; beetle v2 coxa/femur/tibia/
tarsus 0.02/0.095/0.11/0.06, contact 30°, kneeLift 12°. Spiders do not climb yet.

## Locomotion

| field | meaning | shipped |
|---|---|---|
| `speed` | head cruise at scale 1 (× √scale) | monitor 0.9 (real cruise stride-capped at 0.62 m/s) |
| `turnRateDeg` | heading change limit | 160 walkers, 240 snake |
| `accel`, `turnSlowdown` | | 2–3, 0.3–0.5 |
| `undulationDeg`, `undulationHz` | lateral head wave, fades when idle | monitor 6° @ 1.4 Hz; snakes need a **long wave** (R27): wavelength ≈ speed/Hz ≥ ~0.7 body length, because the drag chain low-passes short waves |
| `gaitSwayDeg`, `gaitRollDeg` | girdles swing toward the reaching leg; roll over the planted side | monitor 12 / 3 ("slightly", R18) |
| `subSteps` | fixed sub-steps per frame | monitor/snake 1 (perf), beetle 2 |

## Climbing data

Set `climb.canClimb` and leave the rest at 0 = default unless a test asks for it.
Fields and defaults: `climbing.md`.

## Look (`CreatureLook`, read by `Creature.shader`)

| field | meaning |
|---|---|
| `dorsal`, `flank`, `belly`, `pattern` | palette, **authored sRGB** (the renderer's `SetColor` decodes them once) |
| `patternType` | None 0, Bands 1, Spots 2, Stripes 3, BandedSpots 4 |
| `patternScale` | **bands per metre** of rest arc length (monitor 9, snake 11, hexapod 18) |
| `spotScale` | spot size relative to the band period (monitor 0.08 → 0.5–1 cm speckles; 3–4 cm blotches read wrong) |
| `patternContrast`, `patternSoftness` | 0.55–0.7, 0.25–0.3 |
| `smoothness`, `rimStrength`, `subsurface` | gloss, rim, warm terminator |
| `sizeJitter` | ± fraction of scale (the per-individual size) |
| `hueJitter` | **in turns**; keep near 0.01 (0.03 turned sand olive) |
| `valueJitter` | ± brightness fraction |
| legs branch | `bandColor`, `sheen`, `sheenColor` |
| wyvern branch | `membrane`, `membraneTranslucency`, `veinContrast`, `membraneRim` |

Sandy creatures read darker and cooler than the sand: warm the palette. Use
`CreatureDisplace` (vertex hook) for scale geometry, not mesh hacks.

## Part-id registry (uv1.x, one id per triangle)

| id | part | owner |
|---|---|---|
| 0 | body | CreatureMeshBuilder |
| 1 | leg | CreatureMeshBuilder, ArthropodLegMesh; wyvern finger tubes |
| 2 | foot / claw | CreatureMeshBuilder, ArthropodLegMesh; wyvern thumb claw |
| 3 | eye | CreatureMeshBuilder (`PartEye`), OctopusMeshBuilder |
| 4, 5, 6, 7 | octopus arm, web, mantle, siphon | OctopusMeshBuilder (octopus branch) |
| 8 | wyvern membrane | WingedMeshBuilder (wyvern branch) |
| 9 | arthropod knee band | ArthropodLegMesh (legs branch) |

Older spec text says membrane 7 and band 4/bristle 5; those were superseded. The
next free id is 10. A shader branch per id must not change other ids' pixels.

## Worked check: the monitor's gait acceptance (R8, R16)

At scale 1 on a flat plane: cruise ≥ 0.5 m/s (0.62), front foot lands ≥ 0.6 ×
(upper + lower) ahead of its shoulder (0.63), stride ≥ 0.9 × (1.01), tight-turn swing
within limits (59–60°), MaxBend 0 inversions; trunk clearance in turns +6.5 cm (R28).
The tune is **sensitive**: re-run `CreatureMonitorTests` after any monitor change.
