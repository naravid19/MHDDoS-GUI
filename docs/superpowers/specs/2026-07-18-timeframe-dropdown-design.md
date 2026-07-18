# Timeframe Dropdown Design

## Overview
This design replaces the wide row of 8 timeframe buttons (1M, 5M, 30M, 1H, 3H, 6H, 12H, 24H) in the MHDDoS-GUI frontend with a sleek, minimalist dropdown menu. This aligns with the "Option C" minimalist aesthetic requested by the user, saving horizontal space and reducing visual clutter.

## Architecture & Structure
The component will be built using raw HTML, Tailwind CSS, and Vanilla JavaScript. It will be implemented in both `web/index.html` and `web/index-new.html`.

### UI Components

1. **Trigger Button**
   - **Purpose:** Displays the currently selected timeframe and acts as the toggle for the dropdown.
   - **Styling:** Dark translucent background (`bg-gray-800/50`), ghost border (`border-gray-700/50`), monospaced text, and a small SVG chevron.
   - **State:** Updates text automatically when a new timeframe is selected.

2. **Dropdown Menu (Popover)**
   - **Purpose:** Contains the 8 timeframe options.
   - **Positioning:** Absolute positioned relative to the trigger button container. Z-index elevated to float above charts.
   - **Styling:** Glassmorphism effect (`backdrop-blur-xl`, `bg-gray-900/90`), tight padding, rounded corners, subtle border.
   - **Items:** Each option is a button with hover effects (`hover:bg-gray-800/50`). The active item is highlighted with text color (`text-white`) or a dot indicator, while inactive ones remain muted (`text-gray-400`).

## Behavior & Interaction Logic

1. **Toggling:**
   - Clicking the trigger button toggles a `hidden` class on the dropdown menu.
   - An event listener on the `document` detects clicks outside the dropdown container to close it (Click-outside behavior).

2. **Selection:**
   - When an item is clicked in the dropdown:
     - The dropdown menu is immediately hidden.
     - The text inside the trigger button is updated to match the selection (e.g., "1H").
     - The existing global `setTimeframe(val)` function is called to trigger the chart refresh.
     - The active state styling within the dropdown list is updated.

## Implementation Details

- Add inline JS to handle the dropdown state directly in the HTML or add a small utility script block at the end of the files.
- The markup will use a `<div class="relative">` wrapper around the trigger and the absolute menu to ensure correct positioning.

## Scope
- Modify `web/index.html` (Network Velocity Tracking section)
- Modify `web/index-new.html` (Telemetry Flux section)
- Ensure existing `setTimeframe` function integrates smoothly without requiring backend changes.
