# Validation record — 2026-11-10

Environment: Linux, Python 3.12.3, NumPy 1.26.4, SciPy 1.11.4, FFmpeg 6.1.1.
No dependencies, optional tools, or model weights were downloaded during development.

## Completed checks

- 18 unittest methods passed (10 core, 8 FFmpeg integration). Parameterized loops
  exercised all 101 picture-model operations and all 41 procedural audio operations,
  plus the raw-databending path and all native picture/audio filter recipes.
- Tests cover saved-project validation, source/asset overwrite protection,
  seeded selection, locked exclusions, data-dependent recommendations, temporal
  field behavior, zero strength, time windows, deterministic noise, bounded history,
  forward print-through pre-echo, disk-backed complete audio reversal, and caching.
- Real FFmpeg integration covers complete-duration analysis, source audio and
  synthetic audio beds, asset compositing/mixing, cancellation cleanup, partial
  intervals, final media decoding, output duration and optical-flow boundary padding.
- Every one of the **23 video/audio codec catalog entries** completed a separate
  real encode/decode round trip with the installed encoders. Result duration was
  checked. This does not guarantee damaged inputs always recover with other builds.
- A **42-entry asset stack** rendered with synthetic picture/audio supplied to all
  slots. This verifies the compositor/mixer integration, not the authenticity of
  externally prepared AI, speech, HRTF, engine or legacy-codec material.
- A final **258-entry Select All stack**, with all required assets supplied, rendered
  a three-second 96-pixel test interval and retained exactly 3.0 seconds of video.
  This exercises every selected stage, including codec damage and recovery. It is
  a functional stress test, not a claim that all effects remain visually separable.
- An automated PTY interaction opened the TUI at 125×32, searched for tracking,
  toggled it, edited the preview interval, generated a moving preview, and exited
  successfully. Test state/cache were isolated from user home state.
- `pip wheel --no-index --no-deps --no-build-isolation` built the package offline.
- A six-second 640×360 synthetic source and tape/composite example were rendered;
  a before/after frame was visually inspected. The source contains no added REC,
  battery or decorative scanline interface.

## Reproduce

```sh
python3 -m unittest discover -s tests -v
python3 scripts/verify_catalog.py validation.json
```

The extended command tests available codecs and the large built-in/asset stacks.
A missing optional encoder is reported as unavailable, not a passing codec test.
For full Select All, supply an audio/video asset to each asset-dependent entry.

No full-length personal video, actual EliteBook 840 G3, macOS/WSL installation,
network-restricted fresh dependency installation, was available for validation. Long videos, codec builds, malformed files and extreme parameter stacks
can expose further issues. The code and issue template are supplied for continued
improvement.


## Browser port (v0.2)

- 23 native/bridge unittest methods pass, including shared picture/audio math,
  temporal history across chunks, incremental analysis, authored time windows,
  and a non-multiple-of-16 raster regression found during browser testing.
- A real studio preview downloaded and was independently inspected by ffprobe:
  H.264 + AAC, 480×270, exactly 1.0 seconds.
- Browser whole-source analysis examined all 144 frames of the six-second fixture.
- A 192-entry built-in picture/filter/audio/timing stack completed in WASM/Pyodide.
  The unavailable Rubber Band filter was explicitly excluded for that test.
- 21 of 23 codec entries passed browser encode/decode round trips. GSM and Codec2
  are explicitly unavailable. Opus passed using the native FFmpeg Opus encoder.
- All 42 authored slots completed a combined browser render using synthetic assets.
  This validates compositing/mixing, not the authenticity of external AI or speech.
- Browser UI checks covered search, focused previews, locks, chaos and all 258
  selections. The synthetic diagnostic page provides repeatable engine checks.

The native all-258 stress test above is separate from browser coverage. Runtime
versions and memory limits are documented in BROWSER.md; native success does not
imply a particular browser has enough memory or the same codec libraries.
