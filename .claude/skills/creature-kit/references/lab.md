# The Creature Lab

The lab's animals are `Config/Creatures/CreatureLabRoster.asset` (`CreatureLabRoster`, kit T3.5): one entry
per enclosure, in arc order, each `{species, scaleOverride, count, rocks}` (0 = the species' own `scale`; `count` 0/1 =
one individual, a group gets consecutive seeds `seed + slot + 1000 + i` spread round a ring; `rocks` = sandstone
boulders in the enclosure, walked round - RockCrab: 5 crabs, 6 rocks). `CreatureLab`
reads it (its `species` / `scaleOverrides` arrays are filled from the roster) and places enclosures and
aviaries; `OctopusLab` takes the first Grove species. No per-type code: the habitat comes from the species.

## Habitat from the modules (`CreatureKit.LabHabitat.For`)

| habitat | when | lab |
|---|---|---|
| Grove | a soft body, or the `Ambush` behaviour | `OctopusLab`: oak/tree grove, beetle prey |
| Aviary | it can fly (`Fly` + `Wing` parts + a cruise speed) | `AviarySizing` radius, roof; posts, trees, rock perches (`AviaryDressing`); `FlightBrain` |
| Climbable | `Climb` | enclosure whose shade tree (Baobab, `plantScale` 2.0) it may climb; `ClimbingBrain` |
| Plain | otherwise | enclosure with a shade tree it walks round; `WanderBrain` |

The brain follows the behaviour modules (`BrainFactory`): Wander / ClimbExcursion / FlightExcursion keep
the shipped brains; any other behaviour (e.g. `Flee`) gives a `ModularBrain` over all of them.

## Sizes

Enclosure radius `LabHabitat.EnclosureRadius(sp, maxScale, aviaryRadius)` = max(5 m, 2 body lengths x
maxScale), maxScale = `scale` x (1 + `look.sizeJitter`) (or the entry's override) - the largest individual.
Aviaries follow the flight (`AviarySizing`). Editing a species asset in play mode respawns it at its new size.

## Adding an animal: the LAST step of the new-animal workflow

Only after `creature_kit.py check <Species>` is green, its part tests pass and the catalogue is fresh:

1. Add one entry to `CreatureLabRoster.asset` (`species: {fileID: 11400000, guid: <the asset's .meta guid>,
   type: 2}`, `scaleOverride: 0`). Offline this is a YAML edit; the harness tests read it.
2. If the animal is new to `CreatureKitLabTests.Habitat_Resolves`' table, add its expected habitat there.
3. Offline: `creature_kit.py test CreatureKitLabTests` (`Roster_Loads_EveryEntryResolves`,
   `Lab_Placement_NeighboursNeverOverlap` with every entry, `Habitat_Resolves`;
   `Roster_ContainsEveryNonTestSpecies` warns about animals not yet listed).
4. Unity (one agent at a time): Marching Cubes > Rebuild Creature Lab. `CreatureLab.unity` is staged in the
   parent repo only with the user's go-ahead.
5. Hand-off note for the user (R32, no screenshots): where the enclosure is, the play-mode setup, what to
   look at per part, the 0.9x / 1.1x individuals side by side.
