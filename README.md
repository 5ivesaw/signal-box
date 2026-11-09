# Signalbox

A signal-first video degradation workbench with a fast terminal interface.
Composite bandwidth, tape timing, film damage, temporal errors, actual codec
generations, controlled bitstream damage, and audio degradation. No REC/battery
UI decoration and no fake CRT scanline overlay.

**258 individually selectable entries.** The catalog distinguishes implemented
processes, physical/perceptual models, and authored techniques that need assets.
Some advanced techniques accept externally prepared material; Signalbox does not
claim to generate acting, AI hallucinations or true face tracking with a filter.
See [the full catalog](docs/CATALOG.md) and [coverage and limitations](docs/COVERAGE.md).

## Run

Requires Python 3.10+, FFmpeg/FFprobe, NumPy, SciPy, and a terminal with curses.
Linux and macOS are the intended platforms. Use WSL on Windows. FFplay is optional
for opening previews. No GPU or downloaded model is required.

```sh
cd Signalbox
./signalbox-run doctor
./signalbox-run tui /path/to/video.mp4
```

If NumPy or SciPy is missing:

```sh
python3 scripts/bootstrap.py
./signalbox-run doctor
```

The optional installer reuses existing packages or fetches only two binary wheels,
verifies their hashes, and caps application payload downloads at **200 MB**, leaving
100 MB below the requested total budget. It never compiles source dependencies or
fetches model weights. Python, pip/venv, FFmpeg and terminal support are foundational
prerequisites supplied separately. **Development downloaded 0 bytes of dependencies.**
See [installation and resource budgets](docs/INSTALL.md).

For an installed command, in your chosen environment:

```sh
python3 -m pip install --no-deps --no-build-isolation -e .
signalbox tui /path/to/video.mp4
```

## TUI workflow

1. `O` opens a local video. `/` searches live; `Tab` browses categories.
2. `Space` enables/disables an effect. `+`/`-` adjust strength; `e` edits parameters.
   `s` shows selected entries; `h` shows expensive ones; `f` toggles filtered results.
3. `p` makes a motion preview of the focused effect on your actual video, `v` previews
   the full stack, `b` makes the baseline, and `o` opens the last clip in FFplay.
   `g` chooses the start and duration; default previews are 8 seconds, not stills.
4. `a` analyzes the entire source and selects effects using measured picture/audio
   characteristics. `i` shows the measurements and reasons. `l` locks an enabled
   or excluded choice against auto mode, presets and chaos.
5. `c` makes a new, saved-seed chaos combination. `A` enables every entry. Asset slots
   stay selected and preflight reports anything missing; nothing is silently skipped.
6. `d` checks requirements, `S` saves a portable JSON project, `R` renders, `x` cancels.
   `w` changes working width, frame rate and CPU threads. `?` shows complete help.

The UI stays responsive during worker jobs. Selected heavy effects show a warning.
For an EliteBook-class dual-core laptop, start with the default **854-pixel width,
two FFmpeg threads**, and 480-pixel previews. Native resolution is available with
width 0. No benchmark on that exact laptop is claimed.

Automatic selection examines **every decoded frame** at 160×96 across the entire
video, and all decoded audio samples at 16 kHz. It measures luminance distribution,
contrast, detail, chroma, motion, cuts, flicker, clipping, a noise proxy, audio RMS,
peak, silence, spectral bands and stereo correlation. It uses explained multivariate
heuristics and category diversity, **not a trained neural network or scene semantics**.

## Scriptable commands

```sh
./signalbox-run catalog tape
./signalbox-run catalog --json > catalog.json
./signalbox-run analyze input.mp4 -o analysis.json
./signalbox-run save input.mp4 --preset tape -o tape.json
./signalbox-run preview --project tape.json --effect tracking --start 20 --duration 12
./signalbox-run render --project tape.json -o output.mp4
./signalbox-run render input.mp4 --auto --width 854 -o adaptive.mp4
./signalbox-run render input.mp4 --chaos --seed 1234 -o chaos.mp4
./signalbox-run plan input.mp4 --all
```

Parameters use JSON values:

```sh
./signalbox-run save input.mp4 --effects tracking,being_watched \
  --set tracking.strength=0.35 \
  --set being_watched.asset='"figure-on-black.mp4"' \
  --set being_watched.start=12 --set being_watched.end=25 \
  --set being_watched.roi='[0.7,0.2,0.15,0.5]' -o authored.json
```

The default output is playable H.264 + AAC in MP4 or MKV. Actual corruption happens
only to disposable intermediates; recovered pictures are encoded to a valid final
stream. Every render writes a settings/seed/provenance manifest beside the output.
Existing output names are protected unless CLI `--overwrite` is explicit. Input
and asset files cannot be overwritten, even with that flag.

A six-second synthetic source, tape demonstration, and editable project are in
`examples/`. Try `./signalbox-run tui --project examples/tape-project.json`.

## GitHub backup and development

This folder is a standalone MIT-licensed repository with `pyproject.toml`, tests,
GitHub Actions, an issue template, `.gitignore`, and architecture documentation.
It is ready to commit and push to a GitHub repository you own. Nothing has been
uploaded to GitHub automatically. To back up using GitHub CLI after creating an
initial commit (a ZIP extraction needs `git init`, `git add .`, and `git commit` first):

```sh
gh repo create Signalbox --private --source=. --remote=origin --push
```

Change `--private` to `--public` if you want a public release. Media, saved private
projects and generated renders are not needed in the source repository. Keep
separate backups of your original videos and assets.

For a future website, import `signalbox.api` from a background job worker; the
catalog, JSON project, renderer, previews, analysis, progress and cancellation are
independent of curses. See [architecture](docs/ARCHITECTURE.md).

## Verify

```sh
python3 -m unittest discover -s tests -v
./signalbox-run doctor
```

Implementation references: [FFmpeg filters](https://ffmpeg.org/ffmpeg-filters.html)
and [FFmpeg bitstream filters](https://ffmpeg.org/ffmpeg-bitstream-filters.html).
Capability checks use the installed build; optional encoders vary by distribution.
