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

If `films/<name>/CHANNEL_BRIEF.md` exists, the film belongs to one of the customer's channels: read it first and
follow it (language, length, style, voice and speed in `lines.json`, title and thumbnail rules, never-use words,
hashtags, lessons). The studio checks the channel's rules and lessons in `script check`, `qc` and `publish`.

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
`Treatment`, `Script`, `Look`, `Voice`, `Music`, `Picture`, `Mix`, `Render`, `Self-check`, `Publish` (no Storyboard online).

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
   `{"words_file": "voices/words.json", "durations_file": "voices/dur.json", "lines_file": "lines.json",
     "lines": [{"id": "l01", "para": "P01", "at": 0.6}, …], "cuts": [0, 4.2, …]}`
   (`words.json` and `dur.json` are what the library's `tts.py` and `sh STUDIO/bin/studio voice asr <name>` write;
   `lines_file` is the `lines.json` you gave `tts.py`; `at` is the second the line starts in the final film). `qc`
   checks that the voice lines say exactly the passed script.

## The checks before rendering (every film, specs/020)

Each fault comes with its shot or line id, the second, and how to fix it. Fix and run the same command again.

- The page exports `window.SHOTS` (`[[t0, t1, set, shot id]]`, joined from 0 to `DUR`), and should export
  `window.CARDS` (`[[t0, t1, id, text]]`) and `window.CUES` (or write `cues.json`), and draw no subtitle or card
  when `window.CLEAN` is true.
- **Voice step**, right after the voice is made: `sh STUDIO/bin/studio voice asr <name>` (the studio's speech model;
  never call `asr_check.py` yourself), then `sh STUDIO/bin/studio qc voice <name>`. Redo only the lines it names.
- **Picture step**, before any full render: `sh STUDIO/bin/studio qc plan <name>` (seconds; rhythm, shot lengths,
  subtitles, cards), then `sh STUDIO/bin/studio qc shots <name>` (one frame per shot; look at
  `.check/shots/sheet-1.jpg` once). A shot that is flat or dark on purpose:
  `sh STUDIO/bin/studio qc except <name> <shot> <rule> --reason "…"`, one shot at a time. A style warning: fix it,
  or accept it with `sh STUDIO/bin/studio qc accept-style <name> --reason "…"` when the brief asks for it.
- **Render step:** `render` refuses to start until both checks pass, and stops at a chunk with black frames or a
  still shot: fix that shot and run it again (the chunks before it are kept). Never use `--skip-checks` for the
  delivered film.

A changed version of a finished film ("Request changes"): copy the old film's SCRIPT.md, SOURCES.md, checks.json
and `.check/` with the rest. Only when the note changes the narration, change the script as asked and run
`script check --customer-round` and `script review --customer-round`; otherwise keep script and voice as they are.

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
- **Record with the studio, not the library's `video.mjs`:** `sh STUDIO/bin/studio render <name> --fps <the style's rate>` (GPU when the
  machine has one, 10-second chunks that survive a crash; run it again to resume). Page tools the same way:
  `sh STUDIO/bin/studio page still|events|readcheck <name> …`. The log's first line says `render: gpu` or `render: software`.
- **Render once you are sure.** Test with a few frames or a short range before the full render; a full render
  plus a re-render is the most expensive loop.
- Do not explore: no `ls -R`, no reading files "to see what is there".

## The Publish step (every film, after the self-check)

The studio makes the customer's YouTube pack (thumbnails, titles, description, chapters, subtitles) from one small
file you write. It costs little: write it in one `Write`, run one command, fix at most once.

1. `job step <id> Publish`.
2. Write `films/<name>/publish/pack.json`. Pick the 3 thumbnail times from the self-check contact sheet you already
   looked at: strong, clear frames, at least 1 s apart. Do not render or look at new pictures for this.
   ```json
   {"language": "<the film's language, as in SCRIPT.md>",
    "titles": [
     {"angle": "curiosity", "text": "<title>", "thumb": {"t": <seconds>, "text": "<2–6 words>", "position": "bottom"}},
     {"angle": "number",    "text": "<title with a number or a benefit>", "thumb": {"t": <seconds>, "text": "…"}},
     {"angle": "question",  "text": "<title that asks>", "thumb": {"t": <seconds>, "text": "…", "position": "top"}}],
    "hook": ["<line 1>", "<line 2>"],
    "summary": "<2–3 sentences>",
    "chapters": [{"from": "P01", "title": "<≤ 40 characters>"}, {"from": "P03", "title": "…"}, …],
    "hashtags": ["#…", "#…", "#…"]}
   ```
   - Titles: at most 100 characters, and the first 60 must make sense alone (put a `:` or `?` before 60 if longer).
   - The text on each thumbnail adds to its own title; it never repeats the title's words.
     Put it (`position`) where that frame has no text of its own (a clock, a caption), so the two do not overlap.
   - The 2 hook lines together: at most 150 characters. 3–5 hashtags.
   - Chapters: the first is the first paragraph; at least 3, each at least 10 s long (paragraph times are in
     narration.json). A film too short for that: `"chapters": []`.
   - Numbers only as they appear in SCRIPT.md or SOURCES.md. No `<` or `>`. No channel, creator or brand names.
   - Optional per thumbnail: `color`, `plate` (a colour behind the text, or `null`), `plate_opacity`, `font` (one of
     the film's fonts). The defaults (white text on a dark plate, the film's font) are usually right.
3. `sh STUDIO/bin/studio publish <name>`: exit 0 is done. Exit 1 lists problems: fix `pack.json` once and run it
   again. Then go on to `job done` whatever the result; the pack never stops the film from being delivered.

## Finishing

- Self-check against DIRECTOR.md §11 with one contact sheet and the loudness check, then
  `sh STUDIO/bin/studio qc <name>` (the same rhythm rules as `qc plan`, plus loudness range, sound against picture,
  stills over 6 s, characters with no font): fix what it
  reports and run it again. Then the Publish step, then `job done <id> --film <name>`. The studio checks loudness (−14 ± 1 LUFS, true peak ≤ −1 dB), reading time, `qc` and
  the script's review again before delivery; a failure there gives you one round to fix it. After that fix and the
  new render, run `studio publish <name>` again before `job done`: the thumbnails come from the render.
- If the film cannot be made, `job fail` as your instructions say.
