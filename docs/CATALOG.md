# Effect catalog

258 entries. `process` = actual named operation; `model` = approximation; `authored` = supplied material.

Heavy stages can be much slower than real time. Every entry has strength and enabled controls; frame/DSP/asset stages also accept source-time windows.

## Color & tone

| ID | Name | Fidelity | Cost | Required asset | Method |
|---|---|---|---|---|---|
| `range_crush` | Limited/full range crush | process | light | — | Interpret limited levels as full, then crush the ends. |
| `range_wash` | Raised blacks / range wash | process | light | — | Compress full levels into a narrower visible range. |
| `matrix_mismatch` | BT.601 / BT.709 mismatch | process | light | — | Decode with a deliberately mismatched color matrix. |
| `highlight_clip` | Clipped highlights | process | light | — | Hard clip bright values after gain. |
| `shadow_crush` | Crushed shadows | process | light | — | Lift contrast below midgray and discard shadow detail. |
| `channel_swap` | RGB / BGR swap | process | light | — | Exchange red and blue channels. |
| `posterize` | Banding / posterization | process | light | — | Quantize channel levels into visible steps. |
| `threshold` | Threshold | process | light | — | Collapse luminance to two levels. |
| `hue_rotation` | Hue rotation | process | light | — | Rotate chroma phase. |
| `invert` | Signal polarity inversion | process | light | — | Invert the picture values. |
| `color_cast` | White-balance cast | process | light | — | Bias red, green, and blue gains. |
| `saturation` | Chroma overdrive | process | light | — | Increase saturation before clipping. |
| `gamma_shift` | Gamma mismatch | process | light | — | Change the transfer curve. |
| `polaroid` | Photographic dye fade | process | light | — | Reduced saturation, warm shadows, raised black levels. |

## Geometry & sampling

| ID | Name | Fidelity | Cost | Required asset | Method |
|---|---|---|---|---|---|
| `pixelate` | Nearest-neighbor chunkiness | process | light | — | Downsample and reconstruct with nearest neighbors. |
| `aliasing` | Aliasing / moire | process | light | — | Subsample high-frequency detail without a good reconstruction filter. |
| `soft_upscale` | Upscaling softness | process | light | — | Bilinear downscale and upscale. |
| `digital_zoom` | Digital zoom blockiness | process | light | — | Crop centrally and enlarge using nearest neighbors. |
| `aspect_stretch` | Wrong aspect / stretched faces | process | light | — | Crop width and stretch back to the output raster. |
| `hard_crop` | Overscan / hard crop | process | light | — | Crop all sides then resize to the working raster. |
| `sharpen` | Oversharpening / ringing | process | light | — | Unsharp mask creates bright and dark edge halos. |
| `nr_smear` | Noise-reduction smear | process | light | — | Strong spatial and temporal denoising. |
| `fisheye` | Lens / bodycam distortion | process | light | — | Radial lens distortion. |
| `vignette` | Optical vignette | process | light | — | Smooth peripheral darkening. |

## Motion & fields

