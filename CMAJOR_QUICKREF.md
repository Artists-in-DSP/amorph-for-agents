# Cmajor quick reference (Amorph)

Generated code is [Cmajor](https://cmajor.dev) — a C-family DSP language by Cmajor Software Ltd. amorph ships under a [commercial Cmajor license](https://cmajor.dev/docs/Licence.html); your patches are yours, no GPL copyleft, no runtime royalty.

Minimal conventions for **valid** amorph DSP. For full rules, call MCP prompt
`cmajor-rules`; it is the product's source of truth for detailed syntax.

## Variant endpoints

Endpoint declarations must be the first declarations inside the named processor block.
Use the endpoint set that matches the loaded runtime:

| Runtime | Variant | Required endpoints |
|---------|---------|--------------------|
| `Amorph_Instrument` | `instrument` | `output stream float<2> out;` + `input event std::midi::Message midiIn;` |
| `Amorph_FX` | `fx` | `output stream float<2> out;` + `input stream float<2> in;` |
| `Amorph_MIDI` | `midi` | `output event std::midi::Message midiOut;` + `input event std::midi::Message midiIn;` |

Declare **`output` before `input`** inside the processor block.

Audio is `stream`, not `event`. MIDI is `event`.

## Minimal instrument skeleton

```cmajor
processor MyInstrument {
    output stream float<2> out;
    input event std::midi::Message midiIn;

    input event float param1 [[ name: "Volume", min: 0.0, max: 1.0, init: 0.7 ]];

    float volume = 0.7f;
    float phase = 0.0f;
    float amp = 0.0f;

    event param1 (float v) { volume = v; }

    event midiIn (std::midi::Message msg) {
        if (msg.isNoteOn()) {
            amp = msg.getFloatVelocity();
        } else if (msg.isNoteOff()) {
            amp = 0.0f;
        }
    }

    void main() {
        loop {
            phase += float(processor.period) * 440.0f;
            if (phase >= 1.0f) phase -= 1.0f;
            float sample = (phase * 2.0f - 1.0f) * amp * volume;
            out <- float<2>(sample, sample);
            advance();
        }
    }
}
```

## Minimal FX skeleton

```cmajor
processor MyFx {
    output stream float<2> out;
    input stream float<2> in;

    input event float param1 [[ name: "Gain", min: 0.0, max: 1.0, init: 0.5 ]];

    float gain = 0.5f;

    event param1 (float v) { gain = v; }

    void main() {
        loop {
            out <- in * gain;
            advance();
        }
    }
}
```

## Minimal MIDI skeleton

```cmajor
processor MyMidi {
    output event std::midi::Message midiOut;
    input event std::midi::Message midiIn;

    event midiIn (std::midi::Message msg) {
        midiOut <- msg;
    }

    void main() {
        loop {
            advance();
        }
    }
}
```

## Hard rules

| Rule | Detail |
|------|--------|
| Processor | Must be named: `processor MyName { ... }` |
| Endpoint placement | Endpoint declarations first, before state variables/functions |
| Endpoint order | **`output` before `input`** |
| MIDI type | `std::midi::Message` — not `midi::Message` |
| Loop vars | Use `var` for loop variables when needed; avoid `let` in generated Amorph DSP |
| Main loop | `void main() { loop { ... advance(); } }` |
| Parameters | Prefer `input event float param1`, `param2`, ... with display label in `[[ name: "..." ]]` |
| Parameter values | Store event values in state via `event param1 (float v) { ... }`; read the state in `main()` |
| FX output | Write `out <- float<2>(L, R);` or `out <- in * gain;`; do not index the output |

## Common mistakes

- Using `output event float` for audio. Audio endpoints are `stream`.
- Adding audio input to an instrument runtime or MIDI endpoints to an FX runtime.
- Editing locked binary `dsp.cmajor` (`Cmaj0001...` header).
- Assuming file save = compile (use `apply_draft` or `reload_from_disk`).
- `generate_code` without `task_complete` + `apply_draft` — changes do not reach live audio.

## UI (separate file)

JavaScript Web Components live in `index.js`. Rules: prompt `ui-rules`.

## Learn more

- https://cmajor.dev
- Amorph runtime: Settings → Connections → **Copy Instructions** (includes variant-specific rules)
