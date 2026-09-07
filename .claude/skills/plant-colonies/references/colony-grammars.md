# The colony grammars in the world
Written 2026-09-07 by the session generator; the assets are `Config/Flora/*ColonyGrammar.asset` and the letter tables live on each Biome's flora list. Read the comment at the top of each grammar for the kinds it mixes.

## DolomiteBiome - `DolomiteColonyGrammar` (iterations 22)
colonyChance 0.45, coverScale 140, coverThreshold 0.05, coverSoftness 0.25

| letter | species | rarity | spacing |
|---|---|---|---|
| `a` | AnemonePlant | uncommon | 1.8 |
| `b` | BanyanPlant | rare | 4.0 |
| `c` | RedCoralShrubPlant | uncommon | 0.8 |
| `d` | FanTreePlant | uncommon | 4.0 |
| `k` | KrakenVinePlant | rare | 1.8 |
| `l` | LanternTreePlant | rare | 4.0 |
| `m` | MossCarpetPlant | common | 0.8 |
| `n` | NestedBloomPlant | uncommon | 1.8 |
| `r` | RedMossPlant | common | 0.8 |
| `t` | TendrilTreePlant | uncommon | 4.0 |
| `u` | CurtainTreePlant | rare | 4.0 |
| `v` | TremorReedPlant | rare | 1.8 |
| `x` | HorsetailPlant | common | 1.8 |
| `y` | DandelionPlant | uncommon | 1.8 |
| `O` | OakPlant | landmark | 40.0 |
| `P` | PodTreePlant | landmark | 40.0 |
| `Q` | PagodaTreePlant | landmark | 40.0 |
| `T` | TreePlant | uncommon | 4.0 |
| `U` | RedUmbrellaPlant | landmark | 40.0 |

```
// Dolomite colonies. Groves: a chain of three to five anchor trees eight to
// sixteen metres apart, each with moss, red moss and horsetails at its feet
// and three to five satellites (blooms, anemones, coral shrubs, a kraken
// vine, a dandelion) within eight metres. Veins: a long meandering runner of
// moss and small things. Reed beds: tremor reeds in a tight patch. Heroes:
// one landmark with two anchor trees, a coral shrub and a curtain tree kept
// well back. Thickets: a tight cluster of coral shrubs and anemones. Fewer
// colonies, each bigger: the space between them is the point.

#iterations: 22
#axiom: X

X -> +(rand(360)) f(rand(0,4)) K

K : 0.44 -> V(rand(3,5))
K : 0.22 -> W(rand(12,18), rand(1.5,3))
K : 0.04 -> H
K : 0.16 -> C(rand(6,10))
K : 0.08 -> R(rand(5,9))
K : 0.06 -> f(0)

// grove
V(n) : n > 0 -> A [ +(rand(360)) f(rand(2.5,4)) m(rand(0.8,1.3)) ] [ +(rand(360)) f(rand(3,5)) r(1) ] [ +(rand(360)) f(rand(3,6)) x(1) ] S(rand(3,5)) +(rand(-60,60)) f(rand(9,16)) V(n-1)
V(n) : n <= 0 -> A [ +(rand(360)) f(rand(2.5,4)) m(1) ] [ +(rand(360)) f(rand(3,6)) x(1) ]
A : 0.55 -> T(rand(0.9,1.3))
A : 0.25 -> t(rand(0.9,1.2))
A : 0.12 -> d(1)
A : 0.08 -> l(1)
S(n) : n > 0 -> [ +(rand(360)) f(rand(4,8)) B ] S(n-1)
S(n) : n <= 0 -> f(0)
B : 0.35 -> n(1)
B : 0.25 -> a(1)
B : 0.2 -> c(1)
B : 0.1 -> k(1)
B : 0.1 -> y(1)

// vein
W(n,l) : n > 0 -> +(rand(-45,45)) f(l) [ +(rand(-90,90)) f(rand(0,1.5)) M ] W(n-1, l)
W(n,l) : n <= 0 -> f(0)
M : 0.45 -> m(rand(0.7,1.2))
M : 0.3 -> r(1)
M : 0.15 -> x(1)
M : 0.1 -> a(0.8)

// reed bed
R(n) : n > 0 -> [ +(rand(360)) f(rand(1,4)) v(rand(0.8,1.2)) ] R(n-1)
R(n) : n <= 0 -> f(0)

// hero
H -> L [ +(rand(360)) f(rand(14,22)) A ] [ +(rand(360)) f(rand(14,22)) A ] [ +(rand(360)) f(rand(10,18)) c(1) ] [ +(rand(360)) f(rand(8,14)) u(1) ] [ +(rand(360)) f(rand(6,10)) b(1) ]
L : 0.35 -> O(1)
L : 0.30 -> P(1)
L : 0.20 -> Q(1)
L : 0.15 -> U(1)

// thicket
C(n) : n > 0 -> [ +(rand(360)) f(rand(1.5,5)) E ] C(n-1)
C(n) : n <= 0 -> f(0)
E : 0.5 -> c(rand(0.8,1.2))
E : 0.3 -> a(1)
E : 0.2 -> n(1)
```

