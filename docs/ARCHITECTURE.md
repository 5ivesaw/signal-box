# Architecture

Signal Box shares its catalog, schema and DSP across curses, CLI and browser frontends. The native engine does
not depend on a terminal, web framework, GPU runtime or GUI toolkit to render.

```text
TUI / CLI / Python API
              |
       signalbox.api
              |
  Project schema v1 + effect catalog
              |
   preflight / analyze / preview / render
              |
 FFmpeg subprocesses + NumPy/SciPy DSP
              |
 MP4/MKV + reproducibility JSON manifest
```

## Public interface

```python
from signalbox.api import Project, Job, render, analyze, apply_auto, catalog

project = Project(source="/media/source.mp4", width=854, threads=2)
project.set("chroma_bleed")
project.set("wow")
job = Job(callback=lambda event: print(event))
report = analyze(project.source, job=job)
apply_auto(project, report)  # honors locked enabled and excluded settings
render(project, "/media/result.mp4", job=job)
# From another thread: job.cancel()
```

The callback receives dictionaries with `stage`, optional `fraction`, and optional
metadata. Fractions describe the current stage, not a fabricated end-to-end ETA.
Rendering blocks the calling worker. Cancellation is cooperative for DSP and also
terminates registered FFmpeg subprocesses. The TUI runs workers outside curses.
All subprocess commands use argument arrays; no shell interpolation of filenames.

`catalog()` returns JSON-compatible records. `Project.to_dict()` / `from_dict()`
are the serialization boundary. Schema v1 rejects unknown effects or unsupported
versions. Relative source/asset paths in a saved project resolve relative to that
project file. Saved settings include enabled, locked, strength, source-time window,
normalized region and optional asset. Effect IDs are stable extension points.

## Pipeline and ordering

1. Decode the selected source interval, normalize sample aspect ratio, resize and
   convert source cadence to the working constant frame rate.
2. Run custom picture effects in catalog order over a bounded raw-frame history.
   Apply authored picture slots after those models.
3. Run selected native FFmpeg picture filters, then encode an intermediate.
4. Run actual codec generations and controlled compressed-payload damage. Decode
   each damaged intermediate and recover it to a playable H.264 stream.
5. Decode the first audio stream to stereo float PCM (or create a silent bed when
   audio effects are explicitly selected on a silent video). Apply audio filters.
6. Apply chunked DSP and authored audio, then selected audio codec round trips.
7. Apply a final audio peak ceiling, track timing, and mux MP4/MKV. Publish output
   atomically without overwriting existing media by default; write a manifest.

Canonical order is fixed in v0.2. Arbitrary drag-to-reorder, multi-track timelines,
keyframed regions and node graphs are future work. Select All runs every selected
stage, even when later stages visually mask earlier ones. Empty asset slots and
unavailable codecs fail preflight with their names, never silently disappear.

Video memory is bounded by the raster plus at most 32 history frames, with history
storage capped around 128 MiB. Audio uses disk-backed PCM and four-second chunks;
impulse responses are capped at 10 seconds. Codec stages use disk intermediates.
The source file is immutable. FFmpeg and NumPy versions appear in the manifest;
seed reproducibility is best compared on the same installed codec build.

## Adding effects

Add an `Effect` record to the catalog, dispatch its recipe in the applicable module,
and add behavior and integration tests. Use `process` for the actual implemented
operation, `model` for a physical approximation and `authored` for asset-dependent
editorial work. A single process can still approximate a broader real-world system.
Never imply that a perception study reproduces or diagnoses a neurological state.

Frame effects use `apply(recipe, frame, setting, frame_number, source_time, rng)`.
Audio DSP reads slices from memory-mapped samples and writes to alternating scratch
files. Complex filters should keep their state bounded or explicitly report cost.
Optional external models should become separately installable backends with their
own download accounting and capability checks, not hidden runtime downloads.

## Browser implementation

`web/` is a buildless static application. `scripts/build_web.py` exports the canonical
catalog and packages Python modules into `engine.zip`. `signalbox.browser` adapts
the original FrameEngine, audio synthesis, FFmpeg filter recipes and recommendation
scorer to buffers passed through a Pyodide worker. It does not emulate those effects
with unrelated CSS or canvas filters.

`engine.js` orchestrates the Python worker and a separate single-thread FFmpeg WASM
worker. Local File objects are mounted read-only with WORKERFS. Decoded picture
chunks are limited to two seconds or roughly 24 MB, whichever is smaller. The
Python engine preserves temporal history between chunks. Intermediate chunks use
H.264 CRF 14, 4:4:4 before filters and final encoding; this extra generation means
browser and native output are not pixel-identical. Audio currently uses bounded
in-memory PCM, unlike the native disk-backed implementation.

Adaptive analysis examines every decoded frame at 160×96 and all audio at 16 kHz,
using incremental statistics. Browser cut times use the average source cadence;
VFR cut timing is approximate. Analysis and rendering use workers so controls remain
responsive. Cancellation terminates both workers; the next job reloads the engine.

The browser sends no media to a server. Only runtime code and site assets are
fetched. No COOP/COEP headers or SharedArrayBuffer are required, allowing ordinary
GitHub Pages hosting. Runtime versions and limitations are in BROWSER.md.

New Python effects should also be exercised through `tests/test_browser_bridge.py`
and the browser diagnostic page. Update generated browser assets after changing
the catalog, presets, schema or shared modules. Browser codec stages have an
explicit JavaScript orchestration adapter, so new codec recipes need both native
and browser implementations.
