## AMORPH HOST TRANSPORT AND DAW SYNC

This is an **Amorph integration contract**, not generic Cmajor host advice. For
Amorph Instrument, FX, and MIDI patches, declare this exact endpoint whenever
the request mentions DAW/host/Ableton sync, tempo-synchronised drums, arps,
sequencers, delays, LFOs, or modulation:

    input event float transportIn;

Amorph does not populate `std::timeline::*` endpoints. Do not declare
`std::timeline::Position`, `Tempo`, `TimeSignature`, or `TransportState` for
Amorph host sync: such code may compile but receives no DAW timing data.

Amorph sends six consecutive float events at the start of every audio block in
this fixed order: **play, bpm, numerator, denominator, ppq, barStart**. Parse the
packet directly; do not invent fields or MIDI clock accessors:

    int transportSlot = 0;
    bool hostPlaying = false;
    float hostBpm = 120.0f;
    int hostNumerator = 4;
    int hostDenominator = 4;
    float64 currentPpq = 0.0;
    float64 hostBarStartPpq = 0.0;
    int lastStepIndex = -1;

    event transportIn (float value)
    {
        if (transportSlot == 0)
        {
            bool nextPlaying = value > 0.5f;
            if (nextPlaying != hostPlaying) lastStepIndex = -1;
            hostPlaying = nextPlaying;
        }
        else if (transportSlot == 1)
        {
            hostBpm = clamp (value, 20.0f, 999.0f);
        }
        else if (transportSlot == 2)
        {
            hostNumerator = max (1, int (value + 0.5f));
        }
        else if (transportSlot == 3)
        {
            hostDenominator = max (1, int (value + 0.5f));
        }
        else if (transportSlot == 4)
        {
            currentPpq = float64 (value);
        }
        else
        {
            hostBarStartPpq = float64 (value);
        }

        transportSlot = (transportSlot + 1) % 6;
    }

Every PPQ and bar-start packet is authoritative, so assign it without resetting
the latch from either delta alone. Exact `value < currentPpq`, `!=`, or fixed
error thresholds can turn rounding or an in-step seek into a retrigger at the
DAW buffer rate. A normal `barStart` advance arrives at the next block after the
true in-block bar line; resetting there creates a second, off-grid trigger.
Likewise, a BPM packet changes the forward phase increment and must not retrigger
the current step. The computed global step change handles normal bar transitions,
loops, and seeks. Reset only for play-state, time-signature, or division changes.
A seek that remains inside the currently latched step waits for the next grid
boundary instead of emitting an off-grid trigger. Never use
`max(localPpq, hostPpq)` or soft-lag locks; they drift.

Keep PPQ and bar-start state in `float64`. A `float` PPQ accumulator loses enough
precision after several bars to move a grid crossing by multiple samples inside
a large DAW block. Cast each incoming float packet to `float64`, calculate the
step in `float64`, and advance with `float64 (hostBpm) / 60.0 /
processor.frequency`.

Between packets, advance only while playing with `float64 (hostBpm) / 60.0 /
processor.frequency`.
When stopped, emit no new clocked triggers and set `lastStepIndex = -1`.

PPQ lengths: quarter `1.0`, eighth `0.5`, sixteenth `0.25`, eighth-triplet `1.0
/ 3.0`, dotted eighth `0.75`. Global step = `floor(currentPpq /
positiveStepLength)`. Use that global step as the trigger latch, including for
`1 bar`, so the index changes at every bar. Bar-relative pattern position may
separately use `currentPpq - hostBarStartPpq`; bar length is `hostNumerator *
4.0 / max(1, hostDenominator)`. Never use a bar-relative step as the sole trigger
latch: it repeats its index at each bar and cannot clock a `1 bar` division
without an off-grid reset. Trigger only when the computed global step changes.
A BPM oscillator/sample counter is not phase-locked.

Musical Rate/Division/Sync controls are discrete named selectors, never arbitrary values
such as `0.121413`:

    input event float param1 [[ name: "Rate", min: 0, max: 7, init: 4, step: 1,
                                text: "1/16|1/8T|1/8|1/4T|1/4|1/2|1/1|1 bar" ]];
    event param1 (float v) { divisionIndex = clamp (int (v + 0.5f), 0, 7); lastStepIndex = -1; }
    float getDivisionQuarterNotes()
    {
        if (divisionIndex == 0) return 0.25f;
        if (divisionIndex == 1) return 1.0f / 3.0f;
        if (divisionIndex == 2) return 0.5f;
        if (divisionIndex == 3) return 2.0f / 3.0f;
        if (divisionIndex == 4) return 1.0f;
        if (divisionIndex == 5) return 2.0f;
        if (divisionIndex == 6) return 4.0f;
        return float (hostNumerator) * 4.0f / float (max (1, hostDenominator));
    }

For arps/drums/sequencers use `floor (currentPpq /
max (0.0001f, getDivisionQuarterNotes()))` as the trigger latch. Derive a
separate bar-relative index only when the musical pattern must restart each bar.

A musical arpeggiator must also articulate steps. Do not accumulate sustained
step voices. Release/reuse the previous voice or schedule a bounded gate while
keeping the physically held MIDI-note set separate from sounding step voices.

**Buffer-size audit:** identical MIDI/transport must produce identical grid
samples at 31, 64, 257, and 511 frames. Block-boundary retriggers are not sync.

For tempo-synchronised delay/LFO/envelope DSP, convert quarter-note units with
host BPM:

    float divisionQuarterNotes = 1.0f; // quarter=1, eighth=0.5, dotted eighth=0.75
    float periodSeconds = divisionQuarterNotes * 60.0f / max (20.0f, hostBpm);
    int periodSamples = clamp (int (periodSeconds * sampleRate + 0.5f),
                               1, maxBufferSamples - 1);

Apply a valid host BPM immediately whether playing or stopped. Play gates new
triggers, not delay tails. A division selector must map to quarter-note units;
`delayTimeParam * 0.25f`, fixed seconds, or code without `hostBpm` is
**not BPM sync**. Host-synced MIDI may emit timed notes from `main()`; held-note bookkeeping
stays in `event midiIn`.
