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
`hostBpm / 60 / sampleRate`. Host BPM overrides any manual BPM control while
playing; a BPM parameter is fallback-only when free-running was explicitly
requested. When stopped, emit no new clocked triggers by default and set
`lastStepIndex = -1` so restart immediately re-aligns.

Use PPQ lengths: quarter `1.0`, eighth `0.5`, sixteenth `0.25`, eighth-triplet
`1.0 / 3.0`, dotted eighth `0.75`. For a global clock use
`floor(currentPpq / positiveStepLength)`. To restart a pattern each bar use
`currentPpq - hostBarStartPpq`; bar length in quarter notes is
`hostNumerator * 4.0 / max(1, hostDenominator)`. Trigger only when the computed
step index changes. Recalculate from the authoritative PPQ after start, seek,
loop, tempo automation, and time-signature changes; never let a local sample
counter become the source of truth.

Host-synced MIDI generators may schedule note events from `main()`; this is the
intentional exception to the event-only MIDI rule. Held-note bookkeeping remains
inside `event midiIn`. Audio instruments/effects keep their normal audio loop and
use the same clock state to trigger drums or update tempo-synchronised DSP.
