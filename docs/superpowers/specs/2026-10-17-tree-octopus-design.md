# Tree octopus: design

Status: design, 2026-10-17. Builds on `2026-10-17-creature-climbing-design.md` (ISurfaceProbe) and `2026-10-16-creature-module-design.md`. Branch: submodule `feat/creature-octopus`, cut from `feat/creature-climbing` once `SurfaceProbes.cs` is committed.

## 0. Binding constraints (user)

- Contact on real geometry only: every tentacle/body contact comes from `ISurfaceProbe.Probe/Cast` on real colliders (plant bark LOD0 via ClimbableFlora, terrain, SpaceGame colliders). No capsules, SDFs or fitted cylinders as contact.
- Skeleton hints allowed (user decision 1) for perception/planning only (which branch to reach for). Every hint is confirmed by a probe before commitment. Optional: a null `IBranchHints` = probe-only (SpaceGame).
- Independent tentacles (user decision 2): each arm is its own chain with its own state machine — picks its own target, feels, anchors, wraps, releases. The brain publishes only an intent; nothing places tips centrally.
- Body driven by the chains (user decision 3): mantle and head are a dynamic soft body pulled by anchored tentacle tension and gravity. No own path or animation.
- Squishy body (user decision 4): shape-matching lattice — squash/stretch under pull, jiggle, volume preservation.
- Generic, zero GC per tick, main thread, one instanced draw per species. Priorities: looks, then speed.

## 1. Fit with what exists

Reused: CreatureSpecies (look, scale, TimeScale = sqrt(size)), EnclosureArea + climbing's 3D containment, ISurfaceProbe / CompositeSurfaceProbe / CreatureSurfaces / ClimbableFlora, the TickAll backface window, CreatureDebugView, the look shader.
Renderer fits with one generic change: `ICreatureBody` (Species, SizeScale, WriteBoneWorld, EncapsulateBounds, Tick, Bounds); CreatureSim implements it unchanged. Bones: 8 arms × 24 + 6 soft + 2 eyes + 1 siphon = 201 (12.9 KB/instance).
New: OctopusBody (ICreatureBody), TentacleChain, TentacleAgent, SoftLattice, WrapMarch, BranchHints, OctopusBrain, IPreyTarget, OctopusMeshBuilder.
Species data: `bodyPlan {Spine, Cephalopod}` (default Spine), `CephalopodSpec`, `TentacleSpec` (segments, length, radii, taper, bend limit, tip curl, max stretch, wrap limits, speeds, suckers). CreatureWorld.Spawn dispatches on the plan; brain lives inside the body.

## 2. Simulation (flat arrays, fixed sub-steps, default 3 at 60 Hz)

2.1 TentacleChain: N = 24 particles + Verlet + per-segment twist; root x[0] kinematic on the web ring (lattice-driven). Modes Free / Pinned (contact point, normal, source). XPBD-lite, 3 iterations: distance (spacing·s, s ∈ [0.85, 1.35]), bend cone 28°/joint, rest curl toward ventral rising to the tip, soft muscle pull toward the agent's target shape, infinite-weight pins at contact + normal·radius, gravity + damping on free particles. FABRIK gives intent (target shape), PBD gives physics; reaching adds a travelling sinus. Rotation-minimising frames + twist (pinned: suckers to the surface; free: toward the body axis), ≤ 20°/segment. Bone scale 1/sqrt(s) × squeeze (0.92 wrapped, 1.05 bulge past the wrap).

2.2 TentacleAgent per arm reads the brain intent (Rest | Travel | Stalk | Strike | Retreat | Hold + urgency), a contact blackboard (anchors, tensions, support margin) and its own memory (≤ 4 grasp candidates). States: Curl/Idle → Feel (exploratory curl path in its own reach cone; tip tactile Cast per frame; hint-directed Cast every 0.25 s; only hits enter memory) → Reach (tip-led to its best memory point; miss → back to Feel) → Grip (thin branch: WrapMarch zips tip→base over 0.25–0.4 s; thick trunk: spread pins flat with suckers down) → Anchored/Pull (anchor toward intent → shorten; behind → lengthen, release candidate) → Release (peel base→tip; only if support margin stays ≥ 1 — local inhibition, like the gait-group rule) ; Strike (qualifying arms shoot straight to the predicted intercept in 0.12–0.2 s, s → 1.35) → Hold (wrap prey). Spacing from other arms' anchors is a local scoring term. Score: reach fit (0.35–0.9 L), progress, root line of sight, surface angle, graspability, hint confidence, freshness.

