# Contributing

The Python core has no UI imports. Put new effects into `signalbox/catalog.py`
and their implementation into the relevant processing module. Keep stable IDs;
projects and manifests depend on them. Label actual operations `process`, physical
approximations `model`, and asset-based editorial techniques `authored`.
Never relabel a cheaper approximation as an exact process.

Run `python3 -m unittest discover -s tests -v`. Include a synthetic, small test
for behavior and a real FFmpeg round trip for new codec or filter integrations.
Test time windows, strength zero, duration and cancellation. Avoid whole-video
arrays, opaque downloads, and user-specific absolute paths in examples.

New optional dependencies must document binary download sizes and remain opt-in.
Use `Job.emit` for progress and `Job.check` in processing loops. Register spawned
processes through `Job.spawn` so cancellation reaches the entire pipeline.
See `docs/ARCHITECTURE.md` for shared frontend and extension boundaries.

After changing shared modules, run `python3 scripts/build_web.py` and commit the
updated `web/catalog.json` and `web/engine.zip`. Check JavaScript with
`npm --prefix web run check` (no npm install is needed). Serve the site locally
and run its synthetic `diagnostics.html` checks; cover UI behavior in a browser.
Keep media local and runtime downloads explicit. Do not add analytics or upload
endpoints without a deliberate, documented privacy-design change.