| ID | Name | Fidelity | Cost | Required asset | Method |
|---|---|---|---|---|---|
| `stutter` | Dropped / duplicated frames | model | light | — | Hold sampled frames at a strength-dependent cadence. |
| `judder` | Uneven frame pacing | model | light | — | Alternate short and long frame holds. |
| `telecine` | Bad pulldown cadence | model | light | — | Repeat fields with a 3:2 cadence at the working frame rate; cadence model. |
| `frame_blend` | Frame-conversion double images | model | light | — | Mix adjacent decoded frames. |
| `interlace` | Interlace combing | model | light | — | Weave alternate lines from consecutive frames; no decorative lines. |
| `field_order` | Wrong field order | model | light | — | Weave temporally reversed field lines. |
| `bob` | Bad deinterlace / bob shimmer | model | light | — | Double one field and alternate vertical phase. |
| `freeze` | Frozen video / live audio | model | light | — | Hold a video frame for part of each six-second cycle. |
| `timestamp_jump` | Timestamp jump appearance | model | light | — | Periodic skips and repeated pictures in a playable constant-rate file. |
| `reorder` | B-frame reorder appearance | model | light | — | Read the short history buffer out of order. |
| `loop` | Short picture loops | model | light | — | Repeat a captured one-second sequence. |
| `reverse` | Reverse bursts | model | light | — | Play the previous half-second in reverse at intervals. |
| `low_fps` | Low frame rate | model | light | — | Hold pictures at a lower rate while audio continues. |
| `time_lapse` | Time-lapse cadence | model | light | — | Sample sparse frames; preserve duration with holds. |
| `motion_gaps` | Motion-triggered CCTV gaps | model | light | — | Hold the last picture when luminance difference falls below a threshold. |
| `slit_scan` | Temporal slit-scan | model | light | — | Each horizontal band comes from a different buffered time. |
| `echo` | Temporal echo / palinopsia | model | light | — | Blend earlier pictures into the current picture. |
| `feedback` | Video feedback | model | light | — | Recursively mix the preceding output with a slight spatial shift. |
| `speed_blend` | Speed-ramp ghosting | model | light | — | Animate the mixing weight between temporal samples. |
| `noise_freeze` | Frozen grain / noise texture | model | light | — | Add a stationary noise field that does not follow scene movement. |
| `optical_flow` | Optical-flow interpolation melting | process | heavy | — | Motion-compensated interpolation at a deliberately low source cadence. Very slow on CPU. |

## Camera & optics

| ID | Name | Fidelity | Cost | Required asset | Method |
|---|---|---|---|---|---|
| `sensor_noise` | Sensor luma noise | model | light | — | Signal-dependent noise, strongest in darker regions. |
| `chroma_noise` | Chroma noise blotches | model | light | — | Low-resolution independent channel noise. |
| `fixed_pattern` | Fixed-pattern sensor noise | model | light | — | Persistent row and column gain errors. |
| `hot_pixels` | Hot / dead pixels | model | light | — | Fixed saturated and black sensor sites. |
| `heat_noise` | Heat noise build-up | model | light | — | Noise amplitude increases through a repeating slow cycle. |
| `low_light` | Low-light gain | model | light | — | Boost shadow noise with reduced shadow precision. |
| `aberration` | Radial chromatic aberration | model | light | — | Separate color-channel sampling radially. |
| `bloom` | Highlight bloom | model | light | — | Blur only over-threshold highlights into neighboring pixels. |
| `lens_smear` | Lens highlight smear | model | light | — | Spread strong highlights horizontally. |
| `flare` | Optical flare | model | light | — | Source-responsive broad glare around the brightest region. |
| `autofocus` | Autofocus hunting | model | light | — | Slowly vary blur radius. |
| `exposure_pump` | Auto-exposure pumping | model | light | — | Time-varying exposure gain. |
| `wb_pump` | White-balance hunting | model | light | — | Time-varying red/blue balance. |
| `rolling_shutter` | Rolling-shutter skew / wobble | model | light | — | Sample each row with a time-dependent horizontal displacement. |
| `shake` | Handheld camera shake | model | light | — | Smooth frame displacement with reflected edge sampling. |
| `stabilization` | Electronic stabilization warp | model | light | — | Spatially varying elastic correction. |
| `refresh_bars` | Screen refresh beating | model | light | — | Moving broad exposure bands, not a scanline overlay. |
| `pwm` | LED PWM exposure banding | model | light | — | Rolling exposure integrates periodic light intensity. |
| `night_vision` | IR / night-vision capture | model | light | — | Green luminance, amplified noise, highlight bloom. |
| `capture_loss` | Capture signal-loss flicker | model | light | — | Brief, sparse signal attenuation. |

## Tape & composite

