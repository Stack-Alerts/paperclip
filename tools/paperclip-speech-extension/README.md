# Paperclip Speech Input — Brave Extension (v0.3.0)

Adds a floating mic button to every Paperclip input. Click → speak → text appears in the input.

**Backend:** browser-native Web Speech API. No local server, no API keys, $0.

**Scope:** **Paperclip only.** Won't load on any other site you visit in Brave.

---

## Install (one time, ~30 seconds)

1. Open Brave and go to `brave://extensions`
2. Toggle **Developer mode** (top-right)
3. Click **Load unpacked**
4. Select this folder:
   `/home/sirrus/.paperclip/instances/default/workspaces/73e7ef43-1337-47f8-9cf2-8db91ebcf555/paperclip-speech-extension`
5. The extension card should appear, enabled.

## Use it

1. Open your local Paperclip UI in Brave (anything served from `localhost` or `127.0.0.1`).
2. A small mic button (🎤) appears in the top-right corner of every text input.
3. **First click → Brave will ask for mic permission. Allow it.**
4. Click 🎤 → it turns red (🎙️) → speak → click again to stop.
5. The transcript appears in the input. Press send normally.

## If the mic button shows ⚠️ with "network" error

This is the documented Brave/Web-Speech-API issue. The Web Speech API calls a Google cloud endpoint; Brave sometimes blocks it.

**Fixes to try, in order:**

1. **Enable the Google services flag in Brave:**
   - Open `brave://settings/braveSync`
   - Or `brave://flags` → search "speech" → enable any related flag → relaunch.
2. **Allow Google services in Brave Shields for your Paperclip origin:**
   - Click the Shields icon in the address bar → set to disabled for `localhost`.
3. **Check site mic permission:**
   - `brave://settings/content/microphone` → ensure your Paperclip origin is allowed.
4. **If none of the above work:** the Web Speech API path is broken for your Brave build. Escalate on issue [BTCAAAAA-30570](/BTCAAAAA/issues/BTCAAAAA-30570) and we'll switch to path B (Groq hosted Whisper) or path C (self-hosted faster-whisper).

## If the mic button doesn't appear

The extension watches for input elements. If a Paperclip update changes input markup:

1. Open the page, right-click → Inspect → confirm a `<textarea>`, `<input>`, or `[contenteditable]` exists.
2. Open `brave://extensions` → reload this extension.
3. If still nothing, report on [BTCAAAAA-30570](/BTCAAAAA/issues/BTCAAAAA-30570) with a screenshot of the DOM around the input — we'll widen the selector list.

## Disable

`brave://extensions` → toggle off, or **Remove**. Paperclip is untouched.

## How this survives `npx paperclip@latest`

The extension lives in your Brave profile, not in Paperclip's install directory. `npx paperclipai` only updates server/CLI/UI inside its own paths. Your extension is unaffected by any Paperclip upgrade.

## Files

- `manifest.json` — MV3 manifest, matches `localhost` and `127.0.0.1`
- `content.js` — input discovery + mic button + Web Speech recognition
- `content.css` — mic button styling (floating overlay, no layout shift)

## How "Paperclip only" works (v0.2.0)

Two layers of scoping — the extension is invisible everywhere else:

1. **Manifest match patterns** restrict the content script to `http://localhost:3100/*` and `http://127.0.0.1:3100/*` (Paperclip's known web-UI port). The script doesn't even load on other origins or other localhost ports.
2. **Runtime guard** inside `content.js` checks for Paperclip's identity marker (`<meta name="apple-mobile-web-app-title" content="Paperclip">` or `<title>Paperclip</title>`). If the marker isn't present within 3 seconds of page load, the script bails silently. So even if you ever loosen the match patterns, the mic still only attaches on actual Paperclip pages.

## Customization

- **Paperclip on a different port?** Edit `manifest.json` → replace `3100` in both `matches` entries with your port (e.g. `"http://localhost:3200/*"`). The runtime marker check still protects against false matches. Reload the extension after editing.
- **Different language?** Edit `content.js` → `recognition.lang` (defaults to your browser locale).
- **Don't want continuous capture?** Edit `content.js` → set `recognition.continuous = false` (then a single utterance auto-stops).

## Privacy note

Web Speech API streams audio to Google for transcription. If you'd rather not — switch to path B (Groq) or path C (self-hosted) by replying on [BTCAAAAA-30570](/BTCAAAAA/issues/BTCAAAAA-30570).
