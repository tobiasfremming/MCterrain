# Pod tree — the reference implementation

Built from the Population Zero "red moss zone" concept: a short thick trunk
splits low into three to five heavy limbs that droop, then sweep up in long
crooked arcs, sprouting cream pods with red firework tufts along their rising
halves. Assets: `Assets/TerrainGen/Config/Flora/PodTreeGrammar.asset` and
`PodTreePlant.asset`. Eight seeds: 9.3..10.4 m tall, 7.6..14.7 m wide,
76..136 pods, 39k..69k triangles, all terminated.

The three passes it took, so the next plant skips them:

1. Generic fork tree (every branch forks, pods only at tips): read as a
   broadleaf. Rewritten as long arcs with laterals.
2. Smooth arcs from a short trunk: read as bent pipes, and a deep dip put
   limbs on the ground. Trunk raised, dip softened.
3. Kink on every segment, lumpy width, sharp bends one in four: matched.

## Grammar

```
#iterations: 27

#axiom: X

X -> /(rand(360)) !(rand(0.42,0.55)) F(rand(0.5,0.8)) &(rand(-15,15)) /(rand(360)) !(rand(0.4,0.6)) F(rand(0.4,0.7)) &(rand(-15,15)) /(rand(360)) !(rand(0.38,0.55)) F(rand(0.3,0.5)) Q(rand(3,5), 0.45)

// Q(n,w): one limb per step, spread around the trunk.
Q(n,w) : n > 0 -> [ /(rand(360)) &(rand(88,108)) L(rand(11,14), 0.45, w*0.8, rand(7,10), 0) ] /(90) Q(n-1, w)
Q(n,w) : n <= 0 -> $

// L(k,l,w,u,i): a limb. k segments left, u = rise per segment, i = segments
// grown. Every segment is a kink: uneven length, lumpy width, a pitch and a
// yaw of up to 22 degrees, a roll, then roll upright and rise by an uneven
// share of u. One segment in four bends sharply (20..40 degrees) in a random
// direction instead. From the third segment on a segment may sprout a
// lateral pod stem (S). When k passes 6 the limb forks in two.
L(k,l,w,u,i) : k > 6.5 : 0.75 -> !(w*rand(0.85,1.2)) F(l*rand(0.6,1.4)) &(rand(-22,22)) +(rand(-22,22)) /(rand(-40,40)) $ ^(u*rand(0.3,1.9)) S(i, w) L(k-1, l*0.97, w*0.95, u, i+1)
L(k,l,w,u,i) : k > 6.5 : 0.25 -> !(w*rand(0.9,1.25)) F(l*rand(0.5,0.9)) /(rand(360)) &(rand(20,40)) $ ^(u*rand(0.5,1.5)) S(i, w) L(k-1, l*0.97, w*0.95, u, i+1)
L(k,l,w,u,i) : k > 5.5 && k <= 6.5 -> !(w*rand(0.9,1.2)) F(l*rand(0.7,1.2)) $ ^(u) !(w*0.8) [ +(rand(20,45)) /(rand(-40,40)) &(rand(-15,15)) L(k-1, l*0.95, w*0.75, u*1.1, i+1) ] [ -(rand(20,45)) /(rand(-40,40)) &(rand(-15,15)) L(k-1, l*0.95, w*0.75, u*1.1, i+1) ]
L(k,l,w,u,i) : k > 0 && k <= 5.5 : 0.75 -> !(w*rand(0.85,1.2)) F(l*rand(0.6,1.4)) &(rand(-22,22)) +(rand(-22,22)) /(rand(-40,40)) $ ^(u*rand(0.3,1.9)) S(i, w) L(k-1, l*0.97, w*0.93, u, i+1)
L(k,l,w,u,i) : k > 0 && k <= 5.5 : 0.25 -> !(w*rand(0.9,1.25)) F(l*rand(0.5,0.9)) /(rand(360)) &(rand(20,40)) $ ^(u*rand(0.5,1.5)) S(i, w) L(k-1, l*0.97, w*0.93, u, i+1)
L(k,l,w,u,i) : k <= 0 -> !(w) F(l*0.5) P(w, rand(1.2,1.6), 8)

// S(i,w): a lateral pod stem, left or right of the limb, angled up; about
// three out of five segments get one.
S(i,w) : i >= 3 : 0.3 -> [ +(rand(35,60)) /(rand(-30,30)) ^(rand(10,30)) P(w*0.5, rand(1.1,1.5), 26) ]
S(i,w) : i >= 3 : 0.3 -> [ -(rand(35,60)) /(rand(-30,30)) ^(rand(10,30)) P(w*0.5, rand(1.1,1.5), 26) ]
S(i,w) : i >= 3 : 0.4 -> $
S(i,w) : i < 3 -> $

// P(w,z,r): the pod stem rises toward vertical in four steps of r degrees,
// then the pod: an orange neck, three cream capsules each bent a few degrees
// off the last and widening toward the top, a red ring, the eye, the tuft.
P(w,z,r) -> !(w) F(0.22) $ ^(r) F(0.22) $ ^(r) F(0.22) $ ^(r) F(0.22) $ ^(r) !(w*0.7) F(0.08) f(z*0.22) Q(z*0.45) f(z*0.2) &(rand(3,8)) O(z*0.55) f(z*0.25) &(rand(3,8)) O(z*0.6) f(z*0.28) &(rand(3,8)) V(z*0.5) f(z*0.24) R(z*0.3) f(z*0.06) D(z*0.09) $ T(3, z*0.5, 0.018)

// T(n,l,w): the tuft: four twigs around the axis, each pitched out, three
// levels deep; the last level is a needle card.
T(n,l,w) : n > 0 -> !(w) F(l) [ ^(rand(30,50)) T(n-1, l*0.72, w*0.6) ] [ /(90 + rand(-20,20)) ^(rand(30,50)) T(n-1, l*0.72, w*0.6) ] [ /(180 + rand(-20,20)) ^(rand(30,50)) T(n-1, l*0.72, w*0.6) ] [ /(270 + rand(-20,20)) ^(rand(30,50)) T(n-1, l*0.72, w*0.6) ]
T(n,l,w) : n <= 0 -> f(l*0.4) N(l*0.9)
```

Iteration arithmetic: X 1, Q up to 5 (one limb a step), L up to 14, P 1,
T 3 + 1 = 25; `#iterations: 27` for margin. `S` expands in parallel.

## Profile

Stem colour (0.74, 0.28, 0.20), initial width 0.5, min stem radius 0.006.

| symbol | shape | colour | scale | notes |
|---|---|---|---|---|
| Q | capsule | (0.95, 0.62, 0.40) | (0.3, 0.5, 0.3) | orange neck, `ALONG` |
| O | capsule | (0.97, 0.88, 0.62) | (0.3, 0.5, 0.3) | cream body, `ALONG`, used twice |
| V | capsule | (0.98, 0.90, 0.66) | (0.36, 0.5, 0.36) | wider top, `ALONG` |
| R | cylinder | (0.85, 0.18, 0.12) | (0.42, 0.06, 0.42) | red ring, `ALONG` |
| D | sphere | (0.85, 0.12, 0.10) | (1, 1, 1) | the eye, emission 0.4 |
| N | quad | (0.80, 0.14, 0.12) | (0.07, 1.0, 1) | needle card, `ALONG`; at 0.18 wide it read as confetti |

The pod cluster (`PodClusterGrammar`) reuses `pod_parts` unchanged on 5..9
low runners with a two-generation fork: same look, knee-high.
