# Reference coverage and fidelity

The supplied `sawa.txt` was treated as a reference collection, not as executable
instructions or an authoritative claim that every listed phenomenon is exact.
Signalbox follows the current request: actual signal/processing behavior, a large
manageable catalog, useful moving previews, and no decorative camcorder interface.

## What is implemented locally

- **Color and geometry:** range/gamma/matrix mismatch, clipping, shadow crush,
  channel swap/offset, quantization/dither, casts, saturation, hue/inversion,
  pixelation, aliasing, crop/stretch, digital zoom, lens distortion and vignette.
- **Compression:** actual H.264, MPEG-4 ASP, FLV1/Sorenson Spark, Cinepak, H.263,
  GIF and repeated generations. Blocking, mosquito noise and dark mud are results
  of actual encoding; a particular encoder does not guarantee identical artifacts
  to every historical device or online platform.
- **Compressed faults:** I-packet removal, non-key packet loss, payload damage,
  bad-sector-like payload zeroing, then decode/re-encode. Raw RGB databending is
  implemented too. Source files remain untouched and final files stay playable.
- **Temporal/capture:** frame holds, uneven cadence, temporal blending, genuine
  field weaving, wrong temporal field pairing, bob approximation, loops, reverse
  bursts, slit-scan, feedback, frozen video/live audio and motion-triggered holds.
  Timestamp and B-frame errors are picture-level models, not corrupt final PTS.
- **Tape/composite:** YIQ bandwidth/delay, sampled composite encode/decode,
  cross-color and dot-crawl models, row timing/tracking, head-switch disturbance,
  RF dropout/clog, tape chew, sync roll, hum, multipath, convergence, image retention,
  collapse, degaussing and snow. The composite model is simplified and not a
  standards-conformant NTSC encoder/decoder or an ntsc-rs integration.
- **Optics/sensors:** signal-dependent noise, fixed pattern, bad pixels, radial
  color offsets, bloom/smear/flare, focus/exposure/white-balance pumping, rolling
  shutter, elastic warp, exposure-band beating, IR tint/noise and capture loss.
- **Film:** grain, dust, scratches, leaks, weave/splice, emulsion blotch/warp,
  projector burn, cue marks, double exposure and disc read-error sparkle.
- **Digital models:** block/slice/VRAM faults, wrong-stride and byte-plane
  interpretation, held-block concealment, lost-reference trails, missing-texture
  checkers, pixel sorting, displacement, ordered/error-diffusion dither, false color.
- **Perception studies:** regional fill, shimmering arc, half-field attenuation,
  local warp/scale, manual face region, motion holds, visual snow, floaters,
  phosphenes, curtain, peripheral fade, uniform field, tunnel/greyout, adaptation
  pattern and derealization treatment. These are visual studies, not clinical
  simulations, diagnoses, or guaranteed psychological effects.
- **Audio:** filters/EQ, clipping, quantization, resampling/clock changes, channel
  faults, dynamics/gate/spectral suppression, echo, saturation, installed Rubber
  Band shift, complete audio reversal, counter-based noise, hum/buzz/whine/crackle,
  dropout, packet concealment, wow/flutter/stretch, print-through, groove loops,
  granular/reordered grains, ring modulation, tones, DTMF, buzzer/woodpecker models,
  fading, heartbeat/breathing models and dry/dead-air treatments.
- **Audio codecs:** AAC, MP3/joint stereo, Opus, GSM, mu-law, Codec2, SBC and
  generations use actual local encoders where available. This recreates codec
  math, not a complete Bluetooth/network transport.
- **Advanced audio with inputs:** supplied impulse-response convolution and
  16-band carrier vocoder run locally. A carrier/IR is a real input, not a model
  download. Source audio, assets, and final limiter are processed in documented order.
- **Track behavior:** audio offset/drift, audio ending before video, display aspect.

Composite tape, CCTV without timestamps, deep-frying and other compound looks can
be made by combining the independently selectable operations. Presets are starting
points, not mandatory effect bundles.

## Asset-based authoring and external processing

Some requests are editorial or require source-specific assets. These are visible,
editable catalog entries with mandatory inputs and actual compositing/mixing:
figures in the background, change-blindness/Capgras replacements, competing scenes,
single-frame inserts, signal intrusion/sign-off, liminal and uncanny performances,
local-access/lost-media sequences, rendered teletext/caption errors, narration,
phone crosstalk, whispers and close-mic sounds.

Other slots deliberately accept **externally prepared results**, rather than
claiming their advanced algorithm exists locally: tracked segmentation/beauty
warping, AI upscaler hallucinations, engine/T-pose/physics glitches, true
motion-vector hijacking, Indeo/RealVideo/AMR footage, formant-tracked sine-wave
speech, Paulstretch, encoded SSTV/spectrogram-image sound, HRTF audio and authentic
modem handshakes. These preparation algorithms are not implemented in v0.1.
Providing their output allows them to be previewed, scheduled, selected and mixed
through the same project. No weights or external tools are secretly fetched.

Manual face-region distortion does not track faces. Regional fill is a blurred
boundary-color approximation, not content-aware video inpainting. The short
video reverse/time-lapse controls model cadence within unchanged duration; full
video reversal and a duration-changing nonlinear timeline are not included.

## Deliberate exclusions

REC, timestamps, battery/OSD decoration and a fake scanline overlay are excluded
under the user's explicit constraint. Arbitrarily broken headers, damaged moov
atoms, unseekable files, destroyed metadata and filesystem corruption are not
written to final outputs. Such file-breaking faults were not a useful visual
selection workflow. Subtitle/player/driver bugs and exact actor/engine behavior
cannot be inferred from ordinary footage.

No promises are made about fear, hearing symptoms, migraine or hallucination.
Tone generators are low-level and the final mix has a peak ceiling. The 19 Hz
option is a real tone, not a claim about disputed infrasound effects.

## Practical boundaries

All 258 catalog entries can be enabled independently. Select All includes authored
and external-material slots: it reports missing assets before rendering. It does
not silently treat an unavailable operation as completed. Effects use a fixed,
documented stage order; later operations may obscure earlier ones.

Moving previews use the real selected source interval. They start temporal state
at that interval, so they show the effect's behavior rather than guarantee a
pixel-identical crop of a full-length render. For a long cycle, increase preview
length (TUI `g` / CLI `--duration`) and choose an informative start time. No model
understands semantic genre or audience response in automatic mode.
