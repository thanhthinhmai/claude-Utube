# The sound of an After Effects film (specs/037)

Sound effects are not written into a `mix.py` any more. After the Animatic is approved, Claude writes a **sound
plan** with commands, one cue per sound; the studio finds each sound in the library, times it from the shot's
keyframes and mixes `out/mix.wav`. When a shot's length changes at the Animatic, every time follows by itself.

## What to read first

- `SCRIPT.md`: what happens in each paragraph.
- `animatic/keys.json`: the motions of each shot, `{shot: [{layer, prop, t0, t1}]}` in seconds within the shot. A
  motion is named `Layer · Prop`, for example `Hand R · Rotation`.
- the style's `sound.sfx` (from `learn sfx`; read from the film's `kit/template.json` or `my-styles/<film.json → style>/template.json`): sounds per minute, gain against the
  voice, which actions get a sound, chosen silences, how sounds end at a cut. Follow it. Without it the defaults are
  12 sounds a minute at most, −6 dB against the voice, point sounds fade at the cut, whole-shot sounds stop hard.

## One cue per sound

```sh
sh bin/studio sound cue add <film> S2 --action "window breaks" --query "glass window shatter" --cat GLASS \
   --motion "Window · Scale" [--edge start|end] [--offset-f 2]
sh bin/studio sound cue add <film> S1 --action "eyes pop open" --query "cartoon pop" --line l01 --word window
sh bin/studio sound cue add <film> S5 --action "a beat later" --query "watch ding" --at 0.6     # share of the shot
sh bin/studio sound cue add <film> S3 --action "office fish tank" --query "aquarium bubbles loop" --cat WATER --span
sh bin/studio sound silence add <film> S4 --line l05 --word silent --len 0.6 --db -57
```

- Every named motion worth hearing gets one cue anchored to it (`--motion`). A hit, a pop, a swoosh lands on the
  motion's start; a landing or a stop on its end (`--edge end`).
- `--line/--word` for a sound tied to what the narrator says ("the window breaks"); `--at` only when no motion or
  word fits; `--span` for a background that lasts the whole shot (it stops at the cut).
- A chosen silence is a moment where everything drops away (the narrator says "…goes silent"); the voice stays.
- Queries are short English words the way sound libraries name files: material + action (`glass shatter`,
  `sneaker step gym`, `crowd cheer small`, `paper scribble pencil`). `--cat` is a UCS category (GLASS, WATER,
  FOOTSTEPS, CROWDS, WHOOSHES, CARTOON, UI, PAPER…).
- Do not stack sounds closer than 0.2 s; the studio drops the extra ones ("too dense").
- `--gain` (dB against the voice) only when the style asks for it; `--cut hard|fade|over [--fade s]` when a sound must
  end differently at the cut (hard: stops dead on the cut, like a crowd cut off).

Then `sh bin/studio sound mix <film>` (prints `cues P placed · D dropped · M missing`) and `sound plan <film>` to
read what happened. A `missing` cue found nothing: try other words once; if it is still missing, leave it — the
studio never puts a made-up sound in its place. A `dropped` cue says why.

## Music

The film's own `mix.py` (if any) only makes the music: `out/music.wav`, 48 kHz stereo, the length of the film, no
voice and no effects. `sound mix` puts the voice, the music (ducked under the voice) and the effects together.

## Licences

Library sounds are Sonniss GDC (the studio owner's films only) or Freesound CC0. The mix writes one CREDITS line
per sound used. Never take a sound from a reference video or from anywhere else.
