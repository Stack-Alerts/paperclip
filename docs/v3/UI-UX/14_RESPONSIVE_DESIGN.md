# Responsive Design Specification
**Document**: 14_RESPONSIVE_DESIGN.md
**Status**: 🟢 Complete
**Priority**: P3 - Low

## Breakpoints
- Desktop: ≥1280px (primary target)
- Laptop: 1024-1279px
- Tablet: 768-1023px (not primary)
- Mobile: <768px (not supported)

## Layout Adaptation

### Desktop (1280px+)
- Full UI with all panels visible
- Side-by-side block search and configuration
- Wide preview panel
- All tooltips and helpers visible

### Laptop (1024-1279px)
- Slightly condensed panels
- Block search collapsible
- Preview panel resizable
- Maintain all functionality

### Tablet (768-1023px)
- Stacked layout
- Collapsible panels
- Touch-friendly buttons (48x48px min)
- Limited preview

## Scrolling
- Main window: Vertical scroll
- Block list: Independent vertical scroll
- Preview chart: Horizontal & vertical pan/zoom
- Search results: Independent scroll

## Window Resize Handling
- Debounced resize events
- Maintain panel ratios
- Persist user preferences
- Graceful degradation

**Version**: 1.0
