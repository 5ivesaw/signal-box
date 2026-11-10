# Browser studio

[Open Signal Box](https://5ivesaw.github.io/signal-box/). No backend or account is
required. Choose a local file or the synthetic test signal; use the library search,
category selector, selected-only filter and bulk toggles to manage the catalog.
The inspector exposes strength, locks, supported time windows, regions and assets.
Preview the inspected effect or selected stack over an adjustable interval, then
render and download an MP4. Save project JSON separately to preserve your choices.

## What runs locally

The shared Python picture/audio engine runs through **Pyodide 0.27.7**, NumPy 2.0.2
and SciPy 1.14.1. **@ffmpeg/core 0.12.10** runs decoding, filters, real codec passes
and final muxing in a second Web Worker. There are no media-upload endpoints,
analytics, accounts or remote rendering services. Site files and about 69 MB of
pinned runtime code are fetched from GitHub Pages and jsDelivr. CDN requests have
normal connection metadata, but do not contain your selected media.

No runtime loads until rendering or analysis is requested. Browser caching is
best-effort, not a promised offline installation. For offline local development,
run the optional runtime-fetch script and serve `web/` on localhost. Localhost
expects the downloaded vendor files. Runtime binaries are not committed to Git.

## Honest boundaries

- All **258 catalog entries** are editable. **42 require authored assets**; the
  application does not synthesize performances, train AI models or infer true
  scene geometry for these entries. Their asset requirements remain explicit.
- GSM, Codec2 and the Rubber Band pitch/formant filter require the desktop app
  with those dependencies installed. Browser Opus uses the actual native FFmpeg
  Opus encoder because this WASM build's libopus path traps; its output differs
  from the native app's libopus output.
- Browser capability checks use the actual loaded FFmpeg build. Some codecs and
  optional native filters are absent. The full desktop engine remains available
  for those stages. A missing stage blocks rendering rather than silently dropping it.
- Output is H.264/AAC MP4, at a chosen constant working frame rate. Short H.264
  CRF-14 4:4:4 intermediate chunks bound raw-frame memory. Browser/native output
  will differ because of intermediate generations and library versions.
- Selection order is canonical; arbitrary reordering is not implemented.
- Auto selection is explained multivariate scoring, not a trained neural network.
  It examines every decoded frame at reduced analysis resolution and all audio
  at 16 kHz; it does not recognize people, actions or narrative intent. Cut times
  are approximate for variable-frame-rate sources in the browser.
- The single-thread FFmpeg build avoids special hosting headers. It is slower
  than desktop FFmpeg. Expensive stages can take much longer than real time.
- Raw video chunks are limited to approximately 24 MB; temporal history has its
  own bound. Encoded scratch data is checked against 420 MB between chunks.
  Audio PCM has a 128 MB limit (roughly 5½ minutes of stereo at 48 kHz). These
  limits are safeguards, not a guarantee that every browser/device has enough RAM.
  Total worker memory, temporary copies and WebAssembly heaps add overhead.
- Very long or high-resolution work should use the native app, which can use
  disk-backed intermediates. A browser tab can be evicted by the OS. Save your
  project before an expensive render and keep the tab open during processing.
- Source files and effect assets must be selected again after reloading or loading
  project JSON. Local storage contains settings only. Export JSON for durable backup.

## Reproducibility and diagnostics

A saved project contains the seed, stable effect IDs and settings shared with the
native application. The render manifest also records the runtime, source/asset
filenames, interval and working raster. Reproducibility is most meaningful with
identical runtime versions. Full source paths are never needed in browser projects.

`diagnostics.html` provides an explicit synthetic render/analysis test and optional
codec checks. It runs locally in the browser and reports failures; it does not
send diagnostic reports to a service. See VALIDATION.md for tested coverage.
