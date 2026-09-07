# Limb and structure recipes

Rule fragments that worked in the flora lab, with the numbers. Symbols are
single characters; `F`, `G`, `f`, `g` are turtle DRAW commands and can never
be part symbols: a part named `G` is drawn as a stem segment sticking out
of wherever it was placed (it happened twice: glow-bush clubs, umbrella rim
balls). Rules named `G` are fine, they are rewritten away before the
turtle sees them. Parts are centred on their marker, so `f(half)` before a
part.

## Crooked limb (the baseline)

See `pod-tree.md`. Kink ±22° pitch and yaw, roll ±40°, `$ ^(u*rand(0.3,1.9))`,
one in four segments `/(rand(360)) &(rand(20,40))`, width ×rand(0.85,1.2),
length ×rand(0.6,1.4). Launch 88..108 from vertical, rise 7..10, 11..14
segments, fork once at `k` crossing 6.

## Smooth arc (when smooth is wanted: fronds, tentacles, stalks)

```
R(k,l) : k > 0 -> F(l) &(rand(4,8)) [ leaflets ] R(k-1, l*0.98)
```
Constant small pitch per segment = a droop (frond, palm). `$ ^(k)` per
segment = a lift toward the sky (dragon tree arms, corkscrew climb).

## Tightening coil (tendrils, croziers, tentacle tips)

```
C(k,l,a,w) : k > 0 -> !(w) F(l) &(a) [ leaflets ] C(k-1, l*0.93, a*1.06, w*0.95)
```
Angle grows 6% and length shrinks 7% a step: the curve tightens to a centre.
Or index-driven: `&(c + i*0.85)` over 24 segments (kraken vine).

## Arch over the top (cage plant)

```
A(k,l,w,u) : k > 0 : 0.75 -> !(w*rand(0.85,1.2)) F(l*rand(0.7,1.3)) ^(u*rand(0.7,1.3)) +(rand(-7,7)) A(k-1, l*0.98, w*0.96, u)
```
Launch out and down (`&(100..120)`), then pitch about the stalk's OWN left
axis every segment with no roll and no `$`: the curve stays in its launch
plane and passes over the top (u = 13..17 over 14 segments = 180..240
degrees). `$ ^(u)` always rotates toward the sky, so it can never make an
arch; the first cage stood up like a row of posts.

## Levelling a cap (umbrella, chanterelle)

`$ ^(u)` does NOT stop at vertical. `$` is a no-op once the heading is
vertical, and after the heading passes vertical `$` flips local up, so the
next `^` pitches back: `$ ^(45) $ ^(45) $ ^(45)` leaves a tilt anywhere up
to 45 degrees and the umbrella's top plates stood on edge. Level in small
steps with a counting rule, worst tilt = one step:

```
N(n) : n > 0 -> $ ^(5) N(n-1)
N(n) : n <= 0 -> $
...  !(w) F(l*0.3) N(16) C(rand(10,14))     // 16 steps = 80 degrees of range
```

Budget the steps into `#iterations`.

## Pointing at the ground (curtain cords, cathedral columns)

`$ &(90)` is relative to the limb heading, not the world: off a limb that
has swept up 45 degrees it points 45 degrees down and BACK toward the
trunk, and the curtain tree's cords fanned across the crown instead of
hanging. Same stepped rule, pitching down:

```
P(n) : n > 0 -> $ &(10) P(n-1)
P(n) : n <= 0 -> /(rand(360))
...  A(i,w) : i >= 1 : 0.35 -> [ P(15) D(rand(5,10), rand(0.4,0.6)) ]
```

15 steps of 10 degrees cover a limb pitched anywhere up to 60 degrees up.
Hanging things are card strips or cylinder parts placed with `f`, never
`!(0.03) F`.

## Launching a limb at a world elevation (bonsai)

Off a twisted or leaning trunk, `&(a)` gives an elevation that depends on
the trunk's tilt, so the same grammar throws one limb at the sky and the
next at the floor. Point down first, then level up a counted amount:

```
[ $ +(rand(360)) P(14) N(rand(14,20)) L(...) ]   // azimuth random, elevation -20..+10
```

`$ +(rand(360))` yaws round the vertical, `P(14)` points down, `N(n)` pitches
up 5n degrees and stops at vertical. The trunk's tilt drops out. Costs
P + N iterations per limb; budget them.

## Twisting trunk (bonsai)

Corkscrew = a yaw round the vertical of the same sign every segment, with
the pitch wandering and a pull back to vertical that grows with height:

```
T(k,l,w,y,i) : k > 0 -> !(w*rand(0.85,1.25)) F(l*rand(0.7,1.2)) $ +(y*rand(30,55)) &(rand(-12,28)) $ ^(rand(5,12) + i*0.8) T(k-1, l, w*0.90, y, i+1)
```

`y` is +1 or -1 drawn once per tree, launched leaning 25..35 degrees, one
segment in four a sharp kink (`/(rand(360)) &(rand(30,50))`), taper 10 % a
segment. Without the `$` before `+` the yaw is about the local up and the
spiral collapses into a wobble.

## Roots (stilt tree, banyan, strider, thicket)

The limb rule with the rise replaced by a pull toward the ground: `$ &(u)`
instead of `$ ^(u)`. Launch 100..150 from vertical, fork once, overshoot
the ground on purpose (a root that stops short floats; one that goes on is
buried). Aerial roots from limbs: hook `A(i,w)` drops `[ $ &(90) /(rand(360))
D(...) ]` on three in ten segments; nearly straight (`&(rand(-9,9))`),
`$ &(u)` pull, 14..20 segments. Budget the iterations from where they
start: the banyan's roots begin at the last limb segment, so they needed
twenty more iterations than the limbs.

