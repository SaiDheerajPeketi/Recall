import {
  AlertTriangle,
  ArrowUpRight,
  Check,
  CheckCircle2,
  ChevronRight,
  CircleAlert,
  ClipboardCheck,
  Database,
  FileSearch,
  Gauge,
  LoaderCircle,
  Menu,
  Plus,
  Search,
  Send,
  ServerCog,
  ShieldCheck,
  ThumbsDown,
  ThumbsUp,
  X,
} from "lucide-react";
import { FormEvent, useEffect, useMemo, useRef, useState } from "react";

import {
  analyzeTicket,
  ApiError,
  DemoTicket,
  getDemoTickets,
  getHealth,
  submitFeedback,
  TicketAnalysisResponse,
  TicketAnalyzeRequest,
} from "./api/client";

type AnalysisState = "idle" | "loading" | "complete" | "error";
type QueueState = "loading" | "ready" | "error";

const blankCase: TicketAnalyzeRequest = {
  subject: "",
  description: "",
  product_area: "",
};

const loadingStages = [
  "Searching dense and lexical indexes",
  "Reranking the strongest evidence",
  "Checking citations and answer safety",
];

function formatScore(value: number): string {
  return `${Math.round(value * 100)}%`;
}

function caseCode(ticket?: DemoTicket): string {
  return ticket?.id ?? "NEW CASE";
}

