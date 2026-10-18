# Plan: octopus arm roles and swinging (2026-10-18)

Status: plan. Start only after the jitter, cloak and 4× size fixes land on `feat/creature-octopus`; rebase onto them first.
Spec: `docs/superpowers/specs/2026-10-17-tree-octopus-design.md` §2.2, §3 and user decisions 5–7. Skill: `creature-module`. Code: `Assets/TerrainGen/Scripts/Creatures/Octopus/`.
Workflow (R32): develop offline in the .NET harness (session scratchpad `octopus_proto/octo_tests`, `dotnet bin_out/TerrainGen.Tests.dll <filter>`), compile gates, Unity tests once per finished feature, no screenshots, each task ends with a "what to look at" note for the user. New `.cs` files get `.meta` at the next Editor refresh — commit them.

## Design

A new **ArmCoordinator** (owned by `OctopusController`, ticked after `Brain.Tick`) turns `OctoIntent` into one **ArmCommand** per arm on the blackboard, deciding at ~4 Hz × 1/TimeScale with hysteresis, minimum hold time and a rate limit. `TentacleAgent` keeps its autonomy (target search, `BestCandidate`, WrapMarch, `CanRelease`, drape, contact); its command only changes what it is for (cone axis, may grip, may let go, tone, curl, groom path). It reports back Busy/Done/Failed.
Swinging: a pure **SwingPhase** estimator (pendulum of the body COM about the anchor centroid), **grip groups** (2–3 arms act as one hand), release at the forward apex, and length-target pumping on the anchored arms. The body is still moved only by chain tension and gravity (decision 3).

## Mapping onto the code

- `OctopusTypes.cs`: `enum ArmRole { Rest, Anchor, Grip, Feel, Hang, Groom, Tuck, Strike }`; `struct ArmCommand { role, dir, point, groomArm (-1 = mantle), group, urgency, swing }`; `enum ArmReport { None, Busy, Done, Failed }`; `OctoIntent` gains `swing, swingDir, routeNext`.
- `ArmBlackboard.cs`: `Command[]`, `Role[]`, `Report[]`, `RoleSince[]`, `Group[]`, `CommittedSupport` (counted in `Recount()`); `CanRelease` unchanged.
- New `ArmCoordinator.cs`: assignment, hysteresis, failure cool-downs, idle schedule, SwingPhase.
- `OctopusController.Tick`: `Brain?.Tick → Coordinator.Tick → agents`; `RestAnchors` moves into the coordinator; with no brain the coordinator runs on `c.Intent`.
- `TentacleAgent`: reads `board.Command[Index]`; Strike only on role Strike (else report Failed); `ConeAxis` blends toward `cmd.dir` for Grip/Feel; `TickCurl` executes Rest/Tuck/Hang; `TickFeel` grips under Feel only if `cmd.allowGrip`; `TickAnchored` takes `wantsRelease` from the role (Anchor never lets go except on swing-release; role change away from Anchor/Grip releases only while `CanRelease`); new `State.Groom` + `TickGroom`; `BestCandidate` gets a swing term.
- `TentacleChain` untouched (Tuck uses `SetTargetShape`).
- `OctopusBrain`: `State.Play` (idle swinging), `PlanSwingRoute` (hints), sets `intent.swing`.
- `OctopusLab`: role readout (T5).

## Tasks (thresholds × SizeScale, times × TimeScale; tests also at scale 4 and 0.9/1.1)

