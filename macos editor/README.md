# macOS Editor

A lightweight native macOS editor prototype for this repo.

What it does:

- opens multiple documents in one app window
- reads and writes `.docx`, `.rtf`, `.txt`, and `.html`
- uses AppKit's native rich text engine to stay small and fast
- embeds the existing DocEdit browser UI in a side panel
- starts the local `./scripts/doc-edit-game.sh` server from inside the app
- creates game API sessions and can import or submit game documents

What it does not try to do:

- full Microsoft Word feature parity
- perfect round-trip fidelity for every complex `.docx` feature
- a full iOS build in this first pass

## Run

From this folder:

```bash
swift run
```

Or open `Package.swift` in Xcode and run the `MacOSEditorApp` target.

## Notes

- The rich document path is powered by AppKit's attributed string document support, including Office Open XML on macOS.
- The DocEdit game uses its own structured text format internally, so game imports are opened as plain text editing tabs while the existing browser UI is also available in-app.
- The app looks for the repository root by walking upward until it finds `scripts/doc-edit-game.sh`.
