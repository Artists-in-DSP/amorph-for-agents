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
    float currentPpq = 0.0f;
    float hostBarStartPpq = 0.0f;
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
            if (value < currentPpq) lastStepIndex = -1;
            currentPpq = value;
        }
        else
        {
            if (value != hostBarStartPpq) lastStepIndex = -1;
            hostBarStartPpq = value;
        }

        transportSlot = (transportSlot + 1) % 6;
    }

Every received PPQ value is authoritative. Always assign it exactly as shown,
even when it moves backwards or differs only slightly from the locally advanced
value. A backward PPQ packet or changed bar-start value must reset the step latch
before the next sample; otherwise a loop/downbeat that has the same local step
number as the previous bar is silently skipped. Never use `max(localPpq,
hostPpq)`, a one-sided deadband, or a soft-lag lock. Those patterns drift and
then jump after tempo changes, seeks, or loops.

Between packets only, advance `currentPpq` while playing using
`hostBpm / 60 / sampleRate`. A BPM parameter is fallback-only when free-running
was explicitly requested. When stopped, emit no new sequencer/drum triggers by
default and set `lastStepIndex = -1` so restart immediately re-aligns.

Use PPQ lengths: quarter `1.0`, eighth `0.5`, sixteenth `0.25`, eighth-triplet
`1.0 / 3.0`, dotted eighth `0.75`. For a global clock use
`floor(currentPpq / positiveStepLength)`. To restart a pattern each bar use
`currentPpq - hostBarStartPpq`; bar length in quarter notes is
`hostNumerator * 4.0 / max(1, hostDenominator)`. Trigger only when the computed
step index changes. Recalculate from the authoritative PPQ after start, seek,
loop, tempo automation, and time-signature changes; never let a local sample
counter become the source of truth.

Whenever the user asks for a musical Rate, Division, Sync Time, arp rate, or
sequencer step, expose a **discrete named selector**, not a continuous beat
value. The UI must show musical labels such as `1/4`, never arbitrary values
such as `0.121413`:

    input event float param1 [[ name: "Rate", min: 0, max: 7, init: 4, step: 1,
                                text: "1/16|1/8T|1/8|1/4T|1/4|1/2|1/1|1 bar" ]];
    int divisionIndex = 4;
    event param1 (float value)
    {
        divisionIndex = clamp (int (value + 0.5f), 0, 7);
        lastStepIndex = -1;
    }

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

For arps, drums, and sequencers, derive the step from authoritative PPQ:
`floor ((currentPpq - hostBarStartPpq) / max (0.0001f,
getDivisionQuarterNotes()))`. Reset `lastStepIndex` when the division changes,
transport starts/stops, or a new position packet seeks/loops backward. A
sample counter or BPM-only oscillator can follow tempo but is not phase-locked
to the DAW grid.

For tempo-synchronised delays, LFO periods, envelopes, and other time-based DSP,
the musical division must be converted from quarter-note units using the host
BPM received in every packet:

    float divisionQuarterNotes = 1.0f; // quarter=1, eighth=0.5, dotted eighth=0.75
    float periodSeconds = divisionQuarterNotes * 60.0f / max (20.0f, hostBpm);
    int periodSamples = clamp (int (periodSeconds * sampleRate + 0.5f),
                               1, maxBufferSamples - 1);

Apply a valid host BPM immediately whether transport is playing or stopped, so
tempo-synchronised effect tails and the next start already use the correct
length. The play flag gates new clocked triggers; it does not turn a delay tail
off. A selector such as `DelayTime` 0..7 is only a division index: map it to
quarter-note units first, then use the formula above. `delayTimeParam * 0.25f`,
a fixed seconds table, or any calculation that does not contain `hostBpm` is
**not BPM sync**.

Host-synced MIDI generators may schedule note events from `main()`; this is the
intentional exception to the event-only MIDI rule. Held-note bookkeeping remains
inside `event midiIn`. Audio instruments/effects keep their normal audio loop and
use the same clock state to trigger drums or update tempo-synchronised DSP.
