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
            currentPpq = value;
        }
        else
        {
            hostBarStartPpq = value;
        }

        transportSlot = (transportSlot + 1) % 6;
    }

Every received PPQ value is authoritative. Always assign it exactly as shown,
even when it moves backwards or differs only slightly from the locally advanced
value. Never use `max(localPpq, hostPpq)`, a one-sided deadband, or a soft-lag
lock. Those patterns drift and then jump after tempo changes, seeks, or loops.

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
