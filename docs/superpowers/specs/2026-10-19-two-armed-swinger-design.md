# Two-armed tree swinger: design

Status: approved for implementation by the user, 2026-10-19 ("time to start implementing").

## Intent (user's words and why)

"An octopus-like being with only 2 tentacles that it uses to grab branches, and a few small tentacles that it uses only for eating. The body should be quite smaller." Two purposes, both binding:
1. **Debug the tree octopus.** Eight arms are hard to understand; with two arms, weird behaviours show up clearly. So it must run on the SAME octopus code (body, tentacle chains, arm roles, branch-route planning), so that whatever is wrong with two arms points at the octopus.
2. **Be a new, interesting creature** in its own right.
It must be made soon.

## What it is (agreed in conversation)

- **Related to the octopus but a completely different species, and stranger looking** than the octopus — not a miniature octopus.
- **Two long arms** for moving, **a few short mouth tentacles** used only for eating.
- **Body much smaller** than the tree octopus.
- **Moves like a gibbon:** hand over hand under the branches — hangs from one arm while the other reaches, swings, catches, then lets go of the first. Never a spare hold, so grab/release timing must be right every time.
- **Hunts small things:** small spiders climbing the trees. It spots one, swings close along the branches, then **creeps the last bit and grabs it with the small mouth tentacles** (not the long arms).

## Constraints

- Do NOT build it with the creature kit yet (user: "not use the creature kit yet, if it's unfinished"). Use the octopus code path and species data directly.
- Same octopus code, generalised: arm count and arm roles from data; the short mouth tentacles are a second, non-locomotion tentacle set (feeding only). Changes to the octopus core must be generic (the 8-arm octopus keeps working; its tests stay green) and small, because another agent is fixing octopus test failures in parallel.
- Contact only on real geometry (same rule as the octopus/climbing); size via species.scale × per-individual jitter, √scale timing; zero GC per tick; the user does visual inspection (no agent screenshots).
- Its arm-role/route debug readout (F3 + Show Roles, like the octopus) must work, since debugging is a purpose.

## Builder's calls (marked as mine, not agreed with the user)

- Look: a strange silhouette — e.g. an elongated, slightly translucent sac-like body that hangs below its arms, eye stalks or a crest of eyes, two long ribbon-like or banded arms, and a ring of 4–6 short mouth tentacles around a beak. Exact look is the builder's call within "stranger than the octopus, clearly a relative".
- Two arms: gibbon brachiation as the default travel; a two-arm grip rule (release only when the other arm holds); swing pumping as the octopus has; resting = hang from one or both arms.
- Mouth tentacles: short chains with a "Feed" role only; they reach for prey within a short radius once the body has crept close (a slow final approach).
- Prey: small spiders that climb the trees. Our spiders can't climb yet, so give a small spider species climbing (ClimbSpec on arthropod legs, using the climbing API). If spider climbing proves too large for v1, ship with spiders walking along branch tops and say so.
- Lab: its own small grove (reuse the octopus grove placement) with the prey spiders on the trees.
- Name: working name "Swinger"; the user can rename it.

## Done when

It lives in the creature lab: swings hand over hand through its grove, creeps up on climbing spiders and eats them with its mouth tentacles; the 8-arm octopus still passes its tests; tests cover two-arm grip safety, brachiation progress, the feeding catch, size variation and no-GC.
