# Recall interface design guide

## Product framing

Recall is an incident workbench for database-support engineers. It helps an operator turn a new or seeded case into either a cited resolution draft or an explicit escalation. The interface is deliberately not chat-first: the active case, the decision, and the supporting evidence stay visible as one review surface.

The governing principle is **evidence before eloquence**. Confidence is presented as inspectable evidence strength rather than a probability of correctness, and escalation is treated as a safe, successful outcome when the available sources are weak, incomplete, or conflicting. Recall remains a copilot: the operator reviews, accepts, corrects, or hands off the result.

Case text is transient. The privacy note belongs near the active case, not in a distant settings view, because non-persistence is part of the workflow contract.

## Layout and information hierarchy

The desktop composition is a pinned command workbench:

1. **Top bar:** product identity, queue search, corpus health, and generation-provider status. This answers “where am I?” and “is the system ready?” before the operator acts.
2. **Incident queue:** a persistent left rail for selecting safe example cases or starting a new case. Selection is indicated by both a tonal change and a blue inset rule.
3. **Case toolbar:** the active case code and state sit beside the transient-processing notice.
4. **Primary work area:** case input and Recall analysis appear side by side so source details and the proposed decision can be compared without navigation.
5. **Evidence ledger:** retrieved passages, relevance, excerpts, and citation status form a full-width provenance layer beneath the decision.
6. **Action dock:** the current case, feedback controls, draft acceptance, and the primary Analyze action remain fixed at the bottom.

At wide desktop sizes the queue is 292px and the primary work area favors the case editor over the decision panel (`1.25fr / 0.95fr`). Panels use compact headings, clear borders, and dense spacing so operational detail stays visible without becoming a dashboard of disconnected cards.

## Visual system

### Color

The interface uses a matte navy and slate foundation with restrained semantic accents.

- **Canvas:** deep navy (`#0c151f`).
- **Primary surfaces:** navy-slate (`#111f2b`), with raised and soft layers at `#162735` and `#1a2d3d`.
- **Borders:** cool slate (`#2a4051`) and a stronger divider (`#3c586c`). Borders and tonal layering carry most of the depth; shadows are reserved for the bottom dock, status glow, and centered analysis symbols.
- **Text:** near-white (`#e9eef5`), muted blue-gray (`#a7b9c9`), and dim blue-gray (`#8197aa`).
- **Action blue:** `#48a8f7` for primary actions, selection, links, progress, and focus-adjacent emphasis.
- **Amber:** `#f7b84b` for weak evidence, relevance, and caution.
- **Red:** `#ff695d` for unavailable analysis, conflicts, and escalation.
- **Green:** `#72d89b` for healthy status, cited drafts, and confirmed feedback.
- **Focus:** light blue (`#8bcaff`) with a two-pixel outline and two-pixel offset.

Color never carries meaning alone. Decision banners pair color with an icon and explicit language; evidence status uses text and a border; health and feedback states include readable labels.

### Typography

Manrope Variable is the primary family, chosen for compact readability and a calm operational tone. IBM Plex Mono is reserved for identifiers, metrics, counts, scores, and source references. Headings are modest rather than promotional: most panel titles are `1rem`, while the brand is `1.35rem`. Small labels typically sit between `0.66rem` and `0.78rem`, with weight and spacing supplying hierarchy.

Use short line lengths for guidance and state copy. Long incident text belongs in the resizable description field; evidence excerpts are visually clamped on desktop to preserve scanability.

### Shape, spacing, and depth

The form language is precise and gently rounded:

- Panels use a 9px radius.
- Buttons and state banners use 7px.
- Inputs use 6px.
- Small step markers, citation chips, and evidence badges use 4–5px.

Spacing is compact and regular: 8px for control internals and small gaps, 12–16px for component padding, and 14–18px between major workbench regions. One-pixel rules establish structure. Avoid ornamental gradients, oversized radii, and decorative shadows; the visual authority comes from alignment, density, and evidence structure.

### Component behavior

- **Primary action:** solid light blue with dark text, high weight, a 38px desktop minimum, and a 44px mobile touch target. Disabled actions remain visible at reduced opacity and use a not-allowed cursor.
- **Secondary action:** raised slate with a stronger border; hover increases border and surface contrast.
- **Icon button:** transparent at rest, then gains a border and raised surface on hover. Every icon-only action requires an accessible name.
- **Fields:** dark inset surface, visible border, blue caret, descriptive placeholder, persistent help, and inline invalid guidance.
- **Decision banner:** green for a cited draft and red for escalation, always with a distinct icon, heading, and explanation.
- **Evidence ledger:** a real table on larger screens, with source links, relevance, supporting excerpts, and explicit “Cited” or “Context” status.

