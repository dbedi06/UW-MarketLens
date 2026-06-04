// /uw — UW Community Impact framing page. Three concrete workflows
// the project supports, with real demo links into the department-
// filtered library / citation / CSV surfaces. Scope statement +
// "honest delta from the proposal" section keep the page from
// overclaiming relative to the original DYOP pitch.

import { Link } from "react-router-dom";
import PageShell from "../ui/PageShell";
import SectionHeading from "../ui/SectionHeading";

type Workflow = {
  persona: string;
  goal: string;
  steps: string[];
  cta_label: string;
  cta_to: string;
};

const WORKFLOWS: Workflow[] = [
  {
    persona: "A Political Science (POLS) instructor",
    goal: "Build a reading list of prediction markets relevant to your course — markets students can analyse for the term paper without you having to vet each one by hand.",
    steps: [
      "Open the Library page and pick the POLS department tab.",
      "MarketLens filters the library to markets the LLM tagger has classified for that department, with a reliability score on each row.",
      "Click any market to see the full reliability report — plain-language reasons, anomaly chart, subscores, snapshot permalink.",
      "Drop the snapshot permalink into the syllabus PDF. The permalink re-renders the identical verdict at that URL — deterministically for mock mode, and as long as the ingestion cache holds the source data for live mode (a cold cache returns 503 rather than silently substituting different data).",
    ],
    cta_label: "Filter the library by POLS →",
    cta_to: "/library?dept=POLS",
  },
  {
    persona: "An Economics or Evans School researcher",
    goal: "Cite a Polymarket market in a paper or policy memo with a reliability flag and a stable URL — not a screenshot of a price that will be stale by the time peer review comes back.",
    steps: [
      "Look up the market URL from the Home page. The full pipeline (S1–S7) scores it: liquidity, trading-pattern integrity, resolution corroboration.",
      "The verdict card shows the band (HIGH / MEDIUM / LOW) plus the reliability flag (RELIABLE / USE WITH CAUTION / NOT RECOMMENDED).",
      "Copy the citation in APA, MLA, or BibTeX — or download .ris for Zotero / Mendeley / EndNote. The reliability flag is embedded in every format.",
      "Use the snapshot permalink as the URL in your bibliography. It pins the score to the date you cited; the report at that URL stays stable as long as the ingestion cache holds the source data (deterministic forever for mock-mode reports).",
    ],
    cta_label: "Open a sample report →",
    cta_to: "/market?url=https%3A%2F%2Fpolymarket.com%2Fevent%2Fworld-cup-winner",
  },
  {
    persona: "An Information School (INFO) data-methods class",
    goal: "Hand students a real CSV of prediction markets they can analyse in R or Python without having to write their own Polymarket scraper.",
    steps: [
      "Open the Library page and apply whatever fits the assignment — the POLS/ECON/INFO/EVANS department tabs or a question search.",
      "Click Download CSV. The export includes market URL, question, reliability score, band, departments, and verified flag.",
      "Drop the CSV into the assignment brief. Students can join it to other course datasets, run descriptive stats, or use it as a starting point for their own analysis.",
      "Every row has a stable Polymarket URL — students can navigate from a row in the CSV back to the live market for follow-up.",
    ],
    cta_label: "Open the Library →",
    cta_to: "/library?dept=INFO",
  },
];

