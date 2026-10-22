# Product brief

## Outcome

Help hardware-store customers and staff identify compatible products, obtain truthful branch availability, prepare quotations, and fulfill operational orders. The AI assistant must work with incomplete descriptions and Costa Rican Spanish while relying on verified catalog and inventory data.

## Explicit owner requirements

Create the project in the confirmed hardware_store_platform repository. Prepare a plan and Claude Code orchestration to build it. Exclude payment gateways and payment processing entirely. This package does not begin application implementation.

## Proposed MVP

- One business organization, multiple branches, organization ownership on business data.
- Spanish-first interface, Costa Rican terms and optional mixed English queries; locale and currency configurable. Initial currency CRC.
- Customer catalog/search, product comparison, real catalog images, branch availability and own quotation requests.
- Employee catalog identification, stock lookup, quotations, order confirmation and operational status.
- Manager inventory adjustments, scoped staff permissions and audit.
- Warehouse picking and complete-order fulfillment.
- Grounded AI copilot after deterministic workflows pass.

Public browsing uses only published catalog fields and business-approved availability exposure. Customer quote creation requires authentication; guest browsing must not expose customer records. Exact stock quantities versus availability bands is a business decision.

## Exclusions

No checkout, payment provider SDK, card storage, payment links, transaction settlement, payment status, payment webhook, refund processing, cash register accounting, cashier-specific payment screen, or placeholder payment module. An order means a fulfillment instruction; it does not assert that money was collected. Settlement happens outside this platform.

No fiscal invoice compliance claims, procurement, accounting, tenant signup, live employee tracking, microservices or autonomous AI stock/price changes in MVP. Delivery, returns, transfers, partial fulfillment, advanced promotions/analytics, semantic retrieval and customer-photo analysis are deferred candidates; each requires a later scoped decision.

## Success criteria

A customer can describe a need, inspect actual candidate products and request a quotation. An employee can issue a price snapshot, convert an accepted quote to an atomically reserved order, and fulfill it without overselling. An unknown or stale source never becomes an invented stock count or price. Unauthorized requests fail at the API even when bypassing the UI.

No fabricated product/price/stock claim and no critical unsafe recommendation is acceptable in the release evaluation set. Search, latency and cost budgets are set before provider evaluation, then measured. A passing evaluation set reduces risk; it is not a guarantee of all possible model behavior.
