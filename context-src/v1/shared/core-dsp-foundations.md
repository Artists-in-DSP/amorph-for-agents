## C) MUSICAL PARAMETERS AND CMAJOR 1.0.3175 DSP FOUNDATIONS

Use safe host values and DSP conversions. Do not invent annotations or replace a
meaningful midpoint with a linear dial. `select(mask, a, b)` is Vector-only masked selection. For scalar values use `cond ? a : b`. Cast math results into `float` state.

### Parameter semantics

| Meaning | Host declaration | DSP use |
|---|---|---|
| Cutoff/frequency | Hz; use `mid` for a requested centre or a range over two octaves | Smooth Hz; clamp to `0..0.45 * sampleRate` before coefficient updates |
| Gain/trim/output | dB; linear dial position | Smooth, then `std::levels::dBtoGain`; `0 dB` = gain `1.0` |
| Time | `ms` or `s`; useful `mid` | Clamp above zero; convert once to seconds, frames, or coefficient |
| Resonance | true Q, or labelled normalised `0..1` | TPT SVF takes true Q; never feed it a normalised amount |
| Mix | `0..100 %` or `0..1` | Clamp; use linear only for intended level interaction, otherwise equal-power |
| Pan | bipolar `-1..1` | `std::pan_law::centre3dB` |
| Pitch | semitones/cents | Ratio `2 ** (semitones / 12)`; never add Hz |

`mid` maps control position, not event value; `init` sets startup value. Never emit `skew`: it is not the Amorph parameter contract.

Example requested as "0 to 20 kHz, 1 kHz in the middle and initially 1 kHz":

    input event float param1 [[ name: "Cutoff", min: 0.0, max: 20000.0,
                                mid: 1000.0, init: 1000.0, unit: "Hz" ]];

For a dB control, keep the parameter in dB and convert it explicitly:

    input event float param2 [[ name: "Output", min: -24.0, max: 6.0,
                                init: 0.0, unit: "dB" ]];
    float outputDb = 0.0f;
    event param2 (float v) { outputDb = clamp (v, -24.0f, 6.0f); }
    // audio loop: float outputGain = float (std::levels::dBtoGain (outputDb));

### Prefer verified standard-library primitives

Cmajor `1.0.3175` is authoritative. Use `std::filters (float<2>)::tpt::svf::Processor` as a graph node or an `Implementation` for custom/per-voice state. State belongs at processor scope; call `create` once at `main()` start where `processor.frequency` is live:

    std::filters (float)::tpt::svf::Implementation filter;
    void main()
    {
        filter = std::filters (float)::tpt::svf::create (
            std::filters (float)::tpt::svf::Mode::lowPass,
            processor.frequency, 1000.0, 0.707);
        loop { /* process one sample, then advance() */ }
    }

    // Recalculate at control rate or after smoothed values change:
    filter.setFrequency (processor.frequency, float64 (safeCutoff), float64 (safeQ));
    float filtered = filter.process (sample);

SVF Q is true Q and must exceed zero. Map a friendly `0..1` Resonance explicitly:

    float r = clamp (resonanceAmount, 0.0f, 1.0f);
    float safeQ = 0.5f + r * r * 11.5f;  // 0.5 .. 12.0 true Q

Use `std::oscillators::PolyblepState` per voice: set with `osc.setFrequency (processor.frequency, float64 (frequencyHz));`; call `nextSawtooth()`, `nextSquare()`, `nextTriangle()`, or `nextSine()`.

For a manual oscillator use one unit. Prefer cycles `[0, 1)`: add `frequencyHz * float (processor.period)`, wrap at `1.0`, then call `sin (float64 (twoPi * phase))`. Calling `sin (phase)` on a cycles phase is wrong by `twoPi`. Radians instead add `twoPi * frequencyHz * dt` and wrap at `twoPi`.

Hard audit: returned source must contain zero occurrences of `processor.currentTime`, `Math.`, `uint`, or `unsigned`. Cmajor supplies `pi`/`twoPi`; never declare a local named `twoPi`. Processor properties here are `frequency`, `period`, `id`, `session`. For time, own processor-scope `float64 phase`; in `main()` use `phase += float64 (frequencyHz * float (processor.period))`, wrap at `1.0`, then `sin (float64 (twoPi) * phase)`.

`external` is host-supplied and cannot be initialised: `external int voiceCount = 8;` is invalid. Use `const int voiceCount = 8;` internally, or mutable `int voiceCount = 8;`.

For noise declare processor-scope `std::random::RNG rng;`, seed once before the loop with `rng.seed (int64 (processor.session));`, then use `rng.getBipolar()`/`rng.getUnipolar()`. Floating-point `%` is invalid; use `fmod`/`remainder`.

### Musical modulation, envelopes, and smoothing

Filter envelope/LFO modulation should be proportional in pitch space so its
musical depth is consistent across the cutoff range:

    float octaveOffset = envAmountOctaves * envelopeValue + lfoAmountOctaves * lfoValue;
    float modulatedHz = cutoffHz * float (pow (2.0, float64 (octaveOffset)));
    float safeCutoff = clamp (modulatedHz, 0.0f, float (processor.frequency) * 0.45f);

