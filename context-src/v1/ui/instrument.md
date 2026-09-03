You are writing the JavaScript UI for the **Amorph_Instrument** plugin variant.

Variant facts:

- Parameters: `sendEventOrValue`, `addAllParameterListener`, and
  `requestParameterValue` are available.
- Output events may be observed with `addEndpointListener`, but only for endpoints
  actually declared by the supplied DSP.
- Incoming MIDI visualization is available through `window.__amorphProcessMidi`.
- Instrument has no `window.__amorphProcessMidiOut` bridge.

When the requested UI needs MIDI input or clickable notes:

```javascript
window.__amorphProcessMidi = messages => {
  for (const { s, d1, d2 } of messages) {
    const type = s & 0xF0;
    if (type === 0x90 && d2 > 0) highlightKey(d1, true, d2 / 127);
    else if (type === 0x80 || (type === 0x90 && d2 === 0)) highlightKey(d1, false, 0);
  }
};
```

UI note buttons send packed MIDI only with:

```javascript
patchConnection.sendMIDIInputEvent("midiIn", (0x90 << 16) | (note << 8) | velocity);
patchConnection.sendMIDIInputEvent("midiIn", (0x80 << 16) | (note << 8));
```

`sendMIDI` does not exist. Delete only the handler this view installed in
`disconnectedCallback()`. Generate all requested keys as real buttons.

The user request determines the visual style. Preserve its palette, references,
layout, control emphasis, and exclusions while satisfying the contract below.

{{CORE_UI_CONTRACT}}
