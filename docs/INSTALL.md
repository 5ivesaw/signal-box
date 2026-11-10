# Installation, budget and performance

## Supported setup

Python 3.10+, NumPy >=1.24,<3, SciPy >=1.10,<2; FFmpeg/FFprobe with libx264 and AAC.
Linux/macOS curses terminal, at least 70×20 cells (100×30 is more comfortable).
FFplay is optional. Windows users can use WSL. The TUI is not native Windows curses.
The tested local environment is Python 3.12, NumPy 1.26.4, SciPy 1.11.4, FFmpeg 6.1.1.

`./signalbox-run` changes into the repository and uses `.venv/bin/python` if present,
otherwise `python3`. Pass absolute video paths from outside the repository, or run
`python3 -m signalbox` from the repository with relative paths. Installation with
pip exposes the `signalbox` command in the chosen environment.

## Download accounting

The native implementation reused installed libraries/tools. The browser runtime
vendor script fetched **68,849,742 bytes** during development. Production browsers
fetch approximately 69 MB on first use from pinned official package CDN URLs.
Native rendering never downloads anything; browser runtime caching is controlled
by the browser. Do not combine repeated fresh runtime downloads and optional
installers without accounting for their sum under a metered data budget.

`scripts/bootstrap.py` is optional and explicit. If NumPy/SciPy are importable it
exits with zero downloads. Otherwise it fetches pinned binary wheels (NumPy 2.2.6,
SciPy 1.15.3) using the interpreter's platform tags and verifies PyPI SHA-256 hashes.
Metadata and wheels share a **200,000,000-byte payload ceiling**, reserving 100 MB
below the requested 300 MB budget for transfer overhead. It checks advertised
sizes before fetching and enforces the ceiling while reading. It installs offline
with `--no-index --no-deps`, records a ledger, and never attempts a source build.
If wheels are unavailable, it stops. It does not fetch FFmpeg, Rust, OpenCV,
PyTorch, pretrained models, node modules or optional tools.

Python, pip/venv and FFmpeg are foundational tools supplied separately as permitted
by the request. GitHub-hosted CI downloads its own dependencies; those downloads
are on the runner, not the laptop's connection. Installing optional packages
manually is outside the managed installer budget and must be accounted for by you.

## Modest hardware

Default working width is 854 pixels, preview width 480, two FFmpeg threads. Width 0
keeps the source display raster; FPS 0 follows source average rate up to 120 fps.
The source is converted to a constant working cadence; VFR timing is not preserved
bit-for-bit. Auto analysis still examines every decoded original frame and its PTS.

At these defaults, picture history has a fixed upper bound rather than growing
with clip duration. Audio is processed in four-second chunks using disk-backed PCM.
Long clips can need substantial temporary disk: uncompressed stereo float audio is
about **1.38 GB/hour per scratch copy**. DSP uses several copies; supplied audio
assets and codec intermediates add more. `plan` gives rough estimates; they are not
a hard upper bound, especially for large asset sets. The working filesystem must
have room for intermediates as well as the final output. CLI `--scratch` selects
another disk for renders and explicit `preview -o` jobs.

Cost labels are qualitative. Native color/EQ filters are usually lighter; Python
full-raster warps, sorting and many stacked models cost more. Optical flow,
Floyd–Steinberg error diffusion, Cinepak and repeated encode/decode passes can be
much slower than real time. Preview a representative interval to measure your own
machine. No speed promise or benchmark on an HP EliteBook 840 G3 is implied.

## Troubleshooting

- Run `doctor`. Optional encoders/filter builds vary; preflight names missing ones.
- If a source has no duration, remux it into a seekable local file first.
- If damage cannot be decoded, lower its strength or try another interval; no
  decoder can guarantee recovery from arbitrary corruption.
- TUI `i` shows errors and auto-selection reasons. `x` cancels an active worker.
- Without a display, previews are still written as MP4s. Open them with any player;
  FFplay launching from `o` requires a usable video display.
- Cache files are under `$XDG_CACHE_HOME/signalbox` (default `~/.cache/signalbox`).
  Delete that folder when you want to reclaim preview disk. No auto cache eviction
  is implemented yet.
- Recovery autosave is under `$XDG_STATE_HOME/signalbox/last-project.json`.
  Use `L` to load it. `S` writes a project wherever you choose.
