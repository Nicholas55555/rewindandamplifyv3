# Scientific presentation videos

For the **11 November 2026 presentation revision**, these remain conceptual fallbacks. The frequency video illustrates reference ambiguity, and the amplification video depicts the earlier two-bin optical model. Current unknown-onset sensing, changing-drive, phase-inspection and three-bin circuit results appear in the revised slides and the app's **Current research** chapter. Do not narrate the older video values as those newer experiments.

Use the **MP4 videos** for playback. Both are **12 seconds**, **1200 × 676**, H.264 Constrained Baseline with `yuv420p`, 20 frames per second and no audio. The MP4 metadata precedes the video data (`faststart`) so browsers can begin playback without downloading the whole file. These are explanatory diagrams, not laboratory footage.

- [Laser diagnostic lenses](laser-diagnostic-lenses.mp4)
- [Rewind and amplify: separate two-bin optical model](rewind-amplify.mp4)

The conversion preserves the original GIF frames and their timing. It adds **one background row at the bottom** because H.264 `yuv420p` requires even dimensions: the original 1200 × 675 content is neither cropped nor scaled. The codec is lossy, so pixels can change slightly while the diagram, text and scientific values remain the same. Matching PNGs remain available as static fallbacks. The original GIFs are retained as source files; the application should present the MP4s with playback controls.

## Content

- **laser-diagnostic-lenses.mp4:** three four-second scenes. A source with constant power moves from zero frequency offset to +5 Hz; then an atomic reference also moves +5 Hz and becomes unable to distinguish the source change. The coherent reference stays fixed in this example. This illustrates complementary observables and reference ambiguity, rather than benchmarking sensing advantage. Readout probability follows the instantaneous-pulse Ramsey limit with 20 ms dark time, T2 = 0.2 s and asymmetric 2%/4% readout errors. The +5 Hz scene is deliberately larger than the separate benchmark's ±0.5 Hz change.
- **rewind-amplify.mp4:** four three-second scenes describe preparation, marking, reversal and amplification. Before/final history probabilities are copied from `qrsm_photon_poc/generated/two_bin_double.json`. The plots explicitly do not depict intermediate inverse-circuit states. The retained approximate two-bin model's selected-event probability changes from 0.1726398% to 1.5466138% in one ideal Qiskit amplification round. This is the **separate two-bin optical-model extension**, not the original step-three QRSM query or IBM hardware result. These are simulated photon-model histories, not a photonic device recording.

Use the PNGs for static slides and reduced-motion presentation. Start the videos deliberately with their player controls. Show the hardware evidence separately, because neither video displays the IBM measurement record.

## Convert and verify the MP4 files

With Python, Pillow, NumPy and either an installed FFmpeg or `imageio-ffmpeg`:

```powershell
python -m pip install Pillow numpy imageio-ffmpeg==0.8.1
python animations/convert_videos.py --overwrite
python animations/convert_videos.py --verify-only
```

The converter first looks for FFmpeg on `PATH`, then uses the `imageio-ffmpeg` packaged executable. An explicit binary can be selected with `--ffmpeg C:/path/to/ffmpeg.exe`. The performed conversion used FFmpeg 9.0.2 from imageio-ffmpeg 0.8.1 in the existing audit environment.

`video_manifest.json` records source/video SHA-256 hashes, codec, dimensions, duration, frame rate, file size and MP4 box offsets. `video_validation.json` records successful decoding of **all 240 frames per video**, frame-by-frame comparison against the original timed GIF content, and checks of **all three sensor scenes and all four quantum scenes**. Selected decoded PNGs and a contact sheet are in `video-validation/`. These checks verify media integrity and content retention; browser playback is a separate application check.

The original GIF files are never overwritten by the converter. It refuses to replace existing MP4s unless `--overwrite` is given. `--verify-only` checks existing MP4s without encoding them again.

## Regenerate the original diagram sources

Regenerate the archival GIF and static PNG sources with Python and Pillow:

```powershell
python animations/build_animations.py
```

The generator uses Windows Segoe UI fonts and the local archived Qiskit JSON. `animation_manifest.json` records the probability source and sensing parameters. No network, image generation service or random illustrative data is used.