T0 Baseline + scaffolding: rebase; record crossing time, query average/peak, active/resting µs, rest worst mm. Test surfaces `GapBars(gap)`, `Grove(n)`; helpers `RoleTimeline`, `SwingCounter`. No production change.
T1 Data only: types + blackboard; default command = Grip toward intent, Anchor while anchored (today's behaviour). Test `Roles_DefaultsPreserveBehaviour` (existing brachiate/support/strike/determinism green, crossing ±15 %).
T2 Coordinator assignment (pure): quotas per mode (Travel grip 3–4, feel 1–2, rest hang/tuck; Rest anchors + idle slots; Stalk grip 2 slow, others tuck; Retreat grip 4–5; Strike strikers + anchors; Hold); order Strike → Support (≥ MinAnchors + 1 reserve) → Grip by facing the route → Feel far side → Hang lowest roots → Groom/Tuck/Rest; stick 0.25 for the current role. Tests `Roles_FacingRoute_Grip`, `Roles_SupportNeverBelowMin` (10 000 snapshots), `Roles_StrikeNearest`, `Roles_Deterministic`.
T3 Hysteresis: change only after MinHold (1.5 s·ts) and a score gain > 0.25, or pre-empt (Strike, support emergency, Failed); ≤ 2 changes per tick; Failed → 3 s cool-down for that role. Tests `Roles_NoFlipFlop` (≤ 3 changes/min/arm; RED with stick 0), `Roles_PreemptWithinTick`, `Roles_FailureReassigns`.
T4 Agents execute roles (Grip, Anchor, Feel without committing, Hang tone 0.25 drape, Tuck under-mantle shape, Rest curl; reports). Tests `Hang_TipBelowRoot`, `Tuck_Compact`, `Feel_DoesNotGrip_WhenSupported`, `Agent_GripFailsInVoid_Reports`; existing tests green.
T5 Lab readout: `OctopusLab.showRoles` OnGUI box (roles/states, swing count, role changes per minute), optional `logRoles`; no per-frame allocation. User looks at: arms facing the route grip, far side feels/hangs, no flicker.
T6 Groom + idle variety: analytic stroke paths over the mantle shell or a neighbouring arm (no queries), 2–4 strokes, suckers roll; seeded rest schedule re-rolled every 8–20 s with ≥ 6 s quiet windows for sleep. Tests `Groom_TipOnMantle_NoPenetration`, `Groom_ArmPair_NoCrossing`, `Roles_RestVariety`, `Rest_SleepsBetweenBursts`. User looks at: resting in the oak, 1–2 arms grooming, calm body.
T7 SwingPhase estimator (pure). Test `SwingPhase_ApexOnPendulum`.
T8 Grip groups, swing-scored grips (`+ wSwing·ahead + 0.3·level`), rear release at the forward apex once the front group has caught (each rear arm still through `CanRelease`); no ballistic flight (later opt-in `allowFlight`). Tests `Swing_ReleaseAtApex`, `Brachiate_TwoBars_Crosses` (≤ baseline), `Swing_GapBars_Crosses` (1.5 L gap, stretch alone can't reach).
T9 Pumping: anchored arms `LengthTarget = 1 − a·cos(2φ)` (a 0.08 below target amplitude), cap 50°, extra damping above 55°. Tests `Swing_PumpGrows`, `Swing_EnergyBounded`, `Swing_ChainsDriveBody`.
T10 Swing routes: `PlanSwingRoute` up to 3 hint waypoints 0.7–1.4 L apart, preferring another branch/tree, one LOS cast each; probe-only fallback. Tests `Route_PrefersCrossBranch`, `Explore_SwingsInGrove`, `Hints_Optional_ProbeOnly`.
T11 Swinging for its own sake: `State.Play` after 20–60 s rest; not while stalking/watched. Tests `Swing_IdleFrequent`, `Swing_NotWhileStalking`.
T12 Unity pass + hand-off: octopus filters, perf, full suite; Mono Stopwatch table vs T0; metas; parent bump; note for the user.

## Perf

Today ~4× over budget on Mono (active 1.1–1.8 ms; resting 0.42 ms, never sleeps); must not get worse. Coordinator ~2–5 µs, no queries, no allocation; SwingPhase negligible; pumping no queries. Queries should drop 20–30 % (only Grip/Feel arms explore; Hang/Tuck/Rest skip casts; Groom analytic); assert peak ≤ 40, average ≤ baseline. Idle activity in bursts so the body sleeps. Cheap options: 2 solver iterations for Hang/Tuck/Rest arms, skip twist for Tuck, half-rate coordinator under far LOD. `Octopus_NoAlloc` covers coordinator and groom.

## Risks

Role churn as jitter (stick, MinHold, rate limit, RED-checked test); support starvation (support filled first, `CanRelease` local); PBD energy gain under pumping (cap, damping, test); apex catch too strict (fallback: release on catch); groom without self-collision may read as hovering (user judges); thick 4× oak limbs mean spread grips (swing scoring must not need wraps); √4 timing (≈2.8 s swing period on a 3.2 m arm — don't tune faster than physics); shared files with the jitter work (leave `TentacleChain` and contact code alone; rebase before T1).

## What the user looks at

T1 nothing; T5 the role box during travel; T6 rest variety and grooming with a calm body; T8–T9 swinging between two limbs (rear arms let go at the far end, the swing builds, squash at the catch); T10–T11 crossing between oaks by swinging and unprompted swings after long rests.
