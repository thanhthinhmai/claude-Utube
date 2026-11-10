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
5. Right after `TREATMENT.md`: the **Script** step below. Write no voice line before the script passes.
6. `LIB/TECHNIQUE.md` §2–§8 as you build (picture, timeline, voice, music, mix, subtitles, review loop);
   §9 for 3D, §10 for characters. `LIB/core/README.md` for tool flags, when you need them.

Report each stage with `job step` before you start it, using exactly these names:
`Treatment`, `Script`, `Look`, `Voice`, `Music`, `Picture`, `Mix`, `Render`, `Self-check` (no Storyboard online).

## The Script step (every film with narration)

`STUDIO` = the studio folder in your instructions. Lines starting with `>` in SCRIPT.md are notes, not narration.

1. Write `films/<name>/SCRIPT.md`: `Title:`, `Target: <seconds>s`, `Language:` lines, then paragraphs `[P01] …`,
   `[P02] …`. Short sentences (at most 25 words), a hook in the first 30 seconds (a question, a number or a twist),
   no greeting, numbers written the way they are read ("four forty-five", not "4:45"), few brackets or dashes.
2. Write `films/<name>/SOURCES.md`: one line per fact or number, `- [Pnn] "quote": source name, year, link`.
   Find facts with WebSearch (at most 5 searches) and open every link you cite with
   `sh STUDIO/bin/studio web fetch <url> --film <name>`. An invented detail of a story: `- [Pnn] "quote": fiction`.
   No facts at all: the single line `no factual claims`.
3. `sh STUDIO/bin/studio script check <name>` until it exits 0. Then `sh STUDIO/bin/studio script review <name>`:
   - exit 0: the script passed; go on.
   - exit 1: change **only** the paragraphs the editor marked P1 or P2 (others must stay word for word), then run
     `script review` again.
   - exit 3: the script did not pass after 2 fix rounds. Stop: `job fail <id> "<the last score and problems>" --by studio`.
4. A film with no narration at all (music and picture only): `sh STUDIO/bin/studio script skip <name> --reason "no narration"`.
5. The voice lines (`lines.json`) are exactly the passed script's sentences, in order. When the voice is done and
   placed, write `films/<name>/narration.json`; `cuts` are the seconds where the picture cuts (from your timeline):
   `{"words_file": "voices/words.json", "durations_file": "voices/dur.json",
     "lines": [{"id": "l01", "para": "P01", "at": 0.6}, …], "cuts": [0, 4.2, …]}`
   (`words.json` and `dur.json` are what the library's `tts.py` and `asr_check.py` write; `at` is the second the
   line starts in the final film).

If the customer asked to review the treatment, send that review only after the script passed:
`review request <id> --kind treatment --film <name> --summary <file>` adds the script and its scores. When they ask
for changes, change the script as asked, then `script check --customer-round` and `script review --customer-round`.

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
  `sh STUDIO/bin/studio qc <name>` (narration rhythm, cuts, stills over 6 s, characters with no font): fix what it
  reports and run it again. Then `job done <id> --film <name>`. The studio checks loudness (−14 ± 1 LUFS, true peak ≤ −1 dB), reading time, `qc` and
  the script's review again before delivery; a failure there gives you one round to fix it.
- If the film cannot be made, `job fail` as your instructions say.