## Responsive behavior

At widths up to 1180px, secondary header information is reduced: global search and corpus status are hidden, the queue narrows to 250px, and the case and analysis panels stack. The provider remains visible so operators still understand the active analysis context.

At widths up to 760px, the queue becomes a full-height overlay between the header and action dock. Selecting a case or starting a new one closes it automatically. Brand decoration and the provider label collapse, while the active workspace becomes a single-column flow.

On narrow screens:

- Product area and corpus context stack.
- Confidence metrics become rows rather than columns.
- Escalation rationale and missing signals stack with a divider.
- The evidence table becomes labeled records; its header is visually hidden and each cell exposes its own label.
- The bottom action dock wraps, hides the duplicated case summary, and lets Analyze occupy available width.
- Extra bottom padding prevents fixed controls from covering content.

The minimum supported viewport is 320px. Preserve active-case work before queue context whenever space is constrained.

## Accessibility

Use native landmarks and controls: header, aside, main, section, footer, form, buttons, links, and a data table. Associate panel headings with their sections, labels with fields, help and count text through `aria-describedby`, and validation through `aria-invalid` plus visible error copy.

All keyboard-focusable controls use the same high-contrast `:focus-visible` outline. Queue selection exposes `aria-pressed`; the queue toggle exposes `aria-controls` and `aria-expanded`; analysis updates are announced through a polite live region. Decorative icons are hidden from assistive technology, while icon-only controls receive explicit labels.

Keep state meaning redundant across text, shape, icons, and color. External evidence links identify their source visually and open with safe link attributes. Reduced-motion preference shortens animations and transitions to effectively immediate changes. Do not remove visible focus, persistent labels, field guidance, or semantic table structure for visual simplicity.

## Interaction states

### Queue

- **Loading:** spinner with “Loading cases.”
- **Unavailable:** clear error copy while preserving New case as a usable route.
- **No matches:** a direct empty-search message.
- **Selected:** slate-blue fill, blue inset marker, and programmatic pressed state.

### Case input

New case clears the selection and analysis, then moves focus to Subject. Subject and description show minimum-length guidance, invalid state, and a live character count. Analyze remains disabled until both minimums are met and is also disabled during analysis.

Changing cases cancels in-flight work and prevents a late result from appearing under the wrong case. Preserve this binding whenever analysis becomes asynchronous or navigable.

### Analysis

- **Idle:** explains the evidence pipeline and expected decision contract.
- **Loading:** cycles through retrieval, reranking, and safety-check stages, with progress and a reminder that case text is transient.
- **Error:** distinguishes provider rate limiting from general service failure and gives a recoverable next step.
- **Draft:** shows a green decision banner, three evidence factors, cited resolution steps, and source identifiers.
- **Escalation:** shows a red decision banner, the reason Recall stopped, and the signals to collect before handoff.
- **No evidence:** states that unsupported context was not sent to generation.

### Feedback

Positive feedback records directly. Negative feedback expands a labeled correction field and requires content before sending. Recorded and failed states are explicit. “Use draft” records acceptance without claiming a time-saving metric the operator did not provide.

## Rationale and revisit conditions

The dense workbench is intentional: operators need case context, the decision, and provenance close together. The dark operational palette lowers glare during repeated triage, while blue is reserved for action and navigation and semantic colors distinguish draft, caution, and escalation. The evidence ledger receives first-class space because inspectability is the product, not supporting decoration.

Revisit this system when:

- usability testing shows that the queue, case, decision, and evidence need a different default hierarchy;
- production tickets add attachments, identity, collaboration, or a separate ingestion flow;
- background jobs and a result inbox replace synchronous, case-bound requests;
- calibrated outcome data supports a different confidence presentation or threshold model;
- authenticated retention changes the transient-case privacy contract;
- measured accessibility testing reveals problems with the compact type scale, table transformation, focus order, or fixed action dock;
- the corpus or evidence set grows enough that the ledger needs filtering, expansion, or comparison views.

Any revision must preserve three invariants: evidence remains inspectable, escalation remains a valid outcome, and the human operator retains the decision point.
