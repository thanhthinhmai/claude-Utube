# Making a film for Film Studio (online job)

This is the whole guide for an online film job. Do **not** read the studio's `CLAUDE.md`, `specs/`, `tools/`,
`tests/` or `.claude/`: they are about building the studio, not about films, and everything you read stays in
your context for the rest of the job.

## Where things are

- `LIB` = the film library (path in your instructions). Run its tools from `LIB`; never edit anything in it.
- Your project folder is your working directory. The film goes in `films/<name>/` (the name is given).
- The customer's own styles are in `my-styles/<slug>/`; library styles in `LIB/styles/<slug>/`.
- Everything is installed (core, voice, music). Do not run `setup`, `deps` or any installer.

## How to make the film (the library's workflow, skill mode)

Read in this order, and only these, when you reach them:

1. `LIB/styles/<slug>/STYLE.md` in full (or `my-styles/<slug>/STYLE.md`): the style's fixed rules.
2. `LIB/AGENTS.md`, sections **Style and story** and **Workflow** only. Skip the brief: never ask the
   customer anything you can decide yourself (questions are limited; see your instructions).
3. `LIB/DIRECTOR.md` §4 (treatment), then write `TREATMENT.md`. Later §5 (look) before the style frames and
   §11 (before you deliver) before the self-check. Other sections only when a decision needs them.
4. Only after `TREATMENT.md` exists: `LIB/styles/<slug>/DEMO.md`, to learn techniques. In `demo/`, read the
   files you will reuse; for the rest look with `grep -n` or `sed -n 'a,bp'`, not whole files.
5. `LIB/TECHNIQUE.md` §2–§8 as you build (picture, timeline, voice, music, mix, subtitles, review loop);
   §9 for 3D, §10 for characters. `LIB/core/README.md` for tool flags, when you need them.

Report each stage with `job step` before you start it, using exactly these names:
`Treatment`, `Look`, `Voice`, `Music`, `Picture`, `Mix`, `Render`, `Self-check` (no Storyboard online).

## Spend less (every token you read is paid again on every later turn)

- **Plan, then write.** Fix the timeline (`timeline.json` or the like) once, then write each code file whole
  in one `Write`. Prefer one larger edit to many small ones. Do not `Read` a file you just wrote.
- **Keep command output short.** Pipe long output through `tail -n 20` (or `grep` for what you need).
  Wrap renders and other long commands in `job run <id> --step <stage> -- …`: online it prints only the last
  20 lines when the command ends (the job log keeps more).
- **Look at pictures small.** Check frames as one contact sheet at most **1280 px wide** with at most 9 tiles
  (`ffmpeg … -vf "fps=…,scale=420:-1,tile=3x3"`), or a crop of the one detail you need. Never `Read` a
  full-size frame or a sheet wider than 1280 px. Look again only after a change.
- **Render once you are sure.** Test with a few frames or a short range before the full render; a full render
  plus a re-render is the most expensive loop.
- Do not explore: no `ls -R`, no reading files "to see what is there".

## Finishing

- Self-check against DIRECTOR.md §11 with one contact sheet and the loudness check, then
  `job done <id> --film <name>`. The studio checks loudness (−14 ± 1 LUFS, true peak ≤ −1 dB) and reading time
  again before delivery.
- If the film cannot be made, `job fail` as your instructions say.