export default function UwPage() {
  return (
    <PageShell wide>
      <SectionHeading
        eyebrow="For the UW community"
        title="Three workflows MarketLens supports"
        sub="Prediction markets are increasingly cited in UW coursework — Evans School policy memos, Economics papers, iSchool data projects, Political Science forecasting. Students have no academic-grade way to tell a high-quality market signal from low-liquidity noise or manipulated price action, and Polymarket has no incentive to evaluate its own integrity. MarketLens fills that gap. The workflows below show what the department-filtered library, citation, and CSV-export surfaces are for."
      />

      <section className="mt-10 space-y-10">
        {WORKFLOWS.map((wf) => (
          <article
            key={wf.persona}
            className="border-t-2 border-ink pt-6 sm:flex sm:items-start sm:gap-12"
          >
            <header className="sm:w-72 sm:shrink-0">
              <div className="caption">Use case</div>
              <h3 className="mt-1 font-sans text-xl font-extrabold
                tracking-tight text-ink">
                {wf.persona}
              </h3>
              <p className="mt-2 text-sm leading-relaxed text-ink/65">
                {wf.goal}
              </p>
            </header>
            <div className="mt-5 flex-1 sm:mt-0">
              <ol className="mt-1 space-y-3 text-sm leading-relaxed
                text-ink/80">
                {wf.steps.map((step, i) => (
                  <li key={i} className="flex gap-3">
                    <span className="numeral w-6 shrink-0 text-base
                      text-brand-600">
                      {i + 1}
                    </span>
                    <span>{step}</span>
                  </li>
                ))}
              </ol>
              <Link
                to={wf.cta_to}
                className="mt-5 inline-flex items-center font-mono text-xs
                  font-medium uppercase tracking-wider text-brand-600
                  hover:text-brand-700 hover:underline underline-offset-4"
              >
                {wf.cta_label}
              </Link>
            </div>
          </article>
        ))}
      </section>

      <section className="mt-12 border-t border-line pt-8">
        <h2 className="section-title">Scope statement</h2>
        <div className="mt-5 grid gap-px border border-line bg-line
          sm:grid-cols-2">
          <div className="bg-paper p-6">
            <div className="font-sans font-bold text-good">
              In scope, working today
            </div>
            <ul className="mt-2 space-y-1.5 text-sm leading-relaxed
              text-ink/70">
              <li>• Department filter (POLS / ECON / INFO / EVANS) on
                the library, with LLM-assigned department tags per
                market</li>
              <li>• APA / MLA / BibTeX / RIS citation generation with
                an embedded reliability flag</li>
              <li>• CSV export of the library for class-assignment
                use</li>
              <li>• Open-access deployment — no login, no NetID
                required, anyone can use it</li>
              <li>• Snapshot permalinks that re-render the identical
                report — deterministically for mock mode, and as long
                as the ingestion cache holds the source data for live
                mode (cold cache returns 503, never substitutes)</li>
            </ul>
          </div>
          <div className="bg-paper p-6">
            <div className="font-sans font-bold text-warn">
              Out of scope (honest about limits)
            </div>
            <ul className="mt-2 space-y-1.5 text-sm leading-relaxed
              text-ink/70">
              <li>• <b>UW NetID gating</b> — open-access by design;
                no SSO integration</li>
              <li>• <b>UW Libraries citation-tool integration</b> —
                RIS export works in any standard citation manager
                Libraries supports, but there's no direct "Send to
                UW Libraries" hook</li>
              <li>• <b>UW-curated dataset</b> — markets come from
                Polymarket's general catalogue, not a UW-faculty-
                curated reading list</li>
              <li>• <b>Faculty / course-staff verification</b> — the
                Admin route lets anyone approve LLM-suggested tags;
                no UW-affiliation check</li>
              <li>• <b>Self-hosted / self-trained LLMs</b> — Render's
                free tier can't run a model this size, so S4
                (resolution) and S5 (tagging) call the OpenRouter API
                (DeepSeek V4 Pro) rather than language models we host
                ourselves. The Isolation Forest anomaly detector (S3)
                <i> is</i> ours and runs on-box; only the
                language-model steps are outsourced.</li>
            </ul>
          </div>
        </div>
        <p className="mt-4 max-w-prose text-xs italic text-ink/45">
          The honest assessment: what's in scope is real and works
          end-to-end. What's out of scope would require partnerships
          (Libraries) or institutional buy-in (SSO) the project
          doesn't have. The department-filtered library and citation
          tooling are the UW connection that doesn't depend on either.
        </p>
      </section>

      <section className="mt-12 border-t border-line pt-8">
        <h2 className="section-title">Honest delta from the original proposal</h2>
        <p className="mt-2 max-w-prose text-sm text-ink/65">
          The DYOP proposal pitched a few things that turned out to be
          out of scope for a few-week student build — and, frankly,
          impossible on the free Render tier's hardware. What actually
          shipped:
        </p>
        <ul className="mt-4 space-y-2.5 text-sm leading-relaxed text-ink/75">
          <li>• <b>Self-run / self-trained LLMs</b> — Render's free
            tier can't host a model this size, so S4 (resolution) and
            S5 (tagging) call the OpenRouter API (DeepSeek V4 Pro).
            The hardware makes self-hosting a non-starter, not a
            choice.</li>
          <li>• <b>An auto-ingesting ≥1,000-market library</b> — an
            always-on pipeline at that scale needs compute and a
            persistent database the free dyno doesn't have (it sleeps
            after 15 minutes idle). We ship a curated seed plus
            markets you score on the fly; the scored ones live in
            memory and reset when the dyno restarts.</li>
          <li>• <b>Faculty endorsements / Spring-syllabus adoption</b>
            — aspirational in the proposal; not secured.</li>
          <li>• <b>A SUS usability study with ≥10 recruited testers</b>
            — replaced with a lighter heuristic evaluation (Nielsen,
            small reviewer panel). See the About page.</li>
          <li>• <b>≥80% LLM-judge agreement on 30 labeled markets</b>
            — the verified set is 12 cases, and S4 can't verify
            resolved historical markets through free-tier NewsAPI
            (no archival reporting), so the calibration is a sanity
            check, not a headline number.</li>
        </ul>
        <p className="mt-4 max-w-prose text-xs italic text-ink/45">
          None of these change what the tool does for a UW user today
          — they're scope and infrastructure honesty, not capability
          gaps in the shipped workflows above.
        </p>
      </section>

      <section className="mt-12 border-t border-line pt-8">
        <h2 className="section-title">Related pages</h2>
        <ul className="mt-4 space-y-2 text-sm text-ink/70">
          <li>
            <Link to="/about" className="text-brand-600
              hover:text-brand-700 hover:underline underline-offset-4">
              About — architecture, methodology, evaluation results
            </Link>
          </li>
          <li>
            <Link to="/library" className="text-brand-600
              hover:text-brand-700 hover:underline underline-offset-4">
              Library — browse markets, filter by department or
              course
            </Link>
          </li>
          <li>
            <Link to="/" className="text-brand-600 hover:text-brand-700
              hover:underline underline-offset-4">
              Home — look up any Polymarket URL
            </Link>
          </li>
        </ul>
      </section>
    </PageShell>
  );
}
