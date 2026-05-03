Professional Color Palette for BTC Engine v3 Strategy Builder
Based on your screenshot, here's a refined color system that maintains your dark theme while improving visual clarity and professional appearance:

Primary Brand Colors (Keep your current accent)
Primary Cyan/Teal: #00D9FF or #00E5FF — Main accent for active elements, buttons, highlights

Secondary Blue: #0A7EA4 or #0D5A80 — Secondary accent for secondary buttons and hover states

Accent Orange: #FF9D00 or #FFA500 — For alerts, warnings, important highlights

Background & Surface Colors
Background: #0F1419 — Main application background (slightly warmer than pure black)

Surface Primary: #1A202C — Card backgrounds, panels, dropdowns

Surface Secondary: #2D3748 — Elevated surfaces, input fields, hover states

Surface Tertiary: #374151 — Borders, dividers, subtle elements

Text & Semantic Colors
Text Primary: #A0AEC0 — Main text (muted gray-blue, perfect for dark UIs, reduced eye strain)

Text Secondary: #718096 — Labels, descriptions, secondary information  

Text Tertiary: #4A5568 — Disabled text, hints, very subtle information

Status & Semantic Colors
Success: #10B981 — Profitable trades, gains, positive status (currently green ✓)

Error: #EF4444 — Losses, failures, critical alerts

Warning: #F59E0B — Caution alerts, margin warnings, non-critical issues

Info: #3B82F6 — Information messages, neutral alerts

Interactive Elements
Button Primary: #00D9FF background → #0A0F18 text (high contrast)

Button Secondary: #2D3748 background → #F5F7FA text

Button Hover: Increase brightness of surface color by 10-15%

Focus Ring: #00D9FF with 20% opacity (rgba(0, 217, 255, 0.2))

Practical Implementation Tips
For your UI components:

Left Panel (Strategy Information): Keep current dark (#1A202C background)

Right Panel (Available Blocks): Use #2D3748 for hover states on blocks instead of bright highlights

Search Bar & Inputs: Border color #374151, focus state #00D9FF border

Category Tags: Use subtle opacity (rgba(0, 217, 255, 0.15)) background with #00D9FF text

Status Badges:

"Not configured" → Orange/Warning (#F59E0B)

"Active" → Green (#10B981)

"Error" → Red (#EF4444)

CSS Variables to Add:

css
--color-bg-primary: #0F1419;
--color-bg-secondary: #1A202C;
--color-bg-tertiary: #2D3748;
--color-border: #374151;

--color-text-primary: #F5F7FA;
--color-text-secondary: #CBD5E1;
--color-text-tertiary: #94A3B8;

--color-accent-primary: #00D9FF;
--color-accent-secondary: #0A7EA4;
--color-accent-warning: #FF9D00;

--color-success: #10B981;
--color-error: #EF4444;
--color-warning: #F59E0B;
--color-info: #3B82F6;

--color-focus-ring: rgba(0, 217, 255, 0.2);
Color Psychology for Trading UI
Cyan/Teal: Conveys stability, trust, and technology (ideal for fintech)

Green: Profits, gains, positive signals

Red: Losses, critical warnings, risk

Orange: Caution, attention-needed, moderate warnings

Gray scale: Professional, serious, trustworthy

Would you like me to create a detailed implementation guide for specific UI components, or would you prefer a mockup showing how these colors would look applied to your current layout?