| ID | Name | Fidelity | Cost | Required asset | Method |
|---|---|---|---|---|---|
| `chroma_bleed` | Chroma bandwidth / bleed | model | light | — | Low-pass YIQ chroma horizontally while retaining luminance. |
| `chroma_delay` | Chroma delay | model | light | — | Delay chrominance relative to luminance. |
| `composite` | Composite encode / decode | model | light | — | Modulate YIQ onto a sampled subcarrier then imperfectly separate it. Simplified signal model, not standards-accurate NTSC. |
| `dot_crawl` | Composite dot crawl | model | light | — | Leak modulated chroma into recovered luminance near transitions. |
| `cross_color` | Composite cross-color | model | light | — | Decode high-frequency luminance as false chrominance. |
| `tracking` | Tape tracking instability | model | light | — | Band-limited row displacement and noisy RF recovery. |
| `head_switch` | Head-switching disturbance | model | light | — | Bottom-of-picture timing displacement with noisy recovery. |
| `tape_dropout` | Tape RF dropouts | model | light | — | Short irregular streaks of missing recovered signal. |
| `head_clog` | Head clog / tape wrinkle | model | light | — | Occasional broad bands of poor signal-to-noise ratio. |
| `tape_chew` | Tape stretch / chewing picture | model | light | — | Slow horizontal timing collapse and recovery. |
| `hold_roll` | Vertical hold loss | model | light | — | Roll picture address vertically with time. |
| `horizontal_hold` | Horizontal sync loss | model | light | — | Line-dependent horizontal wrap from sync instability. |
| `hum_bars` | Mains hum bars | model | light | — | Slowly moving wide luma modulation. |
| `multipath` | RF multipath ghost | model | light | — | Add an attenuated horizontally delayed signal copy. |
| `convergence` | Color convergence error | model | light | — | Offset red and blue recovery horizontally. |
| `retention` | Phosphor image retention | model | light | — | Persist a dim copy of the opening picture. |
| `turn_off` | Picture collapse / turn-off dot | model | light | — | Compress the picture into a bright line then a small decaying point. |
| `degauss` | Degaussing color wobble | model | light | — | Transient radial channel displacement that decays over time. |
| `power_on` | Power-on flash | model | light | — | Brief initial exposure surge. |
| `static` | RF snow | model | light | — | Mix broadband random luminance with the recovered signal. |

## Film & print

| ID | Name | Fidelity | Cost | Required asset | Method |
|---|---|---|---|---|---|
| `film_grain` | Photochemical grain | model | light | — | Luminance-dependent, spatially correlated grain. |
| `dust` | Film dust | model | light | — | Sparse moving dark and bright dust specks. |
| `scratches` | Emulsion scratches | model | light | — | Sparse longitudinal scratches with temporal persistence. |
| `light_leak` | Film light leak | model | light | — | Soft, slowly moving warm exposure spill from a film edge. |
| `gate_weave` | Projector gate weave | model | light | — | Small independent registration errors between pictures. |
| `splice` | Splice jumps | model | light | — | Brief vertical registration jumps at intervals. |
| `emulsion` | Vinegar / nitrate / emulsion decay | model | light | — | Slowly changing blotches and local warping. |
| `projector_burn` | Film gate burn | model | light | — | Growing luminous irregular hole and brown emulsion boundary. |
| `cue_marks` | Reel-change cue marks | model | light | — | Small ring near the top-right briefly at intervals. |
| `double_exposure` | Double exposure | model | light | — | Combine the picture with a shifted earlier exposure. |
| `disc_rot` | LaserDisc sparkle / rot | model | light | — | Intermittent bright and colored read-error flecks. |

## Digital faults