## Rising helix (corkscrew)

```
H(k,w,a,e) : k > 0 -> !(w) F(0.35) $ &(e) +(a) &(-e) [ fins ] H(k-1, w*0.985, a, e)
```
Yaw about the WORLD vertical by conjugating with the elevation `e`
(pitch `&(90-e)` once at the start). Yawing about the turtle's own up gives a
tilted circle that never rises.

## Sympodial fork tree (dragon tree, glow bush, orb tree)

```
A(l,w,s,a) : l >= MIN : 0.7 -> F(l) $ ^(UP) !(w*TP) [ +(a+rand(-8,8)) /(rand(360)) A(l*s*rand(0.9,1.06), w*TP, s, a) ] [ -(a+rand(-8,8)) /(rand(360)) A(l*s*rand(0.9,1.06), w*TP, s, a) ]
A(l,w,s,a) : l >= MIN : 0.3 -> ... three-way ...
A(l,w,s,a) : l < MIN -> <tip>
```
`s` (shrink) and `a` (half-angle) drawn once per seed. Generations =
`log(MIN/l0)/log(s)`; tips ≈ 2.4^generations. Budget by MIN, not iterations.

## Gnarled fork tree (oak)

Each segment is two half-steps with a kink between, `/(rand(-45,45))
&(rand(-14,14))`; thick wood `$ ^(6)`, thin wood `$ &(10)` (droops) and
carries leaf clusters. Moss strands: a world-aligned quad (`alignToHeading`
off, offset (0,-0.5,0)) at 25% of thick nodes.

## Whorls and tiers (pagoda, horsetail, chime bells)

```
M(k,w) : k > 0 -> !(w) F(l) [ Y(t, t, k) ] /(137.5) M(k-1, w*0.9)
Y(n,t,k) : n > 0 -> [ /(360/t*n + rand(-8,8)) &(rand(80,100)) B(...) ] Y(n-1, t, k)
```
`Y` sheds one branch per iteration, so it needs `t` iterations; count it.
Lower tiers longer: pass `k` (counting down) into the branch length.

## Laterals along a limb

`S(i,w)` hook with age guard `i >= 3`, two side rules at 0.3 each, a 0.4
"nothing" rule. Whatever sprouts re-finds vertical itself:
`F $ ^(r)` × 4 with `r` 26 for laterals, 8 for limb ends.

## Colour gradient along twigs (coral shrub)

Base wood as `F`, then generations drawn as coloured cylinder parts:
```
A(l,..) : l < M1 && l >= M2 -> f(l*0.5) Z(l) f(l*0.5) [ forks ]
A(l,..) : l < M2 && l >= M3 -> f(l*0.5) Y(l) f(l*0.5) [ forks ]
A(l,..) : l < M3 -> f(l*0.4) Y(l*0.8) f(l*0.4) K(0.025)
```
Cylinder scale x = 0.08, `ALONG`, size from the parameter. Two profiles on
the same grammar gave the red-to-yellow and white-to-lilac shrubs.

## Recursive same-rule structures

- **Levels**: `S(k,w,v)` with `v` counting down; the cap rule spawns
  `S(.., c*0.06, v-1)` children (fractal shroom), the bloom rule spawns
  `B(v-1, s*0.5)` at petal tips (nested bloom). Three levels is plenty.
- **Bipinnate**: rachis → `P(m,l)` pinnae → pinnule cards (frond tower).
- **Tuft**: `T(n,l,w)` four-way, three levels, last level a needle card.

## Placing parts on surfaces

- On a cone from its apex: pitch to `180 - atan(r/h)` degrees from up, then
  `f` a random fraction of the slant length. Pitching to the slope measured
  from the base sends parts into the air.
- On a flattened dome (sphere scaled (1, 0.4, 1)): walk out `r` of the
  radius horizontally, then up `0.4*c*(1 - 0.8*r*r)`.
- Hanging bell: funnel `AGAINST`, `f(0.5*s)` first so the apex sits on the
  stalk tip.

## Numbers that failed

| what | why |
|---|---|
| launch 95..125 from a 1.2 m trunk | limbs on the ground before rising |
| polyp cubes sized `w*0.9` | 30 cm blocks on the trunk; size from thin wood: `0.025 + w*0.12` |
| sphere at every coral tip | 54k triangles for a shrub |
| needle quads 0.18 wide | confetti; 0.07 |
| cap cone scale.y 0.14 | a plate; 0.3 |
| `&(rand(0,140))` spikes | 1.9 m underground; cap at 100 |
| `^(a)` yaw after `$` for a helix | tilted circle, 2.5 m instead of 9 |
| `$ ^(u)` for an arch that must pass over the top | posts: it only ever pitches toward the sky; pitch in-plane without `$` |
| `$ ^(45) $ ^(45) $ ^(45)` to level a cap | plates on edge: overshoots and oscillates; use the 5-degree `N(n)` leveller |
| `$ &(90)` to hang a cord off a limb | cords point back at the trunk: it is relative to the limb heading; use the 10-degree `P(n)` pointer |
| aerial roots budgeted from iteration 0 | not terminated, stray `D` markers; count from where the hook fires |
| a part symbol `G` (rim balls) | drawn as sticks: `G` is a draw command; rename the part |
| a thin strand as `!(0.03) F(...)` off a thick limb | the stem tapers from limb width to 0.03 in one segment: a big dark cone; use a thin cylinder part |