export default function App() {
  const [tickets, setTickets] = useState<DemoTicket[]>([]);
  const [queueState, setQueueState] = useState<QueueState>("loading");
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [form, setForm] = useState<TicketAnalyzeRequest>(blankCase);
  const [analysisState, setAnalysisState] = useState<AnalysisState>("idle");
  const [result, setResult] = useState<TicketAnalysisResponse | null>(null);
  const [errorMessage, setErrorMessage] = useState("");
  const [loadingStage, setLoadingStage] = useState(0);
  const [health, setHealth] = useState<"checking" | "ready" | "degraded">("checking");
  const [provider, setProvider] = useState("Provider");
  const [feedbackState, setFeedbackState] = useState<
    "idle" | "comment" | "sending" | "recorded" | "error"
  >("idle");
  const [feedbackComment, setFeedbackComment] = useState("");
  const [queueOpen, setQueueOpen] = useState(() => window.innerWidth > 760);
  const [searchQuery, setSearchQuery] = useState("");
  const analysisController = useRef<AbortController | null>(null);
  const analysisVersion = useRef(0);
  const feedbackVersion = useRef(0);
  const menuButton = useRef<HTMLButtonElement | null>(null);

  const selectedTicket = useMemo(
    () => tickets.find((ticket) => ticket.id === selectedId),
    [selectedId, tickets],
  );

  const visibleTickets = useMemo(() => {
    const query = searchQuery.trim().toLowerCase();
    if (!query) return tickets;
    return tickets.filter((ticket) =>
      [ticket.id, ticket.subject, ticket.description, ticket.product_area]
        .join(" ")
        .toLowerCase()
        .includes(query),
    );
  }, [searchQuery, tickets]);

  useEffect(() => {
    let active = true;
    Promise.allSettled([getDemoTickets(), getHealth()]).then(([demoResult, healthResult]) => {
      if (!active) return;
      if (demoResult.status === "fulfilled") {
        setTickets(demoResult.value);
        setQueueState("ready");
        const first = demoResult.value[0];
        if (first) selectTicket(first);
      } else {
        setQueueState("error");
      }
      if (healthResult.status === "fulfilled") {
        setHealth(healthResult.value.status);
        const providerStatus = healthResult.value.checks.provider;
        setProvider(providerStatus === "ready" ? "Provider ready" : "Provider unavailable");
      } else {
        setHealth("degraded");
        setProvider("Status unavailable");
      }
    });
    return () => {
      active = false;
      analysisController.current?.abort();
    };
  }, []);

  useEffect(() => {
    if (analysisState !== "loading") return;
    const interval = window.setInterval(() => {
      setLoadingStage((current) => (current + 1) % loadingStages.length);
    }, 1800);
    return () => window.clearInterval(interval);
  }, [analysisState]);

  function selectTicket(ticket: DemoTicket) {
    setSelectedId(ticket.id);
    setForm({
      subject: ticket.subject,
      description: ticket.description,
      product_area: ticket.product_area,
    });
    if (window.innerWidth <= 760) {
      setQueueOpen(false);
      window.requestAnimationFrame(() => document.getElementById("case-subject")?.focus());
    }
    resetAnalysis();
  }

  function startNewCase() {
    setSelectedId(null);
    setForm(blankCase);
    if (window.innerWidth <= 760) setQueueOpen(false);
    resetAnalysis();
    window.requestAnimationFrame(() => document.getElementById("case-subject")?.focus());
  }

  function resetAnalysis() {
    analysisController.current?.abort();
    analysisController.current = null;
    analysisVersion.current += 1;
    feedbackVersion.current += 1;
    setAnalysisState("idle");
    setResult(null);
    setErrorMessage("");
    setFeedbackState("idle");
    setFeedbackComment("");
  }

  async function handleAnalyze(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    analysisController.current?.abort();
    const controller = new AbortController();
    const version = analysisVersion.current + 1;
    analysisVersion.current = version;
    analysisController.current = controller;
    setAnalysisState("loading");
    setLoadingStage(0);
    setResult(null);
    setErrorMessage("");
    feedbackVersion.current += 1;
    setFeedbackState("idle");
    try {
      const analysis = await analyzeTicket(
        {
          subject: form.subject.trim(),
          description: form.description.trim(),
          product_area: form.product_area?.trim() || null,
        },
        controller.signal,
      );
      if (controller.signal.aborted || analysisVersion.current !== version) return;
      setResult(analysis);
      setAnalysisState("complete");
      setProvider(`${analysis.provider} · ${analysis.provider_model}`);
    } catch (error) {
      if (controller.signal.aborted || analysisVersion.current !== version) return;
      const rateLimited = error instanceof ApiError && error.status === 429;
      setErrorMessage(
        rateLimited
          ? "The model provider is rate limited. Wait a moment, then analyze the case again."
          : "Recall could not analyze this case. Check service health and try again.",
      );
      setAnalysisState("error");
    } finally {
      if (analysisController.current === controller) analysisController.current = null;
    }
  }

  async function sendFeedback(
    helpfulness: "helpful" | "not_helpful",
    accepted: boolean,
  ) {
    if (!result) return;
    const version = feedbackVersion.current;
    setFeedbackState("sending");
    try {
      await submitFeedback({
        analysis_id: result.analysis_id,
        helpfulness,
        accepted,
        correction: helpfulness === "not_helpful" ? feedbackComment.trim() : null,
        comment: null,
        minutes_saved: null,
      });
      if (feedbackVersion.current !== version) return;
      setFeedbackState("recorded");
    } catch {
      if (feedbackVersion.current !== version) return;
      setFeedbackState("error");
    }
  }

  const canAnalyze =
    form.subject.trim().length >= 3 &&
    form.description.trim().length >= 10 &&
    analysisState !== "loading";

  return (
    <div className="app-frame">
      <header className="topbar">
        <button
          ref={menuButton}
          className="icon-button menu-button"
          aria-label={queueOpen ? "Close incident queue" : "Open incident queue"}
          aria-controls="incident-queue"
          aria-expanded={queueOpen}
          onClick={() => setQueueOpen((current) => !current)}
        >
          <Menu size={19} />
        </button>
        <div className="brand-lockup">
          <span className="brand-name">Recall</span>
          <span className="brand-divider" aria-hidden="true" />
          <span className="brand-description">Support copilot</span>
        </div>
        <label className="global-search">
          <Search size={16} />
          <span className="sr-only">Search demo cases</span>
          <input
            value={searchQuery}
            onChange={(event) => setSearchQuery(event.target.value)}
            placeholder="Search demo cases"
          />
        </label>
        <div className="system-status" aria-label={`System status: ${health}`}>
          <span className={`health-dot health-dot--${health}`} />
          <span>Corpus</span>
          <strong>{health === "ready" ? "ready" : health}</strong>
        </div>
        <div className="provider-status">
          <Database size={17} />
          <span>{provider}</span>
        </div>
      </header>

      <div className={`workbench ${queueOpen ? "" : "workbench--queue-closed"}`}>
        <aside
          id="incident-queue"
          className={`queue-panel ${queueOpen ? "queue-panel--open" : ""}`}
          aria-label="Incident queue"
        >
          <div className="queue-heading">
            <div>
              <h2>Incident queue</h2>
              <p>{tickets.length} safe demo cases</p>
            </div>
            <button
              className="icon-button"
              aria-label="Close queue"
              onClick={() => {
                setQueueOpen(false);
                window.requestAnimationFrame(() => menuButton.current?.focus());
              }}
            >
              <X size={17} />
            </button>
          </div>
          <button className="new-case-button" onClick={startNewCase}>
            <Plus size={16} />
            New case
          </button>
          <div className="queue-scope">
            <span>Open demo cases</span>
            <strong>{visibleTickets.length}</strong>
          </div>
          <div className="queue-list">
            {queueState === "loading" && (
              <div className="queue-message">
                <LoaderCircle className="spin" size={17} /> Loading cases
              </div>
            )}
            {queueState === "error" && (
              <div className="queue-message queue-message--error">
                Demo queue unavailable. New case still works.
              </div>
            )}
            {queueState === "ready" && visibleTickets.length === 0 && (
              <div className="queue-message">No demo cases match this search.</div>
            )}
            {visibleTickets.map((ticket) => (
              <button
                className={`queue-item ${selectedId === ticket.id ? "queue-item--selected" : ""}`}
                key={ticket.id}
                onClick={() => selectTicket(ticket)}
                aria-pressed={selectedId === ticket.id}
              >
                <span className="queue-item-copy">
                  <span className="queue-item-meta">
                    <strong>{ticket.id}</strong>
                    <span>{ticket.product_area}</span>
                  </span>
                  <span className="queue-item-subject">{ticket.subject}</span>
                  <span className="queue-item-description">{ticket.description}</span>
                </span>
                <ChevronRight size={15} aria-hidden="true" />
              </button>
            ))}
          </div>
        </aside>

        <main className="workspace">
          <div className="case-toolbar">
            <div>
              <span className="case-code">{caseCode(selectedTicket)}</span>
              <span className="case-state">{selectedTicket ? "Demo case" : "Unsaved input"}</span>
            </div>
            <span className="privacy-note">
              <ShieldCheck size={15} /> Case text is processed once and not stored
            </span>
          </div>

          <div className="primary-grid">
            <section className="case-panel" aria-labelledby="case-input-heading">
              <div className="section-heading">
                <div>
                  <h1 id="case-input-heading">{selectedTicket ? "Review case" : "New case"}</h1>
                  <p>Describe the incident. Analyze runs the complete evidence pipeline.</p>
                </div>
                <FileSearch size={20} aria-hidden="true" />
              </div>
              <form id="case-form" className="case-form" onSubmit={handleAnalyze}>
                <label htmlFor="case-subject">Subject</label>
                <input
                  id="case-subject"
                  value={form.subject}
                  onChange={(event) => setForm({ ...form, subject: event.target.value })}
                  aria-describedby="case-subject-help"
                  aria-invalid={form.subject.length > 0 && form.subject.trim().length < 3}
                  placeholder="What is failing?"
                  required
                  minLength={3}
                  maxLength={160}
                />
                <span
                  id="case-subject-help"
                  className={`field-help ${form.subject.length > 0 && form.subject.trim().length < 3 ? "field-help--error" : ""}`}
                >
                  At least 3 characters.
                </span>
                <div className="field-row">
                  <div>
                    <label htmlFor="case-area">Product area</label>
                    <input
                      id="case-area"
                      value={form.product_area ?? ""}
                      onChange={(event) =>
                        setForm({ ...form, product_area: event.target.value })
                      }
                      placeholder="Optional"
                      maxLength={80}
                    />
                  </div>
                  <div className="field-context" aria-label="Current scope">
                    <ServerCog size={16} />
                    <span>PostgreSQL + pgvector corpus</span>
                  </div>
                </div>
                <label htmlFor="case-description">Description</label>
                <textarea
                  id="case-description"
                  value={form.description}
                  onChange={(event) => setForm({ ...form, description: event.target.value })}
                  aria-describedby="case-description-help case-description-count"
                  aria-invalid={form.description.length > 0 && form.description.trim().length < 10}
                  placeholder="Include symptoms, timing, environment, and diagnostics already collected."
                  required
                  minLength={10}
                  maxLength={8000}
                />
                <div className="field-meta">
                  <span
                    id="case-description-help"
                    className={`field-help ${form.description.length > 0 && form.description.trim().length < 10 ? "field-help--error" : ""}`}
                  >
                    At least 10 characters.
                  </span>
                  <span id="case-description-count" className="character-count">
                    {form.description.length.toLocaleString()} / 8,000
                  </span>
                </div>
              </form>
            </section>

            <section className="analysis-panel" aria-labelledby="analysis-heading" aria-live="polite">
              <div className="section-heading section-heading--compact">
                <div>
                  <h2 id="analysis-heading">Recall analysis</h2>
                  <p>{result ? `Completed in ${(result.latency_ms / 1000).toFixed(1)}s` : "Evidence-bound output"}</p>
                </div>
                <Gauge size={20} aria-hidden="true" />
              </div>

              {analysisState === "idle" && <IdleAnalysis />}
              {analysisState === "loading" && (
                <div className="loading-analysis">
                  <div className="loading-mark">
                    <LoaderCircle className="spin" size={25} />
                  </div>
                  <h3>Analyzing case</h3>
                  <p>{loadingStages[loadingStage]}</p>
                  <div className="loading-track"><span style={{ transform: `scaleX(${(loadingStage + 1) / 3})` }} /></div>
                  <small>Ticket text remains transient throughout this request.</small>
                </div>
              )}
              {analysisState === "error" && (
                <div className="analysis-error">
                  <CircleAlert size={24} />
                  <div>
                    <h3>Analysis unavailable</h3>
                    <p>{errorMessage}</p>
                  </div>
                </div>
              )}
              {analysisState === "complete" && result && <AnalysisResult result={result} />}
            </section>
          </div>

          <EvidenceLedger result={result} analysisState={analysisState} />
        </main>
      </div>

      <footer className="action-dock">
        <div className="dock-case">
          <span>{caseCode(selectedTicket)}</span>
          <strong>{form.subject || "Untitled new case"}</strong>
        </div>
        <div className="dock-actions">
          {feedbackState === "comment" && (
            <div className="feedback-comment">
              <label htmlFor="feedback-comment">What needs work?</label>
              <input
                id="feedback-comment"
                value={feedbackComment}
                onChange={(event) => setFeedbackComment(event.target.value)}
                placeholder="Missing evidence, unsafe step, wrong category…"
                maxLength={2000}
              />
              <button
                className="secondary-button"
                disabled={!feedbackComment.trim()}
                onClick={() => sendFeedback("not_helpful", false)}
              >
                <Send size={15} /> Send
              </button>
            </div>
          )}
          {result && feedbackState !== "comment" && feedbackState !== "recorded" && (
            <div className="feedback-actions" aria-label="Analysis feedback">
              <span>Was this useful?</span>
              <button
                className="icon-button"
                aria-label="Mark analysis useful"
                disabled={feedbackState === "sending"}
                onClick={() => sendFeedback("helpful", false)}
              >
                <ThumbsUp size={17} />
              </button>
              <button
                className="icon-button"
                aria-label="Mark analysis as needing work"
                disabled={feedbackState === "sending"}
                onClick={() => setFeedbackState("comment")}
              >
                <ThumbsDown size={17} />
              </button>
            </div>
          )}
          {feedbackState === "recorded" && <span className="feedback-confirmed"><Check size={15} /> Feedback recorded</span>}
          {feedbackState === "error" && <span className="feedback-failed">Feedback was not saved. Try again.</span>}
          {result?.action === "draft" && feedbackState !== "recorded" && (
            <button
              className="secondary-button"
              disabled={feedbackState === "sending"}
              onClick={() => sendFeedback("helpful", true)}
            >
              <ClipboardCheck size={16} /> Use draft
            </button>
          )}
          <button className="primary-button" type="submit" form="case-form" disabled={!canAnalyze}>
            {analysisState === "loading" ? <LoaderCircle className="spin" size={17} /> : <FileSearch size={17} />}
            {analysisState === "loading" ? "Analyzing" : "Analyze case"}
          </button>
        </div>
      </footer>
    </div>
  );
}

