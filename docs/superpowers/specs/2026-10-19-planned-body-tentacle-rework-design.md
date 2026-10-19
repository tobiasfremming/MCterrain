# Tentacle creatures, planned body: rework design

Status: approved by the user 2026-10-19 ("yes, do the rework, start with the swinger"). Supersedes decision 3 of `2026-10-17-tree-octopus-design.md` ("body driven by the chains, no own path or animation").

## Why

After several fix rounds the swinger and the tree octopus still jitter and look aimless, and every rest-physics change reshuffles unrelated swing tests. Root cause is structural: the body's main motion is emergent from ~200 PBD particles pulling a soft lattice, with intent passing through four layers of timers (brain, ArmCoordinator, TentacleAgent, muscle target shape). The curvature muscle is not an energy gradient, so toned free arms flutter and a perched octopus never sleeps. The swinger (2 arms) shows the same symptoms, so the problem is in the core, not in 8-arm coordination.

## The new split

1. **Body main motion is planned.** A reduced-order model: the body is a rigid mass hanging on its hold(s) — a pendulum on one hold (rod length = gripping arm's span, may shorten/lengthen as the arm reels), a two-hold sling when both hold, ballistic flight between release and catch. Energy is controlled (pump toward a target amplitude, damping toward rest). Deterministic for a given seed.
2. **Locomotion sequencer (one layer).** For brachiation: pick next hold from the BranchRoute → swing up (pump) → release at the right phase → ballistic → catch (free arm reaches the predicted hold in time) → transfer. Rest, creep (stalk), strike are further steps of the same sequencer. Replaces the brain/coordinator/agent timer stack for locomotion; arms keep local autonomy (exact grip point, wrap, release safety).
3. **Soft lattice = secondary motion only.** Driven by the planned body's acceleration (jiggle, squash on catch, stretch at the bottom of a swing). It no longer carries load.
4. **Holding arms** are stretched between body root and the hold, wrap on real bark via WrapMarch/probes (unchanged contact rule: real geometry only).
5. **Free arms** are passive, damped follow-through (they drag behind the body, no tone fighting gravity), or play purposeful eased gestures (reach for a catch, curl, groom, strike) whose shape targets are blended in with ease-in/out — never a constant muscle pull.
6. **Rest = sleep.** A perched/hanging body settles under damping, then sleeps (body and free arms frozen until a new step starts).

## Keep

TentacleChain as the arm representation (particles, display chain + curve skin), WrapMarch, ISurfaceProbe contacts, BranchHints/BranchRoute, mesh builders and look, MouthFeeder/prey, species data, scale pipeline (√scale timing), debug view (F3, roles → now sequencer step + plan: next hold, predicted arc, release/catch points), zero GC per tick.

## Order

Swinger first (two arms = a gibbon), behind its own body path; the tree octopus keeps the old path until the user has looked at the swinger. Then port the octopus (more arms hold → multi-hold sling; extra free arms are passive/gestures).

## Done when (swinger)

Smooth hand-over-hand brachiation through the grove with clearly visible pendulum swings, no jitter; hangs still and sleeps at rest; free arm reaches the catch in one eased move; catches land on real bark; creeps and feeds as before. Tests: determinism, energy bounded, rest sleeps (body and arm motion below a small bound), brachiation progress along a route, catch success rate, size 0.9/1.1, no GC.
