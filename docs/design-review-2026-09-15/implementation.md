# Review implementation — September 16, 2026

The user authorized working through the review and then required a simple UI.
This implementation keeps three destinations: Overview, Plan, and Sources.

## Delivered

| Review issue | Implementation |
|---|---|
| Invisible defaults and dates | Explicit light/dark input and autofill colors, native color scheme, visible keyboard focus. Verified with a subscription drawer at desktop and 390px phone width. |
| Mechanism-first homepage | Empty Overview leads with “Plan your AI and engineering spend,” one source action, a sample, and a manual-plan link. |
| Credentials before value | Public `/demo` now contains an interactive, clearly labeled sample plan. Sample saves are in-memory only and make no account API requests. |
| AI sources buried | Compact AI API, AI subscription, and cloud/tool groups, in that order. |
| Repeated source setup sections | Removed the redundant hero, source count cards, credential/evidence repetition, and empty-state footer. |
| Unclear manual entry | “Add monthly bill” and “Manually maintained”; manual amounts are not called credentials. |
| Setup guidance missing | Expandable official setup links, key scope, coverage/exclusions, and import/refresh expectations in API drawers. No keys or live provider access were added. |
| Budgets buried | Overview displays account budget next to recorded cost and trend estimate; the account link opens existing detail/budget editing. |
| Static “Current” status | Replaced with actual source records, health, period coverage, and explicit unknown/unavailable states. |
| Scenarios imply confidence | Lower/higher-growth labels, basis messages and explicit scenario language. No statistical interval or automatic spend cap is claimed. |
| Plan assumptions lost | User-scoped immutable plan revisions with optimistic version checking and export. |
| No owned action | Collapsed action section records title, owner, criteria, lifecycle, and result. Measured status requires windows, costs, positive accepted-task counts, quality review and confounder notes. |
| Crowded UI | Comparison is one input panel plus one result panel. Assumptions, action measurement, revisions and sample source charts are progressive disclosures. |

## Boundaries

This is a manual, inspectable planning slice. It does not implement automated token/model
pricing, workload attribution, Kubernetes observation, automatic optimization detection,
provider enforcement, external ticket writes, or independently verified savings.
The user's requested simplicity led to monthly baseline + usage-change + reduction inputs,
rather than a large token/cache/model configuration form. Fixed subscription costs are
separate. User-labeled reported baselines require evidence notes and remain explicitly
user-entered. No fixture is presented as customer demand or measured advantage.

Plan budgets and existing account budgets are separate concepts. The UI says so;
plan saves do not mutate account budgets. A future allocation model must define their
relationship before automatically linking them.

## Verification

- Frontend: 11 suites / 63 tests passed, including account budgets, AI setup, scenario
  arithmetic, sample isolation, save/error handling, unknown-versus-zero, and account scope.
- API: 114 tests passed, including plan round trips, immutable history, stale-save
  conflicts, cross-user isolation, validation, action requirements, and idempotent migration.
- Production frontend build passed. Existing Create React App/dependency deprecation
  warnings remain.
- Browser: changed a sample assumption and saved a sample revision; used an isolated
  local fixture API to save a real plan, reload and restore it, then save a Testing action
  as revision 2. Verified populated Overview and source drawer keyboard focus/escape.
- Browser: checked desktop and 390×844 phone layouts, readable date/default fields,
  and the final public demo. Screenshots are under `after/`.
- The temporary local fixture harness was removed and the original authenticated app
  entry restored before the final build. Production authentication was not bypassed.
- SQLite covered migration execution and persistence. Production PostgreSQL migration,
  live billing credentials/imports, and production deployment were not exercised.

The initial full-suite run used sandbox mode globally, which intentionally disables
provider behavior and caused provider-test failures. Re-running with an isolated SQLite
connection and normal application mode passed all 114 tests; no provider credentials
were used.

## Next discovery work, prepared for execution

Working hypothesis: an engineering lead at a small team using multiple AI APIs who owns
a monthly engineering/workload budget. This is not a validated buyer selection.

Use five interviews and two explicitly consenting design partners. For each interview:

1. Walk through the last real AI budget decision and its deadline.
2. Identify the owner, approver, current tool, time spent, and missing information.
3. Ask them to use the sample plan; observe whether they distinguish budget, recorded
   spend, scenario, and assumed reduction without explanation.
4. Ask what evidence would make them accept or reject one proposed change.
5. Record the buying trigger, budget authority, incumbent, and willingness to pay as
   stated; leave unknowns unknown.

For each partner, obtain written scope for an anonymized fixture: two chosen sources,
account/period/currency, permitted fields, retention, allowed processing environment,
and who can inspect it. Do not collect prompts, credentials, or customer content.
Reconcile included amounts and preserve exclusions. Choose usage/outcome instrumentation
only after the first decision requires it.

Pilot worksheet:

- Participant role / buyer / daily user:
- Decision and deadline:
- Existing process and baseline time:
- Permitted sources and fixture references:
- Meaning of an accepted task and who reviews it:
- Quality and latency limits:
- Time to usable plan:
- Unexplained reconciliation difference:
- Action accepted/rejected and reason:
- Measured cost change, volume, price changes, quality and confounders:
- Payment/procurement evidence:

Suggested targets remain provisional: a usable plan within 15 minutes after data is
available; no unexplained difference in supported fixture totals; an owner able to decide
without rebuilding the evidence. Record failures as well as successes.

Proposed roadmap decision: planning is the user-facing workflow; allocation and action
integrity support it. Validate an API-first workload before requiring Kubernetes. This
proposal is documented here without silently rewriting the Product Brain discovery gates.
Actual interviews, permitted customer fixtures, willingness to pay, and competitive proof
remain outstanding; they cannot be completed with synthetic UI tests.
