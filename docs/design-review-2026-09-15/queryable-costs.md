# Queryable costs and personal dashboards

Design direction recorded 2026-09-16 following founder feedback: users need to
query their cost data and build dashboards, while the UI stays simple.
This document is a proposed implementation scope, not shipped functionality.

## Product interaction

Explore a question → save the query → add it to a dashboard → plan against it.

Datadog's documented Cost Explorer supports querying and exporting a result to a
dashboard. Adopt that interaction pattern for InfraSpend's cross-provider
monitoring and engineering budget planning purpose.

- https://docs.datadoghq.com/cloud_cost_management/reporting/explorer/
- https://docs.datadoghq.com/cloud_cost_management/reporting/dashboards/

## Simple default experience

Navigation: Dashboards, Explore, Plan; Sources accessible through settings.
Ship an editable starter dashboard so new users do not face a blank canvas.
Keep source health visible on dashboards, with a direct link to manage sources.

Explore has a single query row:

`Spend | where Provider is OpenAI | group by Account | Last 6 months`

Below it: one chart and its data table. Chart choices initially: line, bar,
table, or single number. Actions: Save query and Add to dashboard.
Clicking a chart segment filters the table; clicking a widget opens its query
in Explore. Browser URLs retain the query so refresh and back navigation work.

Dashboards have a title, a shared date range, and Add chart. Start with a simple
grid and move-up/move-down controls. Keep widget configuration inside Explore;
avoid a second independent query editor in the dashboard builder.

## First working slice

1. Tenant-scoped query API over persisted monthly cost records. Support date
   range, provider/account filters, monthly buckets, grouping by provider or
   account, and explicit currency selection. Querying does not call provider
   APIs or trigger ingestion.
2. Discoverable filter values restricted to the signed-in user's records.
3. Explore with chart/table views of exactly the same result.
4. Persist saved queries and dashboards in the API. A widget stores a versioned
   query definition and display settings, not a screenshot or fixed result.
5. Add, edit, remove, and reorder widgets; reopen after reload and rerun queries
   against current persisted data. Dashboard dates override widget dates only
   when the widget is explicitly configured to follow the dashboard range.
6. Convert the existing Overview into a starter dashboard using this same query
   path. Existing Plan and Sources functionality stays accessible.

First acceptance workflow: filter OpenAI monthly spend, group by account, save
it as a bar chart, add a second provider widget, reload the dashboard, then open
either widget in Explore and change its query.

## Data boundaries

Current VendorMetrics records expose user, provider, account identifier, month,
cost, currency, and source period. They do not provide queryable model, team,
feature, request, or token dimensions. Do not render unsupported controls or
manufacture daily observations from monthly totals.

- Preserve unknown and missing periods instead of filling them with zero.
- Keep manual subscription bills distinct from metered API costs.
- Never sum currencies without an explicit conversion policy; unknown currency
  remains a separate unresolved category.
- Show source coverage and freshness alongside the result, including partial
  or failed ingestion with retained historical data.
- Validate bounded date ranges, grouping, filters, result size, and enum values
  server-side. No arbitrary SQL endpoint.
- Authorize query execution, dimension discovery, saved queries, dashboards,
  and widgets independently. IDs supplied by the client confer no access.

## Subsequent AI planning capabilities

Preserve provider-supported daily billing and model/project dimensions during
ingestion before exposing those fields in Explore. Add team/feature allocation
only with an explicit mapping and a visible unallocated group.

Attach a budget or scenario to a saved query so the same scope answers both
"what did this cost?" and "what happens if usage doubles?" Freeze the baseline,
source window, and assumptions when saving a plan revision; a changing live
query must not silently rewrite its historical basis.

Cost per successful task requires both attributable spend and a defined outcome
count for the same population/window. A model-switch savings scenario needs
usage and pricing assumptions plus quality constraints; billing totals alone
cannot substantiate it.

Natural-language input can later generate an editable structured query, with
unsupported dimensions explained. It must use the same authorized query API.

## Validation

- Synthetic multi-user fixtures prove no cross-user data or metadata access.
- Query totals match known monthly records; mixed/unknown currency, missing
  months, partial source coverage, and manual/API distinctions remain correct.
- Dashboard persistence survives reload; widget edits affect only their intended
  query, and shared date-range behavior is visible and predictable.
- Browser-check the acceptance workflow at desktop and mobile sizes.

## Roadmap relationship

The local Product Brain README centers monitoring and budget planning. Its older
2026-07-19 roadmap explicitly excludes general-purpose cost dashboards. This
founder request changes the desired interaction and should be reconciled into
the canonical roadmap/queue before treating this design as its approved task
list. No canonical roadmap files were changed by this design note.

Product hypothesis: reusable cross-provider cost questions that also drive
budgets are useful. Datadog documentation establishes an interaction precedent,
not customer demand or an InfraSpend competitive advantage.
