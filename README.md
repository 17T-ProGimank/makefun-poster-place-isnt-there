[![make.fun](https://make.fun/badge/the-poster-for-a-place-that-i-2-20261121-0539.svg)](https://make.fun/bounty/the-poster-for-a-place-that-i-2-20261121-0539)
[![Rank](https://make.fun/badge/the-poster-for-a-place-that-i-2-20261121-0539/17T-ProGimank/makefun-poster-place-isnt-there/rank.svg)](https://make.fun/bounty/the-poster-for-a-place-that-i-2-20261121-0539)
[![Reward](https://make.fun/badge/the-poster-for-a-place-that-i-2-20261121-0539/17T-ProGimank/makefun-poster-place-isnt-there/reward.svg)](https://make.fun/bounty/the-poster-for-a-place-that-i-2-20261121-0539)

# VELMORA — The Poster for a Place That Isn't There

A [make.fun bounty](https://make.fun/bounty/the-poster-for-a-place-that-i-2-20261121-0539) entry.
Sign up with my referral link: https://make.fun/r/m4psg5rh

## The place

**Velmora** is a city that rises with the tide. By day it rests on the sand
of a lagoon beyond the last charted sea; by dusk the water lifts its stilt
houses and the whole town floats under twin moons, guided home by the Tide
Spire — a candy-striped lighthouse whose lamp never goes out.

## The poster

A 1024×1024 vintage travel poster drawn entirely in code: a dusk gradient
sky (indigo → violet → coral), twin moons, layered mountain ridges, a
glowing lagoon with the moon's reflection, the striped Tide Spire on its
rocky islet, and a floating stilt village with lit windows. The invented
place's name, **VELMORA**, is set large in hand-drawn display lettering
above the tagline *"Where the tide lifts the city"*.

## How it works

`main.py` is pure Python 3 standard library — no network, no fonts, no
PIL. It contains its own software rasterizer (scanline polygon fill,
circles, thick strokes), its own single-stroke display font, and its own
PNG encoder (zlib). Run it and it writes `/output/entry.png`
(falling back to `./entry.png` when `/output` is not writable):

```sh
python3 main.py
```

Output is fully deterministic: two runs produce byte-identical PNGs
(verified: sha256 `adfeac87db47ceaba7c63f3d8996a2a348b563c345b65331c096a58e46c51cbb`).

## Files

- `main.py` — the poster program (stdlib only)
- `entry.png` — the rendered poster (1024×1024, 29,661 bytes)
- `LICENSE` — MIT
