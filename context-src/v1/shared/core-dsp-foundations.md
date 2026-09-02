## C) MUSICAL PARAMETERS AND CMAJOR 1.0.3175 DSP FOUNDATIONS

These rules cover host values, Amorph control mapping, and safe DSP conversion.
Do not invent annotations or replace a meaningful midpoint with a linear dial.

Language traps still apply: `select(mask, a, b)` is Vector-only masked selection;
scalar arguments fail. For scalar values use `cond ? a : b`. Built-in math
returns `float64` where documented; cast explicitly into `float` signal state.

### Parameter semantics

| Meaning | Host declaration | DSP use |
|---|---|---|
| Cutoff/frequency | Hz; use `mid` when the user requests a centre position or the range spans more than roughly two octaves | Smooth the raw Hz value; clamp to `0..0.45 * sampleRate` before filter coefficient updates |
| Gain/trim/output | dB; movement is normally linear in dB, so do not add frequency-style curvature | Smooth in dB or linear gain, then use `std::levels::dBtoGain`; `0 dB` must produce gain `1.0` |
| Time | `ms` or `s`; use `mid` for a useful musical centre | Clamp above zero before division, then convert once to seconds, frames, or a coefficient |
| Resonance | Either true Q or a clearly labelled normalised `0..1` amount | TPT SVF receives true Q; never pass a normalised amount directly as Q |
| Mix | `0..100 %` or `0..1` | Clamp, then choose linear crossfade only when level interaction is intended; otherwise use equal-power dry/wet gains |
| Pan | bipolar `-1..1` | Prefer `std::pan_law::centre3dB` |
| Pitch | semitones or cents | Convert ratios with `2 ** (semitones / 12)`; do not add Hz for musical transposition |

`mid` changes the control-position mapping, not the raw event value. `init`
independently sets the startup raw value. Never emit `skew`: it is not the
Amorph parameter contract.

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

The authority is Cmajor `1.0.3175`. Specialise the `std::filters` frame type:
use `std::filters (float<2>)::tpt::svf::Processor` as a graph node or an
`Implementation` for custom/per-voice state. Declare state at processor scope;
call `create` once at the start of `main`, where `processor.frequency` is live:

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

Use `std::oscillators::PolyblepState` per voice instead of a naive saw/square
ramp. Set its frequency, then call its `nextSawtooth()`, `nextSquare()`,
`nextTriangle()`, or `nextSine()`.

For a manual oscillator, use one unit consistently. Prefer cycles `[0, 1)`:
add `frequencyHz * float (processor.period)`, wrap at `1.0`, then evaluate
`sin (float64 (twoPi * phase))`. Calling `sin (phase)` on a cycles phase is wrong
by `twoPi`. Radians instead add `twoPi * frequencyHz * dt` and wrap at `twoPi`.

`processor.currentTime` does not exist in Cmajor `1.0.3175`. For elapsed time,
own and advance a `float64` phase or sample counter in `main()`. For noise,
prefer a processor-scope `std::random::RNG rng`, seed it once at the start of
`main()` with `processor.id` or `processor.session`, and call
`rng.getBipolar()` or `rng.getUnipolar()`. Do not fake noise with floating-point
`%`; `fmod(x, y)` or `remainder(x, y)` is required for floating remainders.

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
- **Delay/chorus:** preserve dry stereo, interpolate fractional reads, smooth time,
  and use distinct/cross-coupled L/R trajectories. Never resize buffers at runtime.
- **Dynamics:** smooth a rectified/RMS envelope; compute gain reduction in dB and
  convert once with `dBtoGain`. Above-threshold input must show measurable dB gain reduction
  versus bypass; moving parameters is not proof of compression.

### Mixing, output, and delay safety

For equal-power dry/wet, use a `0..1` position:

    float theta = clamp (mix, 0.0f, 1.0f) * float (pi) * 0.5f;
    float dryGain = float (cos (float64 (theta)));
    float wetGain = float (sin (float64 (theta)));
    float mixed = dry * dryGain + wet * wetGain;

For pan use `std::pan_law::centre3dB`. Keep feedback below `1.0`; use fixed
buffers, bounded interpolated reads, and safely wrapped indices. Instruments
divide a variable sum by `float(max(1, activeVoiceCount))` and retain headroom.

Budget fixed delay state across the processor. A multi-stage reverb normally keeps
the sum near or below `131072` floats (for example `16 * 8192`) and sizes each
stage for its maximum. If requested delay needs more, reduce the number of large
arrays. Copying `65536` into every comb/all-pass can cause a host compile stall.

Final audit: intended control meaning; finite coefficients; stereo integrity;
`0 dB` unity; audible, unclipped defaults. Compilation and non-silence are necessary, not sufficient:
probe requested extremes and category behaviour.
