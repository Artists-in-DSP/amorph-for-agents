## C) MUSICAL PARAMETERS AND CMAJOR 1.0.3175 DSP FOUNDATIONS

These rules describe the raw value received by DSP, the control mapping shown by
Amorph, and the safe conversion into signal-processing space. Do not invent
annotation properties or substitute a generic linear dial when the requested
control has a meaningful midpoint.

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

`mid` is the Cmajor/Amorph nonlinear control midpoint. It changes the mapping
between control position and the declared raw range; it does not transform the
raw value delivered to the event handler. `init` is independent and remains the
startup raw value. Never emit `skew`: it is not the Amorph parameter contract.

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

The bundled authority is Cmajor `1.0.3175`. `std::filters` is a parameterised
namespace, so specialise its frame type. For a graph node use
`std::filters (float<2>)::tpt::svf::Processor`; for per-voice or custom processor
state use an `Implementation`. Declare the state at processor scope, then call
`create` once at the start of `main`, where `processor.frequency` is live:

    std::filters (float)::tpt::svf::Implementation filter;
    void main()
    {
        filter = std::filters (float)::tpt::svf::create (
            std::filters (float)::tpt::svf::Mode::lowPass,
            processor.frequency, 1000.0, 0.707);
        loop
        {
            // process one sample, then advance()
        }
    }

    // Recalculate at control rate or after smoothed values change:
    filter.setFrequency (processor.frequency, float64 (safeCutoff), float64 (safeQ));
    float filtered = filter.process (sample);

The SVF Q argument is true Q and must be greater than zero. When the user asks
for a friendly `0..1` Resonance control, use an explicit bounded mapping such as:

    float r = clamp (resonanceAmount, 0.0f, 1.0f);
    float safeQ = 0.5f + r * r * 11.5f;  // 0.5 .. 12.0 true Q

Use `std::oscillators::PolyblepState` per voice for saw/square oscillators rather
than a naive phase ramp. Set its frequency with the current sample rate, then use
`nextSawtooth()`, `nextSquare()`, `nextTriangle()`, or `nextSine()`.

### Musical modulation, envelopes, and smoothing

Filter envelope/LFO modulation should be proportional in pitch space so its
musical depth is consistent across the cutoff range:

    float octaveOffset = envAmountOctaves * envelopeValue + lfoAmountOctaves * lfoValue;
    float modulatedHz = cutoffHz * float (pow (2.0, float64 (octaveOffset)));
    float safeCutoff = clamp (modulatedHz, 0.0f, float (processor.frequency) * 0.45f);

For continuously adjustable attack, decay, or release, calculate sample-rate
independent coefficients from a strictly positive time. Do not subtract a fixed
amount per sample and do not divide by a zero-millisecond parameter:

    float seconds = max (0.001f, timeMs * 0.001f);
    float coefficient = 1.0f - float (exp (-1.0 / float64 (seconds * float (processor.frequency))));
    envelope += coefficient * (target - envelope);

Smooth cutoff, gain, mix, pan, drive, delay time, and feedback targets. Use
`std::smoothing::SmoothedValue` when it fits, or an equivalent bounded ramp/one-pole.
Event handlers update targets; the audio loop advances the smoother.

### Architecture recipes

Use these signal-flow recipes as starting points, not as permission to ignore the
user's requested behaviour:

- **Subtractive synth:** note pitch -> per-voice `PolyblepState` oscillator ->
  pitch-space envelope/LFO cutoff modulation -> TPT low-pass with bounded true Q
  -> amplitude envelope -> active-voice normalisation. Each allocated voice owns
  its oscillator, filter, envelope, note, and gate state.
- **Kick/tom:** trigger resets an amplitude envelope and a faster positive pitch
  envelope; a sine body starts above the tuned fundamental and falls to it. Add a
  separately decaying click/noise transient only when requested. Decay coefficients
  are sample-rate independent; never decrement envelopes by a fixed sample amount.
- **Snare/hat:** combine a bounded tonal component with filtered noise. Give body
  and noise separate decay constants, high-pass unwanted DC/rumble, and retain
  output headroom. A trigger resets state; continuous noise must not leak before it.
- **Reverb:** use multiple unequal delay lengths, damp feedback paths, and diffuse
  with all-pass/comb stages; cross-couple stereo paths without collapsing them to
  mono. Clamp feedback below unity and delay reads inside fixed buffers. A single
  feedback delay is an echo, not a convincing reverb.
- **Delay/chorus:** preserve dry stereo, interpolate fractional read positions,
  smooth time modulation, and use different/cross-coupled L/R trajectories when
  width is requested. Never resize a delay buffer at runtime.
- **Dynamics:** measure a rectified or RMS envelope, smooth attack and release,
  compute gain reduction consistently in dB, convert once with `dBtoGain`, and
  avoid subtracting dB values from a linear multiplier.

### Mixing, output, and delay safety

For equal-power dry/wet mixing, use a `0..1` mix position:

    float theta = clamp (mix, 0.0f, 1.0f) * float (pi) * 0.5f;
    float dryGain = float (cos (float64 (theta)));
    float wetGain = float (sin (float64 (theta)));
    float mixed = dry * dryGain + wet * wetGain;

For pan, `float<2> gains = std::pan_law::centre3dB (clamp (pan, -1.0f, 1.0f));`.
Keep feedback magnitude below `1.0`, keep delay buffers fixed-size, clamp every
read delay to the allocated range, and interpolate fractional reads. Instruments
must divide a variable voice sum by `float(max(1, activeVoiceCount))`, retain
headroom, and apply only a bounded final saturator if requested.

Before returning code, audit the complete default signal path: parameters must
have the intended control meaning, coefficient updates must stay finite, stereo
must remain stereo, `0 dB` must be unity, and the default output must be audible
without clipping.
