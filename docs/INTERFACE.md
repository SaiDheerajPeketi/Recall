# Interface direction

Recall uses an incident-command workbench rather than a generic dashboard. The desktop view keeps the queue, active case, analysis decision, source evidence, and next action visible together. On smaller screens, the order becomes case input, analysis decision, evidence, then queue.

## Visual language

- Matte navy surfaces and fine slate dividers establish a focused operations environment.
- Amber communicates incomplete evidence; red is reserved for unsafe or blocked resolution states; green confirms healthy or supported states.
- Dense information uses alignment, labels, and borders rather than decorative cards.
- Icons support visible text and never replace critical labels.
- Motion is limited to state changes and respects reduced-motion preferences.

## New case behavior

The queue's primary action opens an empty case composer with subject, product area, and description fields. **Analyze case** submits those values to `/api/v1/tickets/analyze`. While the pipeline runs, the analysis pane explains the current stage. A supported result replaces it with a cited draft; an unsupported result replaces it with the escalation console and missing-evidence signals.

The initial implementation is based on the approved escalation-console comp. The comp is design reference only and is not shipped as a product asset.

