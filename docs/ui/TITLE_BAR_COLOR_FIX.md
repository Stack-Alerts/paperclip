# Title Bar Color Fix - GNOME/Linux

## Problem
The OS window title bar (with minimize/maximize/close buttons) doesn't match our dark theme. It's using GNOME's default gray color instead of our darkest background (#0F1419).

## Solution
The title bar is controlled by **GNOME's window manager**, not Qt. You have 2 options:

### Option 1: GNOME Theme (Recommended)
Install a proper dark GNOME theme that will affect ALL applications:

```bash
# Install GNOME Tweaks (if not installed)
sudo apt install gnome-tweaks

# Install a dark theme (Adwaita Dark is built-in, or install others)
sudo apt install gnome-themes-extra

# Launch GNOME Tweaks
gnome-tweaks
```

Then in GNOME Tweaks:
1. Go to **Appearance** → **Themes**
2. Set **Applications** to a dark theme (e.g., "Adwaita-dark")
3. The title bar will now be dark

### Option 2: Enable Client-Side Decorations (CSD) in Qt

This would remove the OS title bar entirely and let Qt draw its own. However, this is more complex and may not be ideal for your workflow.

## Current State
✅ All UI elements within the app are properly themed
✅ Menu bar: #1E2128 (Background Tertiary)
✅ Toolbar: #1E2128 (Background Tertiary)
✅ Section headers: #00A3BF (Muted cyan)
✅ Transparent buttons
✅ Semantic Bullish/Bearish colors

❌ OS title bar: Controlled by GNOME (not our app)

## Recommended Action
Use GNOME Tweaks to apply a dark theme system-wide. This will:
- Make the title bar dark
- Make all other apps consistent
- Provide a professional dark environment

## Alternative: Custom Title Bar in Qt
If you really want Qt to control it, I can implement a frameless window with custom title bar, but this is a significant change and may affect:
- Window dragging
- Resize behavior
- System menus
- Window manager integration
