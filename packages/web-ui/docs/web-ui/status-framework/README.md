# Status Framework

The Status Framework is a centralized, typed system for displaying transient messages in the bottom status bar of the Strategy Builder application.

## Overview

The Status Framework replaces scattered `setStatusText()` calls throughout the application with a unified, event-driven API. It consists of:

- **StatusBus**: A lightweight event emitter singleton that dispatches status events
- **StatusContext**: React context + hooks that manage UI state
- **StatusBar**: A fixed bottom-bar component that displays the current status
- **status.emit/update/dismiss/clear API**: Simple imperative functions to emit status messages

## Why

The old approach stored status as local component state (`setStatusText`), which required:
- Status bar markup in every component that needed to show messages
- Manual coordination of message timing and clearing
- Duplication of styling and layout across multiple components

The new framework centralizes status management at the root layout level, with a single StatusBar component.

## Ticker Mode

The Status Framework includes placeholder support for `tickerMode`, which will allow scrolling through a queue of statuses in future enhancements. Currently `tickerMode` is `false` and only the most recent status is displayed.

## Components

### StatusBar (Root Layout)

The `<StatusBar />` component is rendered in `src/app/layout.tsx` at the bottom of the screen. It displays the most recent status entry and automatically clears expired messages.

### StatusBarProvider

Wraps the application root to provide context for status management. Must be a parent of any component using the `status` API or `useStatus()` hook.

## Next Steps

- Test visual regression baseline (3 states: idle, saved, countdown)
- Integrate with Architect review on API surface
- Prepare for Ticker Mode implementation in future slice