| ID | Name | Fidelity | Cost | Required asset | Method |
|---|---|---|---|---|---|
| `macroblocks` | Corrupt macroblock model | model | moderate | — | Replace sparse blocks with colored or held data; decoded-picture simulation. |
| `slice_damage` | Corrupt slice model | model | moderate | — | Replace a horizontal picture slice with displaced data. |
| `zero_yuv` | Zeroed YUV appearance | model | moderate | — | Sparse green/pink decoded frames; valid final stream. |
| `concealment` | Decoder error-concealment model | model | moderate | — | Reuse old blocks over a moving scene. |
| `lost_reference` | Lost-reference trails model | model | moderate | — | Persistent shifted old texture blended into current data. |
| `wrong_stride` | Wrong row stride / wrap | model | moderate | — | Read flattened RGB picture with a changing row start offset. |
| `wrong_format` | Wrong pixel-format interpretation | model | moderate | — | Reinterpret RGB byte planes as planar channels. |
| `vram` | Failing VRAM appearance | model | moderate | — | Intermittent tile corruption and channel errors. |
| `missing_texture` | Missing-texture checkers | model | moderate | — | Replace a chosen region with magenta/black checkers. |
| `pixel_sort` | Pixel sorting | model | moderate | — | Sort horizontal runs above a luminance threshold. |
| `displacement` | Displacement map | model | moderate | — | Smooth two-dimensional procedural displacement. |
| `ordered_dither` | Ordered dither | model | moderate | — | Quantize with a Bayer threshold pattern. |
| `error_dither` | Error-diffusion palette | model | heavy | — | Floyd–Steinberg quantization; Python loop, slow at high resolution. |
| `thermal` | False-color / thermal palette | model | moderate | — | Map luminance through a synthetic heat palette; not thermal measurement. |

## Perception studies

| ID | Name | Fidelity | Cost | Required asset | Method |
|---|---|---|---|---|---|
| `scotoma` | Blind-region fill study | model | moderate | — | Fill a user-chosen region with blurred boundary color. A visual approximation, not true video inpainting. |
| `scintillating` | Scintillating arc study | model | moderate | — | Growing zigzag arc with animated color over a softened region. |
| `hemianopia` | Half-field loss study | model | moderate | — | Gradually attenuate half of the picture. |
| `metamorphopsia` | Local waviness | model | moderate | — | Sine displacement concentrated around a selected region. |
| `face_warp` | Regional face distortion | model | moderate | — | Warp a manually placed face region. No automatic face tracker or model download. |
| `akinetopsia` | Motion-blindness study | model | moderate | — | Sparse stills with residual earlier images. |
| `visual_snow` | Visual snow study | model | moderate | — | Fine noise strongest in dark tones. |
| `floaters` | Drifting floaters | model | moderate | — | Soft moving translucent filaments. |
| `phosphenes` | Phosphene pattern study | model | moderate | — | Dim moving colored light patches. |
| `local_scale` | Micropsia / macropsia region | model | moderate | — | Animate local magnification around a selected point. |
| `curtain` | Retinal curtain study | model | moderate | — | Soft dark boundary sweeps across the picture. |
| `troxler` | Peripheral fading study | model | moderate | — | Gradually suppress peripheral contrast. |
| `ganzfeld` | Uniform field / Ganzfeld study | model | moderate | — | Slowly replace spatial detail with mean field color and faint noise. |
| `tunnel` | Tunnel vision / greyout | model | moderate | — | Animated peripheral attenuation and desaturation. |
| `motion_aftereffect` | Motion adaptation pattern | model | moderate | — | Scrolling luminance pattern followed by a stationary hold. Perceived response varies. |
| `derealization` | Derealization treatment | model | moderate | — | Soft detail, subdued color, lowered contrast. |

## Codec generations