2.3 OctopusBody + SoftLattice: 14 particles (mantle 3 rings × 4 + head front/back) under gravity. Arm roots are barycentric points on the web ring; each chain's constraint impulse at x[0] is applied as force on the lattice. Shape matching (Müller 2005, linear) over 5 overlapping clusters (head, web, mantle base/mid/tip), β = 0.35, A normalised to det 1 (volume), stiffness head 0.6 → mantle tip 0.15 (trailing jiggle). Breathing 1 ± 3 % at 0.4 Hz, siphon pulse. Emergent: pendulum on 2 anchors, swing + stretch toward a hard pull then squash/overshoot, brachiation by releasing at the apex, falls with impact squash. Body collision: 2 lattice particles/frame round-robin probed outward and pushed out along the real normal. Orientation = head cluster R. Trunk: spread anchors drag the body up. Ground: agents anchor on terrain (crawl), climb back by feeling up the trunk.

2.4 WrapMarch on the real mesh: from the contact hit, 3 extra probes estimate the branch axis (normals of a tube ⟂ axis) and curvature radius; r is used only for the wrap-vs-spread decision (2π(r + armRadius) ≤ 0.6 × remaining arm). March segment by segment along the helix tangent (pitch 12°), each point snapped by `Probe` to the real bark; axis re-estimated every 4 pins; a miss ends the wrap (rest free). Pins in world space (static world; source-local pins later for SpaceGame movers). ~28 probes spread over the zip.

