# Interface notes

Recall is an incident workbench, not a chat app. The main screen keeps the selected case, the decision, and the supporting evidence close enough to compare without opening another page.

## Layout

On a wide screen the app has three working areas:

1. the case queue on the left;
2. the active case and result in the center; and
3. the evidence ledger below the result.

The bottom action bar holds feedback and the main **Analyze case** action. At narrower widths the center panels stack, and on mobile the queue becomes an overlay so the current case stays first.

## Visual language

The palette uses dark navy surfaces with thin slate borders. Blue is reserved for navigation and primary actions. Amber marks incomplete evidence, red marks escalation or failure, and green marks a cited result or successful feedback.

Manrope is used for interface text and IBM Plex Mono for identifiers, scores, and source references. Spacing is compact because the screen is meant for scanning operational detail, but headings and labels should stay plain and short.

Color is never the only signal. Statuses also have text, icons, or border treatments.

## Interaction rules

- **New case** clears the selected demo and focuses the subject field.
- Subject and description must meet their minimum lengths before analysis starts.
- Changing cases cancels the in-flight request. Late responses are ignored.
- A draft shows its cited steps and evidence score factors.
- An escalation explains why Recall stopped and what information is missing.
- Negative feedback requires a written correction; positive feedback does not.
- Accepting a draft does not automatically claim that time was saved.

## Responsive behavior

Below 1180px the queue narrows, secondary header details disappear, and the case and analysis panels stack. Below 760px the queue becomes a full-height overlay and the rest of the workbench uses one column. The layout supports widths down to 320px.

The evidence table becomes labeled records on small screens. The action bar wraps and the page adds bottom padding so fixed controls do not cover content.

## Accessibility

Use native landmarks, labels, buttons, links, and table semantics. All interactive controls need a visible `:focus-visible` state. Icon-only buttons need accessible names. Queue selection uses `aria-pressed`, the mobile queue control exposes `aria-expanded`, and analysis updates are announced through a polite live region.

Reduced-motion preferences should make transitions effectively immediate. Do not remove persistent labels, error text, focus indicators, or the semantic evidence structure to simplify the layout.

## States worth preserving

The interface needs explicit states for loading, unavailable demo cases, empty search results, provider rate limits, general service failures, cited drafts, escalations, no evidence, and feedback success or failure. These are part of the product behavior, not decoration.

If the layout changes, keep three things intact: evidence must remain inspectable, escalation must remain a normal outcome, and the operator must make the final decision.