| ID | Name | Fidelity | Cost | Required asset | Method |
|---|---|---|---|---|---|
| `compression` | Blocking / mosquito noise | process | heavy | — | Low-quality H.264 encoding creates actual codec artifacts. |
| `dark_mud` | Dark macroblock mud | process | heavy | — | Crush shadows then encode at very low quality. |
| `generation_loss` | Video generation loss | process | heavy | — | Repeat lossy encoding 2–5 times. |
| `platform_rot` | Platform recompression | process | heavy | — | Alternate MPEG-4 and H.264 generations; no claim to match a particular platform. |
| `mpeg4` | MPEG-4 ASP / DivX-like | process | heavy | — | Encode and decode using MPEG-4 Part 2. |
| `flv` | FLV / Sorenson Spark | process | heavy | — | Encode and decode with the FLV1 codec. |
| `cinepak` | Cinepak | process | heavy | — | Real Cinepak encode/decode at reduced raster; very slow. |
| `h263` | 3GP / H.263 | process | heavy | — | Actual low-resolution H.263 encode/decode. |
| `gif` | GIF palette / dither | process | heavy | — | Actual indexed-color GIF encode/decode. |
| `datamosh` | I-frame removal datamosh | process | heavy | — | Encode MPEG-4 then drop subsequent I packets. Decoder-dependent; may fail on very short material. |
| `packet_loss` | Compressed packet loss | process | heavy | — | Drop selected non-key compressed packets and recover to a playable stream. |
| `bit_rot` | Compressed payload bit rot | process | heavy | — | Damage a temporary MPEG-4 bitstream, then decode. Never modifies the source. |
| `bad_sectors` | Bad-sector payload damage | process | heavy | — | Zero short MPEG-4 frame-payload chunks before recovery. |
| `databend` | Raw RGB databending | process | heavy | — | Flip bytes in the decoded raster before re-encoding. |

## Audio filters

| ID | Name | Fidelity | Cost | Required asset | Method |
|---|---|---|---|---|---|
| `lowpass` | Low-pass bandwidth loss | process | light | — | Remove upper frequencies. |
| `spectral_hole` | Spectral hole | process | light | — | Deep notch in the midrange. |
| `phone` | Telephone band limiting | process | light | — | High-pass and low-pass around voice bandwidth. |
| `radio` | Radio / walkie-talkie EQ | process | light | — | Narrow band, compressed dynamics, soft overload. |
| `tv_speaker` | Small TV speaker | process | light | — | Reduced bass and treble with a resonant midrange. |
| `mic_overload` | Microphone overload | process | light | — | Gain into soft saturation. |
| `clip` | Hard clipping | process | light | — | Gain into hard sample clipping. |
| `bitcrush` | Low bit-depth / bitcrush | process | light | — | Quantize audio amplitude. |
| `sample_reduce` | Sample-rate reduction | process | light | — | Reduce effective sample frequency without ideal reconstruction. |
| `resample` | Resampling artifacts | process | light | — | Small low-quality resampling filter. |
| `pitch` | Sample-clock pitch mismatch | process | light | — | Change playback sample clock, then preserve output duration by trimming or padding. |
| `phase` | Phase cancellation / hollow mono | process | light | — | Mix phase-inverted opposite channel into each channel. |
| `channel_drop` | Single-channel dropout | process | light | — | Remove the right channel. |
| `compressor` | Compressor pumping | process | light | — | Heavy fast compression. |
| `gate` | Noise-gate chopping | process | light | — | Aggressive threshold gate. |
| `noise_suppression` | Watery noise-suppression model | process | light | — | Strong spectral denoising; does not use a neural model. |
| `reverb` | Room / flutter echo | process | light | — | A short series of decaying taps. |
| `tape_saturation` | Tape saturation | process | light | — | Soft nonlinear saturation and high-frequency loss. |
| `formant` | Pitch / formant shift | process | light | — | Rubber Band pitch/formant processing; requires FFmpeg rubberband filter. |
| `dead_room` | Dry / dead-room approximation | process | light | — | Gate low-level room tails; cannot remove arbitrary existing reverberation. |
| `answering` | Answering-machine / microcassette | process | light | — | Narrow bandwidth, soft overload, and reduced precision. |
| `audio_reverse` | Reverse audio | process | light | — | Reverse the complete selected audio interval using disk-backed samples. |

## Audio DSP