function IdleAnalysis() {
  return (
    <div className="idle-analysis">
      <div className="idle-symbol"><Search size={25} /></div>
      <h3>Ready for evidence review</h3>
      <p>Recall will search the pinned support corpus and choose a cited draft or an explicit escalation.</p>
      <ul>
        <li><Check size={15} /> Hybrid dense and BM25 retrieval</li>
        <li><Check size={15} /> Cross-encoder reranking</li>
        <li><Check size={15} /> Citation and evidence-strength gates</li>
      </ul>
    </div>
  );
}

function AnalysisResult({ result }: { result: TicketAnalysisResponse }) {
  const isEscalation = result.action === "escalate";
  return (
    <div className="analysis-result">
      <div className={`decision-banner decision-banner--${isEscalation ? "escalate" : "draft"}`}>
        {isEscalation ? <AlertTriangle size={22} /> : <CheckCircle2 size={22} />}
        <div>
          <h3>{isEscalation ? "Escalate · evidence incomplete" : "Cited resolution ready"}</h3>
          <p>{result.summary}</p>
        </div>
      </div>
      <div className="confidence-grid">
        <Metric label="Evidence strength" value={formatScore(result.confidence.evidence_strength)} tone={result.confidence.label} />
        <Metric label="Source diversity" value={formatScore(result.confidence.source_diversity)} />
        <Metric label="Citation coverage" value={formatScore(result.confidence.citation_coverage)} />
      </div>
      {isEscalation ? (
        <div className="handoff-grid">
          <div>
            <h4>Why Recall stopped</h4>
            <ul className="signal-list">
              {result.escalation_rationale.map((reason) => <li key={reason}><CircleAlert size={15} />{reason}</li>)}
            </ul>
          </div>
          <div>
            <h4>Collect before handoff</h4>
            <ul className="signal-list signal-list--missing">
              {result.missing_signals.map((signal) => <li key={signal}><AlertTriangle size={15} />{signal}</li>)}
            </ul>
          </div>
        </div>
      ) : (
        <div className="resolution-steps">
          <h4>Cited resolution</h4>
          {result.steps.map((step, index) => (
            <article className="resolution-step" key={`${step.title}-${index}`}>
              <span className="step-number">{index + 1}</span>
              <div>
                <h5>{step.title}</h5>
                <p>{step.instruction}</p>
                <div className="citation-list">
                  {step.citations.map((citation) => <code key={citation}>{citation}</code>)}
                </div>
              </div>
            </article>
          ))}
        </div>
      )}
    </div>
  );
}