For adjustable attack/decay/release, calculate sample-rate
independent coefficients from positive time; never use fixed per-sample decay or
divide by zero:

    float seconds = max (0.001f, timeMs * 0.001f);
    float coefficient = 1.0f - float (exp (-1.0 / float64 (seconds * float (processor.frequency))));
    envelope += coefficient * (target - envelope);

Smooth cutoff, gain, mix, pan, drive, delay time, and feedback. Event handlers
set targets; the audio loop advances `std::smoothing::SmoothedValue` or an
equivalent bounded ramp/one-pole.

### Architecture recipes

Use these recipes without overriding requested behaviour:

- **Subtractive synth:** note -> per-voice `PolyblepState` -> pitch-space
  envelope/LFO modulation -> TPT low-pass with bounded true Q -> amplitude
  envelope -> active-voice normalisation. Each voice owns all state.
- **Kick/tom:** trigger resets an amplitude envelope and a faster positive pitch
  envelope; sine falls to the tuned fundamental. Optional click/noise decays
  separately. Coefficients are sample-rate independent. For a conventional GM
  kick, verify the settled body is normally `40..100 Hz`.
- **Snare/hat:** bounded tone plus filtered noise with separate decays, DC/rumble
  filtering, headroom, and no pre-trigger leakage. Conventional output retains
  substantial bright/noise energy.
- **Reverb:** unequal delays, damped feedback, all-pass/comb diffusion, and
  cross-coupled stereo below unity. One feedback delay is an echo. An impulse must
  yield multiple arrivals, distinct stereo wet output, and a finite decaying tail.
  A Schroeder all-pass stage requires a delay buffer and uses this recurrence
  (repeat it with separate buffers, indices, and unequal lengths for each stage):

      float delayed = apBuffer.at (apIndex);
      float allpassOut = delayed - coefficient * stageIn;
      apBuffer.at (apIndex) = stageIn + coefficient * allpassOut;
      apIndex = (apIndex + 1) % allpassLength;

  Keep `abs (coefficient) < 1.0f` and make `allpassLength` a positive compile-time
  constant. A scalar previous-sample variable is not a reverb all-pass stage.
  Reject algebraically cancelling expressions such as `-g * x + state + g * x`.
- **Delay/chorus:** preserve dry stereo, interpolate fractional reads, smooth time,
  and use distinct/cross-coupled L/R trajectories. Never resize buffers at runtime.
- **Modal/physical resonator:** use inharmonic modes with unequal,
  frequency-dependent damping; a harmonic comb bank is not a convincing material.
  Bound each complete delay-write feedback row: after decay,
  `sum(abs(self and cross weights)) <= 0.98`. A safe pattern is
  `fb1 = decayGain * (0.94f * own1 + 0.02f * other)`; by contrast,
  `0.997f * own + 0.018f * other` is unsafe. Do not put `tanh` or a clamp
  inside the loop to excuse an over-unity row; first prove the un-clamped tail
  decays. Modal/comb/nonlinear wet paths can retain DC. DC-block each final wet
  channel before dry/wet mixing, with independent state per channel:

      float dcSafeL = wetL - previousWetL + dcStateL * 0.995f;
      float dcSafeR = wetR - previousWetR + dcStateR * 0.995f;
      previousWetL = wetL; previousWetR = wetR;
      dcStateL = dcSafeL; dcStateR = dcSafeR;

  Probe impulse and zero-mean noise at default and extreme damping/brightness.
  Require an un-clamped finite decaying response, no clipping, and measured
  `abs(wet-output DC offset) < 0.01`; compile and non-silence are insufficient.
- **Dynamics:** smooth a rectified/RMS envelope; compute gain reduction in dB and
  convert once with `dBtoGain`. Above-threshold input must show measurable dB gain reduction
  versus bypass; moving parameters is not proof of compression.

### Mixing, output, and delay safety

For equal-power dry/wet, use a `0..1` position:

    float theta = clamp (mix, 0.0f, 1.0f) * float (pi) * 0.5f;
    float dryGain = float (cos (float64 (theta)));
    float wetGain = float (sin (float64 (theta)));
    float mixed = dry * dryGain + wet * wetGain;

For pan, the function returns a `float<2>` pair; index it, never invent `.left`
or `.right` members:

    float<2> panGains = std::pan_law::centre3dB (clamp (pan, -1.0f, 1.0f));
    float left = sample * panGains[0];
    float right = sample * panGains[1];

Keep feedback below `1.0`; use fixed buffers, bounded interpolated reads, and safely wrapped indices. Instruments
divide a variable sum by `float(max(1, activeVoiceCount))` and retain headroom.

Budget fixed delay state across the processor. A multi-stage reverb normally keeps
the sum near or below `131072` floats (for example `16 * 8192`) and sizes each
stage for its maximum. If requested delay needs more, reduce the number of large
arrays. Copying `65536` into every comb/all-pass can cause a host compile stall.

Final audit: intended control meaning; finite coefficients; stereo integrity;
`0 dB` unity; audible, unclipped defaults. Compilation and non-silence are necessary, not sufficient:
probe requested extremes and category behaviour.