| ID | Name | Fidelity | Cost | Required asset | Method |
|---|---|---|---|---|---|
| `hiss` | Preamp / tape hiss | model | moderate | — | Quiet broadband noise. |
| `hum` | 50 Hz mains hum | model | moderate | — | Fundamental and harmonics. |
| `hum60` | 60 Hz ground-loop hum | model | moderate | — | 60 Hz plus odd harmonics. |
| `rf_buzz` | GSM / RF buzz model | model | moderate | — | Pulse-train-modulated buzz. |
| `whine` | Power-supply whine | model | moderate | — | Quiet drifting high tone. |
| `crackle` | Vinyl / cable crackle | model | moderate | — | Sparse decaying noise impulses. |
| `audio_dropout` | Tape / interface audio dropout | model | moderate | — | Brief repeating loss of audio with small fades. |
| `underrun` | Buffer underrun | model | moderate | — | Repeat short sample blocks. |
| `voip` | VoIP packet concealment | model | moderate | — | Hold previous 20 ms packet after deterministic packet loss. |
| `wow` | Irregular tape wow | model | moderate | — | Time-varying resampling driven by slow and irregular oscillators. |
| `flutter` | Tape flutter | model | moderate | — | Fast low-amplitude sample-clock modulation. |
| `clock_jitter` | Clock jitter / drift | model | moderate | — | Irregular microscopic sample-time offsets. |
| `tape_stretch` | Tape stretch / pitch sag | model | moderate | — | Slow time-delay growth and recovery. |
| `sticky_shed` | Sticky-shed squeal | model | moderate | — | Intermittent chirping friction tone and signal loss. |
| `print_through` | Magnetic print-through | model | moderate | — | Quiet forward copy of future audio appears 0.7 seconds early. |
| `locked_groove` | Vinyl locked groove | model | moderate | — | Repeat a half-second sample fragment. |
| `groove_skip` | Vinyl groove skip | model | moderate | — | Periodically replay a recent phrase. |
| `granular` | Granular stutter | model | moderate | — | Reorder and window short grains. |
| `ring_mod` | Ring modulation | model | moderate | — | Multiply samples by a sinusoid. |
| `shepard` | Shepard rising tone | model | moderate | — | Octave-spaced sinusoids with a moving spectral envelope. |
| `missing_fundamental` | Missing-fundamental tone | model | moderate | — | Synthesize harmonics while omitting their common fundamental. |
| `diplacusis` | Different pitch per ear | model | moderate | — | Independent small periodic sample-time shift per channel. |
| `tinnitus` | Tinnitus tone study | model | moderate | — | Low-level 6 kHz sinusoid; no claim about medical perception. |
| `flyback` | CRT flyback whine | model | moderate | — | Low-level 15.7 kHz tone. |
| `infrasound` | 19 Hz sub-bass | model | moderate | — | Quiet 19 Hz tone. No claim that it induces fear; most laptop speakers cannot reproduce it. |
| `mosquito` | 17 kHz tone | model | moderate | — | Low-level 17 kHz sinusoid. |
| `test_tone` | 1 kHz test tone | model | moderate | — | Quiet test sinusoid. |
| `alert_tone` | Dual-frequency alert tone | model | moderate | — | 853/960 Hz attention-tone pair; not a full encoded EAS message. |
| `dtmf` | DTMF dialing | model | moderate | — | Deterministic sequence of dual-tone digits. |
| `uvb76` | Shortwave buzzer model | model | moderate | — | Gated 462 Hz buzz with harmonics. |
| `duga` | Shortwave woodpecker model | model | moderate | — | 10 Hz short pulse train. |
| `pirate` | Shortwave fading / heterodyne | model | moderate | — | Slow fading plus drifting interfering carrier. |
| `dead_air` | Dead-air gaps | model | moderate | — | Suppress sound during part of each cycle. |
| `heartbeat` | Heartbeat synthesis | model | moderate | — | Pairs of damped low-frequency pulses. |
| `breathing` | Breathing synthesis | model | moderate | — | Slowly amplitude-modulated filtered noise; procedural model. |
| `auditory_exclusion` | Tunnel hearing study | model | moderate | — | Attenuate the source and introduce quiet ringing. |
| `hyperacusis` | Transient emphasis study | model | moderate | — | Emphasize short transients inside the final peak ceiling. |
| `sidechain` | Sidechain-like pumping | model | moderate | — | Periodic control envelope ducks the audio. |
| `wrong_audio_format` | Wrong audio endianness | model | moderate | — | Swap bytes in 16-bit samples, then attenuate. |
| `wrong_interleave` | Wrong channel interleave | model | moderate | — | Interpret adjacent stereo samples as misplaced channel blocks. |
| `power_click` | Power-on click / thump | model | moderate | — | Short decaying low pulse and noise transient. |
| `convolution` | Impulse-response convolution | process | heavy | audio | Convolve source with supplied WAV impulse response; capped at 10 seconds. |
| `vocoder` | Vocoder with carrier | process | heavy | audio | 16-band envelope vocoder using supplied carrier audio. |

