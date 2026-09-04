## AMORPH HOST TRANSPORT AND DAW SYNC

For host sync:

    input event float transportIn;
    int transportSlot=0;
    bool hostPlaying=false;
    float hostBpm=120.0f;
    int hostNumerator=4;
    int hostDenominator=4;
    float64 currentPpq=0.0;
    float64 hostBarStartPpq=0.0;

`transportIn` is the reserved hidden host-fed endpoint; never rename it to `paramN`,
add `[[ ... ]]`, or expose a "Transport In" UI control.
Amorph does not populate `std::timeline::*`. Packet:
**play, bpm, numerator, denominator, ppq, barStart**. Parse only here, never in `main()`:

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

Keep `int lastStepIndex = -1`. Between packets, advance playing PPQ by
`float64 (hostBpm) / 60.0 / processor.frequency`; stop resets the latch and emits
no clocked triggers. Otherwise reset only on play, signature, or division
changes. Do not reset it from either PPQ/barStart delta alone;
exact inequality, value decrease, or a fixed error threshold; a normal `barStart` advance,
rounding, BPM change, or in-step seek must not retrigger at the DAW buffer rate.
Never use `max(localPpq, hostPpq)` or a soft-lag lock.

Quarter lengths: 1/16 `0.25`, 1/8T `1/3`, 1/8 `0.5`, 1/4T `2/3`, 1/4 `1`, 1/2
`2`, 1/1 `4`, bar `numerator * 4 / denominator`. Use a stepped integer selector:
`text: "1/16|1/8T|1/8|1/4T|1/4|1/2|1/1|1 bar"`, never arbitrary values such as
`0.121413`; map it in `getDivisionQuarterNotes()`. Labeled endpoints
must also contain `step: 1` and integer `min`, `max`, and `init`.

For arps, drums, and sequencers compute the global step with
`floor (currentPpq / max (0.0001f, getDivisionQuarterNotes()))` and trigger only
when it differs from `lastStepIndex`. Use that global step as the trigger latch
even for `1 bar`; a bar-relative pattern index cannot be the sole latch.
A BPM oscillator or sample counter is not phase-locked.
A musical arpeggiator must articulate bounded note gates; keep physically held notes separate from sounding step voices.

Tempo-synced delay/LFO/envelope DSP uses
`periodSeconds = divisionQuarterNotes * 60.0f / max (20.0f, hostBpm)`. Apply a
valid host BPM immediately whether playing or stopped; play gates new triggers,
not delay tails. Fixed seconds, `delayTimeParam * 0.25f`, or no `hostBpm` is
**not BPM sync**.

**Buffer-size audit:** identical MIDI/transport must produce identical grid
samples at 31, 64, 257, and 511 frame buffers. Block-boundary retriggers are not
sync.