2.5 Prey: `IPreyTarget` (Position, Velocity, GrabVolume from the prey's own body, CanBeGrabbed, OnGrabbed, OnReleased). Adapters: CreaturePrey (spine joints + halfWidth; Struggle then Flee), PlayerPrey (CharacterController capsule). Hold re-solves a helix around the prey's own GrabVolume each frame. Events: Strike, Grabbed, Released. Lab default: hold 1.5 s, release, no damage.

## 3. Brain (intent only)

Perception: other species' sims + registered player, range 4 L, 270° cone, one LOS Cast per candidate every 0.2 s (canopy occludes), last-known position/velocity.
States: CanopyRest (3–5 anchored, colour drift, breathing) → Explore (Travel to a canopy region every 5–20 s) → Stalk (Travel to a hint branch 0.5–1.0 L above the prey's predicted path, preferably out of its view; low urgency; mottled camouflage + passing clouds; freeze + partial cloak 0.6 when the player faces it within 15°/12 m) → Ambush (0.25 s coil wind-up, then Strike; 2–4 agents qualify themselves, the rest hold) → Retreat (deimatic flash 0.3 s, cloak 1, Travel to the farthest high region at urgency 1, uncloak after 4–8 s calm); Fallen (Travel to the nearest climbable). Goals clipped to the enclosure. BranchHints: per prototype L-system skeleton segments cached in plant-local space (append-only `PlantScatter.GetSkeleton`), transformed by ClimbableFlora instance TRS.

## 4. Performance

Active ≤ 0.35 ms; resting ≤ 0.12 ms; ≤ 40 raycasts/frame (expect ~25); 0 extra draws; 0 GC/tick. Solver ~1.7k constraint evals (~0.12 ms Mono), pinned runs skipped; lattice ~0.01 ms; free-arm sweep round-robin (4 segment casts per free arm; hits become drape pins); distance LOD beyond 30 m / off screen (half rate, 2 iterations, no sweep). ClimbableFlora AABB includes strike reach (1.3 L).

## 5. Mesh and rendering

Arms: tapered tubes, 12 verts × 3 rings per segment, ventral flattening 1.0 × 0.85, pointed tip. Web skirt between arm bases (2-bone weights). Mantle/head ellipsoid shell on 6 soft bones; 2 eye bones (horizontal pupils); siphon. uv0 = (arc m, angle/2π), uv1 = (part id: 4 arm, 5 web, 6 mantle; dorsal coordinate).
Soft bones are affine (det 1): CreatureSkin.hlsl transforms normals by the cofactor matrix (identical for uniform bones; test that the monitor is unchanged).
Look: wet GGX 0.4 + clear coat 0.08; red-orange subsurface through thin arms and web; Voronoi chromatophores driven by per-instance `chroma`; passing-cloud bands; papillae via CreatureDisplace + normals; two staggered sucker rows with rim, cup, AO; counter-shading.
CreatureInstance grows 16 → 32 B (cloak, chroma, flash, cloudPhase), generic for all species.
Cloak (the queued feature, generic): Forward dither-dissolve by `cloak` with an edge glint; ShadowCaster/DepthOnly/DepthNormals ignore it — body gone, shadow and AO remain.

## 6. Tests

Tentacle_LengthsWithinStretch, Tentacle_BendCone, Tentacle_TwistPerSegment, Wrap_Cylinder_OnSurface, Wrap_ContactsComeFromProbe (non-cylindrical bent mesh), Wrap_AxisEstimate, Wrap_TooThick_Spreads, Wrap_EndsAtTwigTip, Agent_IndependentTargets, Agent_ReleaseKeepsSupport, Brachiate_TwoBars_Crosses, Body_DrivenByChains (limp → free fall; one anchor → pendulum period within 25 %), Body_VolumePreserved, Body_NoPenetration, FreeArm_NoPassThrough, Fall_LandsAndReturns, Strike_ReachesStillPrey, Strike_Miss_Retreats, Hold_FollowsMovingPrey, Perception_LoS_Occluded, Stalk_FreezesWhenWatched, Hints_Optional_ProbeOnly, Containment_Octopus_60s, Mesh_Octopus_Builds, Mesh_WrappedPose_NoInvertedTris, Skin_Cofactor_MonitorUnchanged, Renderer_Bounds_ContainArms, Perf_OctopusActive/_Resting/_Queries, Octopus_NoAlloc (positive control, R28), Octopus_Deterministic; shader Cloak_ShadowRemains, ShaderHasError false.

## 7. Editor verification

Verify the instance; CreatureLab in play mode: resting wrapped (sucker close-up), brachiation sequence (reach, zip, swing apex, squash), feeling arm with F3, trunk spread climb, stalking with passing clouds, freeze + partial cloak, strike (3 frames), hold/release, cloaked retreat (shadow only), fallen + crawl. Read back ms resting/active, raycasts/frame, pool/bake counts. Full EditMode suite green.

## 8. Phased plan ([A] can start before climbing lands; [B] needs PhysicsSurfaceProbe)

1. [A] ICreatureBody refactor of renderer + world (no behaviour change; rebase onto climbing's world edits).
2. [A] TentacleSpec + TentacleChain (PBD, FABRIK targets, frames, twist) + Tentacle_* tests; optional numpy/Manim prototype.
3. [A] SoftLattice + OctopusBody with limp arms; Body_* tests.
4. [A] OctopusMeshBuilder + cofactor normals + Mesh_* tests; static lab pose screenshots.
5. [A] Octopus look shader + dynamic instance data + cloak; Editor shader gate.
6. [B] WrapMarch + Wrap_* tests on real MeshColliders.
7. [B] TentacleAgent states + blackboard + Agent_*/Brachiate_* tests.
8. [B] BranchHints (+ PlantScatter.GetSkeleton) + Hints_Optional.
9. [A logic] IPreyTarget + adapters + OctopusBrain + Strike/Hold/Perception/Stalk tests.
10. [B] Lab enclosure (Baobab 2.0 + second tree, prey), fall/ground path, perf + LOD, Editor verification.

## 9. Risks

LBS at tight wraps (fallback: curve skinning behind a keyword); Mono solver and physics query cost unmeasured; PBD stability at strike speeds and pendulum energy gain; open L-system tube ends and faceted normals bias the axis estimate; static-world pins (SpaceGame movers later); emergent motion may look aimless (tune via scoring and gains); shared-file churn with climbing and species work (sequence after climbing, keep edits additive); the thick Baobab may offer few wrappable branches.

## 10. User decisions

(Recorded in the ledger once answered.)

User decisions, 2026-10-17:
1. Prey: the player plus one small lab creature (beetle or snake from the species work) in the octopus enclosure. A grab holds 1.5 s, releases, fires events; no damage; the prey struggles, then flees.
2. Trees: LOTS of trees in the octopus enclosure (a grove of climbable trees with overlapping canopies), not just a second one.
3. Size: fit to branches (arms ~1.6 m at scale 1; lab scale chosen so mid branches take ≥ 1.2 wrap turns).
4. Cloak: generic shader feature shipped with the octopus; the monitor's threat trigger is a later small task.

User refinement, 2026-10-18 (updates decision 2 and the octopus's behaviour):
5. Arm roles: each arm still controls itself (its own chain, target search, contact, wrap, release, safety rule), but the OCTOPUS decides what each arm is used for and sends commands: e.g. Grip toward the route it wants to go (a few arms), Feel around, Hang down, Groom itself, Strike, Hold/Anchor, Tuck. Roles are assigned from intent, support needs and arm position, with hysteresis/minimum hold; the arm executes its role on its own and can report failure for reassignment. Idle variety at rest (some hold, some hang, 1–2 groom or feel).
6. The octopus should WANT to swing between branches: brachiation is its preferred locomotion and a frequent idle behaviour.
7. Size: 4× its previous lab size, via the existing species.scale pipeline (per-individual size variation must look and behave right).