## DesertBiome - `DesertColonyGrammar` (iterations 22)
colonyChance 0.3, coverScale 180, coverThreshold 0.08, coverSoftness 0.25

| letter | species | rarity | spacing |
|---|---|---|---|
| `e` | AloePlant | common | 1.8 |
| `i` | StriderPlant | rare | 1.8 |
| `j` | CagePlant | uncommon | 0.8 |
| `o` | BaobabPlant | rare | 4.0 |
| `p` | PlumePalmPlant | uncommon | 4.0 |
| `q` | PodClusterPlant | uncommon | 1.8 |
| `s` | SandCandlePlant | common | 1.8 |
| `w` | CorkscrewPlant | uncommon | 4.0 |
| `z` | StarSpirePlant | rare | 4.0 |
| `Z` | SailTreePlant | landmark | 40.0 |

```
// Desert colonies. Oases: three to five plume palms in a loose ring with
// aloes and sand candles around them. Dune lines: a long nearly straight
// run of sand candles and aloes, the way a crest catches seed. Pairs: two
// corkscrews close together with a cage or two. Lone giants: a baobab or
// strider with nothing within twelve metres but a star spire. Heroes: a
// sail tree with a pod-cluster patch at its foot. A third of plots grow
// nothing, and the biome seeds far fewer colonies than the others: the
// desert is mostly empty.

#iterations: 20
#axiom: X

X -> +(rand(360)) f(rand(0,4)) K

K : 0.22 -> R(rand(3,5))
K : 0.22 -> D(rand(12,18), rand(1.5,2.5))
K : 0.12 -> N
K : 0.10 -> J
K : 0.02 -> H
K : 0.32 -> f(0)

// oasis: palms in a ring, aloes and candles at the feet
R(n) : n > 0 -> [ +(360/4*n + rand(-30,30)) f(rand(3,7)) p(rand(0.9,1.2)) [ +(rand(360)) f(rand(2,4)) e(1) ] [ +(rand(360)) f(rand(2.5,5)) s(rand(0.8,1.3)) ] ] R(n-1)
R(n) : n <= 0 -> [ +(rand(360)) f(rand(1,3)) e(1) ]

// dune line
D(n,l) : n > 0 -> +(rand(-12,12)) f(l) [ +(rand(-90,90)) f(rand(0,1.2)) M ] D(n-1, l)
D(n,l) : n <= 0 -> f(0)
M : 0.6 -> s(rand(0.7,1.2))
M : 0.25 -> e(0.9)
M : 0.15 -> f(0)

// pairs
N -> w(1) +(rand(360)) f(rand(2.5,4)) w(rand(0.8,1.1)) [ +(rand(360)) f(rand(3,6)) j(1) ] [ +(rand(360)) f(rand(3,6)) j(1) ]

// lone giant
J : 0.55 -> o(1) [ +(rand(360)) f(rand(12,20)) z(1) ]
J : 0.45 -> i(1) [ +(rand(360)) f(rand(10,16)) q(1) ]

// hero
H -> Z(1) [ +(rand(360)) f(rand(10,14)) p(1) ] [ +(rand(360)) f(rand(6,10)) q(1) ] [ +(rand(360)) f(rand(6,10)) q(1) ]
```

