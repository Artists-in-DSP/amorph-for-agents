## AMORPH HOST TRANSPORT AND DAW SYNC

Apply this section only when the request mentions DAW/host/Ableton sync,
tempo-synchronised drums, arps, sequencers, delays, LFOs, or modulation. Declare:

    input event float transportIn;

Amorph does not populate `std::timeline::*`. It sends six floats at each audio
block start in this exact repeating order: **play, bpm, numerator, denominator,
ppq, barStart**. Parse them with `transportSlot = (transportSlot + 1) % 6`.
Store play as `bool`, BPM clamped to `20..999`, numerator/denominator as integers
at least 1, and both PPQ values as `float64`, assigned directly with
`currentPpq = float64 (value);` and `hostBarStartPpq = float64 (value);`.

Keep `int lastStepIndex = -1`. Between packets advance PPQ only while playing by
`float64 (hostBpm) / 60.0 / processor.frequency`; stopped transport emits no
clocked triggers and resets the latch. Reset the latch only on play-state,
time-signature, or division changes. Do not reset it from either PPQ/barStart
delta alone, exact inequality, value decrease, or a fixed error threshold:
rounding, a normal `barStart` advance, a BPM change, and an in-step seek must not
retrigger at the DAW buffer rate. Never use `max(localPpq, hostPpq)` or a
soft-lag lock.

Quarter-note lengths: sixteenth `0.25`, eighth-triplet `1/3`, eighth `0.5`,
quarter-triplet `2/3`, quarter `1`, half `2`, whole `4`, and one bar
`numerator * 4 / denominator`. A Rate/Division/Sync control is a stepped integer
selector with named labels such as
`text: "1/16|1/8T|1/8|1/4T|1/4|1/2|1/1|1 bar"`, never arbitrary values such as
`0.121413`. Put the mapping in `getDivisionQuarterNotes()`.

For arps, drums, and sequencers compute the global step with
`floor (currentPpq / max (0.0001f, getDivisionQuarterNotes()))` and trigger only
when that value differs from `lastStepIndex`. Use that global step as the trigger
latch even for `1 bar`. A separate bar-relative index may select a pattern step,
but cannot be the sole latch. A BPM oscillator or sample counter is not
phase-locked. A musical arpeggiator must articulate bounded note gates and keep
physically held notes separate from sounding step voices.

For tempo-synchronised delay, LFO, or envelope DSP use
`periodSeconds = divisionQuarterNotes * 60.0f / max (20.0f, hostBpm)`. Apply a
valid host BPM immediately whether playing or stopped; play gates new triggers,
not delay tails. Fixed seconds, `delayTimeParam * 0.25f`, or code without
`hostBpm` is **not BPM sync**.

**Buffer-size audit:** identical MIDI/transport must produce identical grid
samples at 31, 64, 257, and 511 frame buffers. Block-boundary retriggers are not
sync.