## Audio codec generations

| ID | Name | Fidelity | Cost | Required asset | Method |
|---|---|---|---|---|---|
| `aac_rot` | AAC pre-echo / swirl | process | heavy | — | Low-bitrate AAC encode/decode. |
| `mp3_rot` | MP3 birdies / pre-echo | process | heavy | — | Low-bitrate MP3 encode/decode. |
| `opus_rot` | Opus metallic warble | process | heavy | — | Low-bitrate Opus encode/decode. |
| `joint_stereo` | Joint-stereo compression | process | heavy | — | MP3 joint-stereo at low bitrate. |
| `gsm` | GSM speech codec | process | heavy | — | Real mono 8 kHz GSM encode/decode. |
| `mulaw` | G.711 mu-law | process | heavy | — | Real 8 kHz mu-law companding. |
| `codec2` | Codec2 speech codec | process | heavy | — | Real Codec2 encode/decode when installed in FFmpeg. |
| `sbc` | Bluetooth SBC codec | process | heavy | — | Actual SBC encode/decode; no transport latency simulation. |
| `audio_generations` | Audio generation loss | process | heavy | — | Repeat MP3 encoding three times. |

## Authored picture techniques

| ID | Name | Fidelity | Cost | Required asset | Method |
|---|---|---|---|---|---|
| `intrusion` | Broadcast signal intrusion | authored | moderate | video | Cut to supplied intrusion footage during the selected time window. |
| `sign_off` | Dead channel / sign-off sequence | authored | moderate | video | Insert an authored sign-off/test-card sequence. |
| `charles_bonnet` | Faint non-interacting figures | authored | moderate | video | Blend supplied figure footage into a selected region. |
| `being_watched` | Being-watched background figure | authored | moderate | video | Place supplied figure footage quietly in a chosen region. |
| `pareidolia` | Pareidolia in shadows | authored | moderate | video | Blend supplied ambiguous shapes into dark regions. |
| `inattentional` | Unemphasized background figure | authored | moderate | video | Composite a supplied peripheral figure. |
| `change_blindness` | Change-blindness replacement | authored | moderate | video | Replace a chosen interval with an authored changed scene. |
| `capgras` | Familiar scene / altered detail | authored | moderate | video | Use a supplied altered version of the scene. |
| `dream_logic` | Dreamlike inconsistent geometry | authored | moderate | video | Insert an authored altered room/text/clock sequence. |
| `uncanny` | Uncanny human performance | authored | moderate | video | Use supplied nearly-human acting, animation, or processed footage. |
| `liminal` | Liminal environment | authored | moderate | video | Use an authored empty-space shot. |
| `hypnagogic` | Sleep-paralysis framing | authored | moderate | video | Place a supplied shadow figure in a chosen region. |
| `local_access` | Overnight local-access treatment | authored | moderate | video | Use supplied staged local-access footage. |
| `lost_media` | Lost-media framing | authored | moderate | video | Insert an authored slate or opening sequence. |
| `binocular` | Competing scene blend | authored | moderate | video | Alternate source and supplied second scene. |
| `single_insert` | Single-frame insert | authored | moderate | video | Insert one supplied frame at the start of the selected time window. |
| `game_glitch` | Engine glitches / T-poses | authored | moderate | video | Use captured engine footage; cannot derive a 3D skeleton from arbitrary video. |
| `ai_hallucination` | AI upscale hallucinations | authored | moderate | video | Insert externally processed model output. No weights downloaded by Signalbox. |
| `segmentation` | Video-call mask / face warping | authored | moderate | video | Insert supplied segmentation or beauty-filter output. |
| `motion_vectors` | Motion-vector hijacking | authored | moderate | video | Insert externally processed motion-vector output; not mislabeled as local vector editing. |
| `indeo` | Indeo legacy codec footage | authored | moderate | video | Use externally encoded footage: standard FFmpeg has no Indeo encoder. |
| `realvideo` | RealVideo legacy footage | authored | moderate | video | Insert an externally encoded RealVideo round trip. |
| `teletext` | Authored teletext mosaic | authored | moderate | video | Supply rendered teletext pages or video; no automatic font download. |
| `caption_errors` | Authored caption errors | authored | moderate | video | Supply a composited caption-error sequence. |

