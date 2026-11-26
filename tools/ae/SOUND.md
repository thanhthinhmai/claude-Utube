# The sound of an After Effects film (specs/037)

Sound effects are not written into a `mix.py` any more. After the Animatic is approved, Claude writes a **sound
plan** with commands, one cue per sound; the studio finds each sound in the library, times it from the shot's
keyframes and mixes `out/mix.wav`. When a shot's length changes at the Animatic, every time follows by itself.

## What to read first

- `SCRIPT.md`: what happens in each paragraph.
- `animatic/keys.json`: the motions of each shot, `{shot: [{layer, prop, t0, t1}]}` in seconds within the shot. A
  motion is named `Layer · Prop`, for example `Hand R · Rotation`.
- the style's `sound.sfx` (from `learn sfx`; read from the film's `kit/template.json` or `my-styles/<film.json → style>/template.json`): sounds per minute, gain against the
  voice, which actions get a sound, chosen silences, how sounds end at a cut. Follow its numbers. `actions` are sounds
  both classifiers heard in the style's videos; `hints` only one did, and are often wrong: use a hint only when the
  picture has that sound. Either way the picture decides what sounds: a sound the style uses but the shot does not
  show is left out. Without `sound.sfx` the defaults are 12 sounds a minute at most, −6 dB against the voice, point
  sounds fade at the cut, whole-shot sounds stop hard.

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
  `sound silence add --line l05 --word w` starts it when that word ends.
- Queries are short English words the way sound libraries name files: material + action (`glass shatter`,
  `sneaker step gym`, `crowd cheer small`, `paper scribble pencil`). `--cat` is a UCS category (GLASS, WATER,
  FOOTSTEPS, CROWDS, WHOOSHES, CARTOON, UI, PAPER…).
- A shot the user turned off (`sound shot off <film> S5`; `sound plan` shows `· sound off`) gets no sound effects:
  `cue add` there is refused (code 5). Leave it off unless the user turns it back on (`sound shot on`). Its old
  cues stay as `off` and come back when it is on. Voice, music and silences are not touched.
- Do not stack sounds closer than 0.2 s; the studio drops the extra ones ("too dense").
- `--gain` (dB against the voice) only when the style asks for it; `--cut hard|fade|over [--fade s]` when a sound must
  end differently at the cut (hard: stops dead on the cut, like a crowd cut off).

Then `sh bin/studio sound mix <film>` (prints `cues P placed · D dropped · M missing`) and `sound plan <film>` to
read what happened. A `missing` cue found nothing: try other words once; if it is still missing, leave it — the
studio never puts a made-up sound in its place. A `dropped` cue says why.

## Music

The film's own `mix.py` (if any) only makes the music: `out/music.wav`, 48 kHz stereo, the length of the film, no
voice and no effects. `sound mix` puts the voice, the music (ducked under the voice) and the effects together.
The music is not ducked or limited in `mix.py`: `sound mix` does that. It also sets one gain for the whole film
from the voice and the music (−14 LUFS, the studio's delivery check) and runs a true-peak limiter at −2.5 dB, so
the AAC copy stays under −1 dB. Do not normalise or limit again in `mix.py`.

### Moving an older film over (done for `ae-sleepless-test`, 2026-11-26)

1. Keep the old full mix: `cp mix.py mix.py.orig`, and copy `out/render.mp4`, `out/mix.wav`, `out/audio.m4a`,
   `<film>.mp4` and `CREDITS` into a backup folder (`sound mix` puts the new sound back on the rendered film).
2. Make `mix.py` music only: run `mix.py.orig` up to the end of the bed (before its ducking line), take the bed
   alone, write `out/music.wav`. Check by ear that no voice or effect is left in it.
3. Remove the effects from the old mix by not carrying them over: each one becomes a cue (`sound cue add`),
   anchored to the motion that makes it (`--motion "<layer> · <prop>"`), to a word, or to the shot.
4. `sound plan <film>`, then `sound mix <film>`; measure the film (`ffmpeg -af ebur128=peak=true`): −14 ± 1 LUFS,
   true peak ≤ −1 dB. Until the Animatic (035) writes `animatic/keys.json`, it is written by hand from the AE keys.

## Licences

Library sounds are Sonniss GDC (the studio owner's films only) or Freesound CC0. The mix writes one CREDITS line
per sound used. Never take a sound from a reference video or from anywhere else.