## CanyonBiome - `CanyonColonyGrammar` (iterations 20)
colonyChance 0.42, coverScale 120, coverThreshold 0.08, coverSoftness 0.25

| letter | species | rarity | spacing |
|---|---|---|---|
| `b` | BramblePlant | uncommon | 1.8 |
| `d` | DragonPlant | uncommon | 4.0 |
| `h` | ThicketPlant | common | 1.8 |
| `k` | DeadFingersPlant | rare | 1.8 |
| `l` | LadderPlant | rare | 1.8 |
| `n` | AntlerCoralPlant | uncommon | 1.8 |
| `s` | SnareLilyPlant | rare | 1.8 |
| `t` | StiltTreePlant | uncommon | 4.0 |
| `Y` | BonsaiPlant | landmark | 40.0 |
| `Z` | RootCathedralPlant | landmark | 40.0 |

```
// Canyon colonies. Ledges: a dragon or stilt tree with thicket and brambles
// crowding its base and antler corals a little out. Hedges: a bramble and
// thicket run along a curve. Bone patches: dead fingers and snare lilies
// together in a tight group. Antler coral fans of three to five. Heroes: a
// bonsai on its own, or a root cathedral with thicket under it. Fewer
// colonies, each bigger.

#iterations: 18
#axiom: X

X -> +(rand(360)) f(rand(0,4)) K

K : 0.34 -> V(rand(2,4))
K : 0.24 -> W(rand(10,15), rand(1.5,2.5))
K : 0.16 -> P(rand(4,7))
K : 0.16 -> N(rand(3,5))
K : 0.02 -> H
K : 0.08 -> f(0)

// ledge
V(n) : n > 0 -> A [ +(rand(360)) f(rand(2,3.5)) h(1) ] [ +(rand(360)) f(rand(2,3.5)) h(1) ] [ +(rand(360)) f(rand(3,5)) b(1) ] [ +(rand(360)) f(rand(5,8)) n(1) ] +(rand(-70,70)) f(rand(10,16)) V(n-1)
V(n) : n <= 0 -> A [ +(rand(360)) f(rand(2,3.5)) h(1) ]
A : 0.55 -> d(rand(0.9,1.2))
A : 0.35 -> t(1)
A : 0.10 -> l(1)

// hedge
W(n,l) : n > 0 -> +(rand(-35,35)) f(l) [ +(rand(-90,90)) f(rand(0,1)) M ] W(n-1, l)
W(n,l) : n <= 0 -> f(0)
M : 0.55 -> h(rand(0.8,1.2))
M : 0.45 -> b(1)

// bone patch
P(n) : n > 0 -> [ +(rand(360)) f(rand(1,4)) E ] P(n-1)
P(n) : n <= 0 -> f(0)
E : 0.5 -> k(1)
E : 0.35 -> s(1)
E : 0.15 -> n(1)

// antler coral fan
N(n) : n > 0 -> [ +(360/5*n + rand(-20,20)) f(rand(1.5,4)) n(rand(0.8,1.2)) ] N(n-1)
N(n) : n <= 0 -> f(0)

// hero
H : 0.6 -> Y(1) [ +(rand(360)) f(rand(6,10)) n(1) ] [ +(rand(360)) f(rand(14,20)) A ]
H : 0.4 -> Z(1) [ +(rand(360)) f(rand(5,9)) h(1) ] [ +(rand(360)) f(rand(5,9)) h(1) ] [ +(rand(360)) f(rand(5,9)) b(1) ]
```

## FrostBiome - `FrostColonyGrammar` (iterations 22)
colonyChance 0.45, coverScale 140, coverThreshold 0.05, coverSoftness 0.25

