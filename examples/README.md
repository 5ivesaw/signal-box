# Synthetic example

`test-pattern.mp4` is a six-second FFmpeg-generated source. `tape-demo.mp4` applies
chroma bandwidth/delay, composite separation, tracking/head-switch/dropout, and
wow/flutter/hiss. It demonstrates processing behavior, not a finished horror edit.
The test pattern is generated locally, not downloaded source footage.

Open the editable project:

```sh
./signalbox-run tui --project examples/tape-project.json
```

Or render it to a new file:

```sh
./signalbox-run render --project examples/tape-project.json -o my-tape.mp4
```

The example's source path is relative to the JSON file, so it survives moving the
repository. Set your own source with `O` and adjust individual effects in the TUI.
