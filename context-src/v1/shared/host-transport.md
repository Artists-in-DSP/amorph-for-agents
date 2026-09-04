## AMORPH HOST TRANSPORT AND DAW SYNC

    input event float transportIn;
    int transportSlot=0;
    bool hostPlaying=false;
    float hostBpm=120.0f;
    int hostNumerator=4;
    int hostDenominator=4;
    float64 currentPpq=0.0;
    float64 hostBarStartPpq=0.0;

`transportIn` is the reserved hidden host-fed endpoint: never rename it to `paramN`, add `[[ ... ]]`, or expose a "Transport In" UI control. Amorph does not populate `std::timeline::*`. Packet: **play, bpm, numerator, denominator, ppq, barStart**. Parse here, never in `main()`:

    event transportIn(float value)
    {
        if(transportSlot==0) hostPlaying=value>0.5f;
        else if(transportSlot==1) hostBpm=clamp(value,20.0f,999.0f);
        else if(transportSlot==2) hostNumerator=max(1,int(value+0.5f));
        else if(transportSlot==3) hostDenominator=max(1,int(value+0.5f));
        else if(transportSlot==4) currentPpq=float64(value);
        else hostBarStartPpq=float64(value);
        transportSlot=(transportSlot+1)%6;
    }

Keep `int lastStepIndex = -1`. Always compute and trigger from the global step first, then increment PPQ exactly once:

    if (hostPlaying)
    {
        float64 stepLength = max (0.0001, float64 (getDivisionQuarterNotes()));
        int globalStep = int (floor (currentPpq / stepLength));
        if (globalStep != lastStepIndex)
        {
            lastStepIndex = globalStep;
            // stop the prior note, then emit at most one grid note
        }
        currentPpq += float64 (hostBpm) / 60.0 / processor.frequency;
    }
    else
    {
        lastStepIndex = -1;
    }

Use that global step as the trigger. This is the only legal PPQ advance. Never replace `processor.frequency` with `processor.period`; never divide by `processor.period`. The generic period-casting rule is only for oscillators and timers. Never cast `processor.frequency` to `float` or store it in a `float` alias; both cause buffer-size-dependent triggers. Stop emits nothing; a transport packet must not directly emit a note.

Set `lastStepIndex = -1` on play-state, signature or division change. Received PPQ only replaces `currentPpq`. Do not reset it from either PPQ/barStart delta, exact inequality, value decrease, or a fixed error threshold. Also, never write `currentPpq = 0.0` on play or restart; a normal `barStart` advance, rounding, BPM change, or seek must not retrigger at the DAW buffer rate. Never use `max(localPpq, hostPpq)` or soft-lag lock.

Quarter lengths: 1/16 `0.25`, 1/8T `1/3`, 1/8 `0.5`, 1/4T `2/3`, 1/4 `1`, 1/2 `2`, 1/1 `4`, bar `numerator * 4 / denominator`. Map `getDivisionQuarterNotes()` from `text: "1/16|1/8T|1/8|1/4T|1/4|1/2|1/1|1 bar"`; never arbitrary values like `0.121413`. Labeled endpoints must also contain `step: 1` and integer `min`, `max`, `init`.

Arps/drums/sequencers: `floor (currentPpq / max (0.0001f, getDivisionQuarterNotes()))`. A BPM oscillator or sample counter is not phase-locked. A musical arpeggiator must articulate bounded note gates and keep physically held notes separate.

Tempo-synced delay/LFO/envelope: `periodSeconds = divisionQuarterNotes * 60.0f / max (20.0f, hostBpm)`. Apply a valid host BPM immediately whether playing or stopped; play gates triggers, not delay tails. Fixed seconds, `delayTimeParam * 0.25f`, or no `hostBpm` is **not BPM sync**.

**Buffer-size audit:** identical MIDI/transport must produce identical grid samples at 31, 64, 257, and 511 frame buffers. Block-boundary retriggers are not sync.
