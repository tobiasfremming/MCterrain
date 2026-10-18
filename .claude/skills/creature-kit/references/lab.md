# The Creature Lab

> Kit in progress: `Config/Creatures/CreatureLabRoster.asset` and `Habitat.For` replace `kSpeciesPaths`
> and the per-type branches in T3.5. Today the lab is `CreatureLab` (spine species) plus `OctopusLab`.

## Habitat from the data

| habitat | today (legacy fields) | lab |
|---|---|---|
| Aviary | `CanFly` (wings + flight.cruiseSpeed) | `aviaryRadius` x max(1, maxScale), roof `aviaryHeight`; `FlightBrain`; rocks/trees (`AviaryDressing`) |
| Climbable | `climb.canClimb` | enclosure with the shade tree (Baobab, `plantScale`); `ClimbingBrain` |
| Grove | `bodyPlan = Cephalopod` | `OctopusLab`, oak/tree grove, beetle prey |
| Plain | otherwise | enclosure, `WanderBrain` |

`CreatureKitAssets.HabitatOf` encodes this; the kit's `Lab` check asserts the species fits it.

## Sizes

Enclosure radius `CreatureLab.EnclosureRadius(sp, maxScale)` = max(5 m, 2 body lengths x maxScale), where
maxScale = `scale` x (1 + `look.sizeJitter`) is the largest individual. Per-slot `scaleOverrides`. Editing
the asset in play mode respawns the species at its new size.

## Adding an animal (today)

Add the asset to the scene's `CreatureLab.species` (+ `scaleOverrides`) - an Editor step with the user's
go-ahead for the scene (`CreatureLab.unity` is staged in the parent repo only then). Phase 3: one roster
entry, last step of the new-animal loop.