## Authored audio techniques

| ID | Name | Fidelity | Cost | Required asset | Method |
|---|---|---|---|---|---|
| `crosstalk` | Telephone crosstalk | authored | light | audio | Mix supplied speech quietly beneath the source. |
| `numbers` | Numbers-station transmission | authored | light | audio | Mix supplied spoken-number recording. |
| `weather_voice` | Weather-radio synthetic voice | authored | light | audio | Mix a supplied synthesized voice file. |
| `public_information` | Civil-defense tone clash | authored | light | audio | Mix a supplied narrator performance. |
| `training` | Training-tape narration | authored | light | audio | Mix a supplied instructional voice recording. |
| `evp` | Near-threshold / backward whispers | authored | light | audio | Mix reversed supplied speech near the noise floor. |
| `musical_ear` | Faint phantom melody | authored | light | audio | Mix supplied music quietly under the original. |
| `dialup` | Dial-up modem handshake | authored | light | audio | Mix a supplied handshake recording for authentic protocol behavior. |
| `sstv` | SSTV transmission | authored | light | audio | Mix a supplied encoded SSTV audio file. |
| `spectrogram` | Spectrogram-hidden image audio | authored | light | audio | Mix supplied audio with an encoded spectrogram image. |
| `sine_speech` | Sine-wave speech | authored | light | audio | Mix supplied formant-tracked sine-wave speech. |
| `paulstretch` | Paulstretch / extreme stretch | authored | light | audio | Mix supplied phase-randomized stretched audio. |
| `hrtf` | HRTF binaural placement | authored | light | audio | Mix supplied binaurally rendered audio; stereo panning is not HRTF. |
| `asmr` | Close-mic body / room sound | authored | light | audio | Mix supplied close-mic recording. |
| `dread_absence` | Silence then a sound | authored | light | audio | Mute original in the selected interval and play supplied sound at its start. |
| `amr` | AMR speech codec recording | authored | light | audio | Use externally encoded AMR audio when no local encoder exists. |

## Container behavior

| ID | Name | Fidelity | Cost | Required asset | Method |
|---|---|---|---|---|---|
| `av_offset` | Audio/video offset | process | light | — | Delay audio by up to two seconds in the final mix. |
| `av_drift` | Audio/video clock drift | process | light | — | Progressively resample audio so it drifts against the picture. |
| `track_mismatch` | Mismatched track lengths | process | light | — | Shorten audio while keeping the complete video. |
| `aspect_flag` | Wrong display aspect flag | process | light | — | Write a deliberately different display aspect ratio into the final container. |
