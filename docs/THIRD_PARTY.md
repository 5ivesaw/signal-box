# Third-party components

Signal Box's own source is MIT-licensed. This does not relicense its dependencies.
Browser runtimes are fetched from pinned official package distributions through
jsDelivr; their binaries are not included in this repository or Pages artifact.

| Component | Pinned browser version | License / source |
| --- | --- | --- |
| Pyodide | 0.27.7 | [MPL 2.0 and bundled package notices](https://github.com/pyodide/pyodide/tree/0.27.7) |
| CPython | bundled with Pyodide | [Python license](https://docs.python.org/3/license.html) |
| NumPy | 2.0.2 | [BSD-3-Clause and bundled notices](https://github.com/numpy/numpy/tree/v2.0.2) |
| SciPy | 1.14.1 | [BSD-3-Clause and bundled notices](https://github.com/scipy/scipy/tree/v1.14.1) |
| OpenBLAS | 0.3.26 | [BSD-3-Clause](https://github.com/OpenMathLib/OpenBLAS/tree/v0.3.26) |
| ffmpeg.wasm core | 0.12.10 | [Build/source and dependency licensing](https://github.com/ffmpegwasm/ffmpeg.wasm) |
| FFmpeg and compiled codecs | bundled in core | [FFmpeg legal information](https://ffmpeg.org/legal.html) |

FFmpeg core contains GPL/LGPL components and codec libraries with their own terms;
the JavaScript wrapper's license is not the license of the full compiled runtime.
If you redistribute vendored binaries, review and satisfy their corresponding
source and notice obligations. The optional fetch script is for local use and
records URLs, sizes and hashes in an ignored vendor ledger.

The native application invokes the user's installed FFmpeg and imports NumPy and
SciPy. Its distribution and enabled codecs vary by operating system. Synthetic
example videos were generated for this project; no third-party footage, fonts,
photographs or proprietary model weights are included.
