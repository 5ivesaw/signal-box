# Architecture and future website

Signalbox is an engine with two frontends: curses and a scriptable CLI. It does
not depend on a terminal, web framework, GPU runtime or GUI toolkit to render.

```text
TUI / CLI / future HTTP job worker
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

Canonical order is fixed in v0.1. Arbitrary drag-to-reorder, multi-track timelines,
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

## Website implementation path

Reuse this package inside background worker processes. An HTTP layer should:

- accept uploads into per-user job directories and translate opaque file IDs into
  paths controlled by the service;
- expose catalog/project validation and submit immutable project snapshots;
- relay `Job.emit` events over SSE/WebSocket and expose cancellation;
- serve completed preview MP4s, render outputs, and manifests;
- apply per-job runtime, disk, memory and concurrency limits, and clean expired
  uploads/previews;
- keep FFmpeg patched and isolate media decoders as untrusted-file workers;
- use authenticated asset ownership checks rather than accepting arbitrary server
  paths, FFmpeg arguments, Python expressions or shell commands.

A browser frontend can use the same IDs, settings, reasons and project JSON.
No TUI code needs porting. There is no HTTP server or deployment in this release;
this is the reusable foundation, not a claim that a website was already built.
