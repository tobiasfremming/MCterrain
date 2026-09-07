# Calibration: numbers that worked and numbers that failed

All from the offline simulator (14×14 plots of 24 m, flat, seed 5150) on
2026-09-07, then adjusted. "Per plot" = placed plants / 196.

## Settings in the world

| biome | colonyChance | coverScale | coverThreshold | coverSoftness | per plot |
|---|---|---|---|---|---|
| Dolomite | 0.45 | 140 | 0.05 | 0.25 | 4.1 |
| Frost | 0.45 | 140 | 0.05 | 0.25 | 2.1 |
| Canyon | 0.42 | 120 | 0.08 | 0.25 | 1.9 |
| Desert | 0.30 | 180 | 0.08 | 0.25 | 0.6 |
| everywhere (herb) | 0.40 | (biome's) | | | 0.6 |

Spacings: trees 4 m, shrubs and fungi 1.8, ground cover 0.8, landmarks 40.

## What failed

| tried | result | fix |
|---|---|---|
| uniform scatter, 13–15 species per biome at common/uncommon presets | ~35 plants per plot, 680 draw calls, "way too random / cluttered" | colonies |
| hero kinds at 5–15 % of colonies | a landmark every ~100 m (Frost 11 in 336 m²) | 2–4 %, landmark spacing 40 m |
| landmark spacing 14 m | fairy rings of chanterelles touching | 40 m |
| spacing = larger of the pair | every moss/satellite within 4 m of a tree rejected (240 per grid); groves were bare trunks | smaller of the pair (72 per grid) |
| coverThreshold 0.35 on the desert | 6 plants in 196 plots | 0.08–0.12; the fbm is normalised by amplitude sum, typical values ±0.4 |
| coverThreshold 0.15–0.2 elsewhere | 67 % glade, colonies cut to fragments | 0.05–0.08 |
| colonyChance 0.65 with small colonies | many small clumps, little open ground | 0.45 with colonies twice the size |
| importing the plain assignment script from the simulator | it rewrote the biome assets without letters at import | module-level writes under `__main__` |
| species letter `G` / `F` | drawn as stems by the turtle | never `F G f g` |

## Densities of the first pass (colonyChance 0.65, threshold 0)

Dolomite 3.2, Canyon 2.0, Frost 2.3, Desert 1.5 per plot; ~45 % of
candidates lost to glades, ~15 % to spacing. The user asked for more room
and more clustering, which is where the settings above came from.
