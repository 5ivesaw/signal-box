# Signal Box

A local video degradation workbench for your **browser and terminal**.
Composite bandwidth, tape timing, film damage, temporal errors, actual codec
generations, controlled bitstream damage, and audio degradation. No REC/battery
UI decoration and no fake CRT scanline overlay.

**258 individually selectable entries.** The catalog distinguishes implemented
processes, physical/perceptual models, and authored techniques that need assets.
Some advanced techniques accept externally prepared material; Signalbox does not
claim to generate acting, AI hallucinations or true face tracking with a filter.
See [the full catalog](docs/CATALOG.md) and [coverage and limitations](docs/COVERAGE.md).

## Open the browser studio

**[Launch Signal Box →](https://5ivesaw.github.io/signal-box/)** · [Browse the catalog](docs/CATALOG.md) · [How it works](docs/ARCHITECTURE.md)

Open a video, browse the searchable library, then preview an effect or your whole
chain. Motion previews use your actual source. Choose adaptive analysis, a seeded
chaos combination, a preset, or every effect; all choices remain individually editable.
Lock included or excluded effects to protect them from automatic selection.

The app workspace includes **Shift-click range selection, Ctrl/Cmd-click multiple
selection, batch actions, an effect context menu, undo/redo, and a searchable
command palette**. Press **?** for shortcuts or **Ctrl/Cmd+K** for commands.

The site is static GitHub Pages: **no account, backend, media upload or hosting
subscription**. Rendering runs in dedicated browser workers using the same Python
picture/audio models through Pyodide and FFmpeg WebAssembly. The first render or
analysis loads about **69 MB** of pinned runtime files from jsDelivr. Your video and
assets stay on your device. Browser caching determines whether subsequent visits
need another download.

Start with a short 480-pixel preview. A recent desktop browser is recommended;
WebAssembly is considerably slower than native FFmpeg and has tighter memory
limits. The full catalog is browsable, but the browser codec build does not contain
every native dependency. Unsupported stages and missing assets are named before
rendering; effects are never silently omitted. See [browser support and limits](docs/BROWSER.md).

Save project JSON and download your finished MP4 plus its settings manifest.
Saved projects contain settings and filenames, not video data: reselect local
media after opening a project or returning to the page. Keep separate media backups.

## Run the terminal app

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
prerequisites supplied separately. The native app reused installed dependencies; the optional browser runtime fetched
during development totals **68,849,742 bytes**.
See [installation and resource budgets](docs/INSTALL.md).

For an installed command, in your chosen environment:

```sh
python3 -m pip install --no-deps --no-build-isolation -e .
signalbox tui /path/to/video.mp4
```

## Choose your workspace

| | Browser studio | Terminal / CLI |
| --- | --- | --- |
| Setup | Open the site; runtime loads on demand | Python, FFmpeg, NumPy, SciPy |
| Media | Local File objects; no upload | Local filesystem; no upload |
| Selection | Search, categories, bulk toggles, locks | Live search, categories, shortcuts, locks |
| Preview | Adjustable moving MP4 in the page | Moving MP4 plus optional FFplay |
| Automatic mode | Whole-source measurements and reasons | Whole-source measurements and reasons |
| Long renders | Limited by browser memory | Disk-backed intermediates |
| Project | Shared JSON schema + saved seed | Shared JSON schema + saved seed |
| Codec coverage | Pinned WASM build; explicit checks | Installed FFmpeg build; explicit checks |

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

## Source, backup and development

The complete source lives in **[5ivesaw/signal-box](https://github.com/5ivesaw/signal-box)**.
Clone it to recover the app on another machine:

```sh
git clone https://github.com/5ivesaw/signal-box.git
cd signal-box
./signalbox-run doctor
```

The MIT-licensed application includes the Python package, browser frontend, tests,
portable examples, contributor guide, and GitHub Actions for tests and Pages.
The shared catalog and project schema keep improvements reusable across frontends.
No web framework, npm dependency tree, model weights, or build service is needed.

```sh
python3 scripts/build_web.py       # regenerate shared catalog + Python archive
python3 scripts/fetch_web_runtime.py  # optional: ~69 MB for local development
python3 -m http.server 8766 --directory web
# Open http://localhost:8766
```

Localhost uses the optional vendored runtimes; the public site loads pinned CDN
runtimes. Vendor files are ignored by Git. Pushes to `main` deploy the static site
after the checks pass. See [architecture](docs/ARCHITECTURE.md),
[contributing](CONTRIBUTING.md), and [third-party notices](docs/THIRD_PARTY.md).

## Verify

```sh
python3 -m unittest discover -s tests -v
./signalbox-run doctor
```

Implementation references: [FFmpeg filters](https://ffmpeg.org/ffmpeg-filters.html)
and [FFmpeg bitstream filters](https://ffmpeg.org/ffmpeg-bitstream-filters.html).
Capability checks use the installed build; optional encoders vary by distribution.