| letter | species | rarity | spacing |
|---|---|---|---|
| `b` | BellowsPlant | uncommon | 1.8 |
| `c` | CoralFungusPlant | uncommon | 0.8 |
| `e` | FernPlant | common | 0.8 |
| `i` | WhiteCoralShrubPlant | uncommon | 0.8 |
| `m` | MistTreePlant | rare | 1.8 |
| `p` | PuffballPlant | common | 0.8 |
| `s` | SeaFanPlant | uncommon | 1.8 |
| `t` | FrondTowerPlant | rare | 1.8 |
| `w` | GlowPlant | common | 1.8 |
| `y` | CordycepsPlant | uncommon | 1.8 |
| `z` | CrozierPlant | common | 1.8 |
| `Q` | LatticeFanPlant | landmark | 40.0 |
| `Z` | ChanterellePlant | landmark | 40.0 |

```
// Frost colonies. Fairy rings: eight to twelve puffballs or coral fungi in a
// ring four to seven metres across, a glow plant at the centre. Fern beds:
// a meander of ferns and cordyceps. Coral banks: white coral shrubs and sea
// fans clustered. Mist stands: two or three mist trees with bellows below.
// Heroes: a lattice fan or chanterelle with a fairy ring around it. One plot
// in eight is bare snow.

#iterations: 20
#axiom: X

X -> +(rand(360)) f(rand(0,4)) K

K : 0.28 -> R(rand(8,12), rand(2,3.5))
K : 0.28 -> W(rand(12,18), rand(1.2,2.2))
K : 0.16 -> C(rand(6,10))
K : 0.13 -> N
K : 0.03 -> H
K : 0.12 -> f(0)

// fairy ring: n mushrooms round a circle of radius r, glow in the middle
R(n,r) -> [ w(1) ] O(n, n, r)
O(n,t,r) : n > 0 -> [ +(360/t*n + rand(-10,10)) f(r + rand(-0.4,0.4)) M ] O(n-1, t, r)
O(n,t,r) : n <= 0 -> f(0)
M : 0.6 -> p(rand(0.8,1.2))
M : 0.4 -> c(rand(0.8,1.2))

// fern bed
W(n,l) : n > 0 -> +(rand(-40,40)) f(l) [ +(rand(-90,90)) f(rand(0,1.2)) E ] W(n-1, l)
W(n,l) : n <= 0 -> f(0)
E : 0.45 -> e(rand(0.7,1.2))
E : 0.25 -> z(rand(0.8,1.2))
E : 0.2 -> y(1)
E : 0.1 -> w(0.9)

// coral bank
C(n) : n > 0 -> [ +(rand(360)) f(rand(1.5,4.5)) B ] C(n-1)
C(n) : n <= 0 -> f(0)
B : 0.6 -> i(rand(0.8,1.2))
B : 0.4 -> s(1)

// mist stand
N -> m(1) [ +(rand(360)) f(rand(5,8)) m(rand(0.8,1.1)) ] [ +(rand(360)) f(rand(5,8)) m(rand(0.8,1.1)) ] [ +(rand(360)) f(rand(2,4)) b(1) ] [ +(rand(360)) f(rand(2,4)) b(1) ] [ +(rand(360)) f(rand(6,10)) t(1) ]

// hero
H : 0.5 -> Q(1) R(rand(8,10), rand(5,7))
H : 0.5 -> Z(1) R(rand(8,10), rand(6,8))
```

## Everywhere - `WorldColonyGrammar` (iterations 8)

colonyChance 0.4; letter `h` = HerbPlant, spacing 1.8.

```
// Everywhere: sparse herb tufts, three to six a plot when a plot has any.
#iterations: 8
#axiom: X
X -> +(rand(360)) f(rand(0,6)) V(rand(3,6))
V(n) : n > 0 -> [ +(rand(360)) f(rand(2,8)) h(rand(0.7,1.2)) ] V(n-1)
V(n) : n <= 0 -> f(0)
```
