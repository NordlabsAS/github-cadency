# P3-08: Mobile / Responsive Design

> Priority: 3 (Nice-to-Have) | Effort: Medium | Impact: Low-Medium
> Competitive gap: Desktop-only layout. Managers checking metrics on mobile get a poor experience.

## Context

DevPulse's current layout is designed for desktop screens. Engineering managers often want to check on stale PRs, workload, or sync status from their phone — especially during on-call or commute. A responsive design would make this possible without a dedicated mobile app.

## What to Build

### Responsive Breakpoints

| Breakpoint | Target | Layout Changes |
|-----------|--------|---------------|
| `>= 1280px` | Desktop | Current layout (no change) |
| `768-1279px` | Tablet | Sidebar collapses, 2-column stat cards |
| `< 768px` | Mobile | Single column, hamburger nav, condensed tables |

### Key Changes by Component

**Layout/Navigation:**
- Hamburger menu replacing top nav on mobile
- Slide-out drawer for sidebar navigation (Insights, Admin)
- Sticky bottom nav bar for primary actions (Dashboard, Sync, Profile)
- Date range picker: compact mode (single button → bottom sheet)

**Dashboard:**
- Stat cards: 1 column on mobile (currently 3-4 columns)
- Trend charts: full width, reduced height
- Tables: horizontal scroll or card-style layout for narrow screens
- Stale PR section: compact card layout

**Charts:**
- Recharts `ResponsiveContainer` already handles width
- Reduce label density on mobile (fewer tick labels)
- Touch-friendly tooltips (tap instead of hover)

**Tables (team registry, sync history, etc.):**
- Priority columns visible by default; secondary columns in expandable row
- OR card layout: each row becomes a card with key info visible

**Forms (sync wizard, settings):**
- Full-width inputs
- Stacked layout (no side-by-side fields)
- Bottom-sheet modals instead of centered dialogs

## Frontend Changes

### Layout Component (`frontend/src/components/Layout.tsx`)
- Add mobile detection (`useMediaQuery` hook or Tailwind responsive)
- Hamburger menu button (visible < 768px)
- Slide-out navigation drawer
- Conditionally render compact date picker

### New Component: `MobileNav.tsx`
- Bottom navigation bar with 4-5 icons
- Active state indicator
- Visible only on mobile

### New Hook: `useBreakpoint.ts`
- Returns current breakpoint ("mobile" | "tablet" | "desktop")
- Based on `window.matchMedia` with SSR safety

### Tailwind Responsive Classes
- Most changes are CSS-only using Tailwind responsive prefixes
- `grid-cols-1 md:grid-cols-2 lg:grid-cols-4` for stat card grids
- `hidden md:block` for secondary table columns
- `block md:hidden` for mobile-only elements

### Table Components
- Add `ResponsiveTable` wrapper that switches between table and card layout
- Priority columns configurable per table instance

### Chart Adjustments
- Reduce `tickCount` on mobile
- Larger touch targets for interactive elements
- Swipe gestures for date range navigation (optional)

## No Backend Changes

This is a frontend-only task. All data and APIs remain unchanged.

## Testing
- Visual testing at each breakpoint (320px, 375px, 768px, 1024px, 1440px)
- Test hamburger menu open/close
- Test table scroll/card layout switching
- Test date picker in compact mode
- Test chart touch interactions
- Ensure no horizontal overflow at any breakpoint

## Acceptance Criteria
- [ ] Dashboard readable and usable on 375px-wide screen
- [ ] Navigation works via hamburger menu on mobile
- [ ] Stat cards stack to single column on mobile
- [ ] Tables either scroll horizontally or switch to card layout
- [ ] Charts render correctly at all widths
- [ ] Date range picker works on mobile (compact mode)
- [ ] No horizontal scroll on the page body at any breakpoint
- [ ] Sidebar sections (Insights, Admin) accessible via drawer