function Metric({ label, value, tone }: { label: string; value: string; tone?: string }) {
  return (
    <div className="metric">
      <strong className={tone ? `metric-value metric-value--${tone}` : "metric-value"}>{value}</strong>
      <span>{label}</span>
    </div>
  );
}

function EvidenceLedger({
  result,
  analysisState,
}: {
  result: TicketAnalysisResponse | null;
  analysisState: AnalysisState;
}) {
  return (
    <section className="evidence-ledger" aria-labelledby="evidence-heading">
      <div className="ledger-heading">
        <div>
          <h2 id="evidence-heading">Evidence and proposed actions</h2>
          <p>Every recommendation must map to a retrieved source passage.</p>
        </div>
        <span className="evidence-count">{result?.evidence.length ?? 0} passages</span>
      </div>
      {!result && (
        <div className="ledger-empty">
          {analysisState === "loading" ? <LoaderCircle className="spin" size={21} /> : <Database size={21} />}
          <div>
            <strong>{analysisState === "loading" ? "Building the evidence set" : "No evidence selected yet"}</strong>
            <span>{analysisState === "loading" ? "Results appear here after reranking." : "Analyze the active case to inspect source passages."}</span>
          </div>
        </div>
      )}
      {result && result.evidence.length === 0 && (
        <div className="ledger-empty ledger-empty--warning">
          <AlertTriangle size={21} />
          <div><strong>No relevant evidence</strong><span>The case was escalated without sending unsupported context to generation.</span></div>
        </div>
      )}
      {result && result.evidence.length > 0 && (
        <div className="evidence-table-wrap">
          <table>
            <thead>
              <tr>
                <th>#</th>
                <th>Evidence / source</th>
                <th>Relevance</th>
                <th>Supports</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {result.evidence.map((evidence, index) => {
                const used = result.steps.some((step) => step.citations.includes(evidence.chunk_id));
                return (
                  <tr key={evidence.chunk_id}>
                    <td data-label="Evidence number">{index + 1}</td>
                    <td data-label="Evidence and source">
                      <a href={evidence.url} target="_blank" rel="noreferrer">
                        <Database size={16} />
                        <span><strong>{evidence.title}</strong><small>{evidence.heading} · {evidence.chunk_id}</small></span>
                        <ArrowUpRight size={13} />
                      </a>
                    </td>
                    <td data-label="Relevance"><strong className="score-value">{formatScore(evidence.relevance)}</strong></td>
                    <td data-label="Supports"><span className="evidence-excerpt">{evidence.excerpt}</span></td>
                    <td data-label="Status"><span className={`evidence-status evidence-status--${used ? "used" : "context"}`}>{used ? "Cited" : "Context"}</span></td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
