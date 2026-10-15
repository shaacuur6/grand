# Grand HMS report accuracy patch

## Files changed

- `reports/views.py`
  - Applies category and food filters to `OrderItem` rows before aggregation, preventing other foods in a matching order from leaking into top-food/category reports.
  - Groups top foods by food ID as well as name so identically named products are not merged.
  - Applies selected inclusive date ranges to RoomStay revenue using the model's exclusive `end_date` convention; open stays are capped at the current hotel date.
  - Makes check-in and check-out reports filter by their own date field across the full selected range.
  - Calculates invoice payments as of the selected report end date.
  - Imports `HttpResponse` for Excel/PDF exports.
  - Uses recorded customer collections, supplier payments, and expenses for cash-flow totals; purchase orders alone are not treated as cash payments.
  - Removes ledger rebuild/seed calls from financial report GET requests.
- `accounting/views.py`
  - Removes ledger rebuilding from accounting statement GET requests. Existing explicit authorized POST endpoint `accounting:accounting_sync` remains the manual synchronization/reconciliation action.
- `reports/tests.py`
  - Adds regression tests for item-level filters, date-range room revenue, checkout ranges, as-of invoice payments, and cash-flow basis.
- `templates/reports/restaurant/top_selling_foods.html`
  - Displays category and an empty state.
- `templates/reports/restaurant/category_sales.html`
  - Displays an empty state.
- `templates/reports/financial/cash_flow.html`
  - Labels supplier payments separately and explains the scope/limitations of recorded cash movement.

## Database migrations

No model fields or schema are changed by this patch; no migration is required.

## Important remaining accuracy limitation

`OrderItem` currently has no stored sale-price snapshot. The restaurant item-sales reports still value historical quantities using the current `FoodItem.price`. If menu prices change, historical sales can change. A separate follow-up migration should add an order-item unit-price snapshot and backfill existing rows only with a clearly documented approximation; current menu prices cannot prove past prices.

The cash-flow report includes only recorded `billing.Payment`, `accounting.SupplierPayment`, and `finance.Expense` movements. Opening balances, transfers, refunds, and unrecorded movements are excluded. It is not a bank reconciliation.

## Safe synchronization workflow

1. Take a database backup before rebuilding accounting journals.
2. Review the accounting synchronization behavior and any closed-period controls.
3. Use the existing authorized POST action at `accounting:accounting_sync` only when an explicit rebuild is intended; do not call synchronization from a report page load.
4. Review the returned counts and compare ledger totals to operational records.
5. Run tests and reconcile trial balance, receivables, revenue, COGS, and expense accounts before relying on reports.

Operational accounting signals already post invoices, payments, expenses, purchases, supplier payments, and inventory movements when those records are saved. The explicit rebuild is therefore a repair/reconciliation workflow, not a routine GET side effect.

## Validation status

Python syntax compilation passed for the changed Python files. Automated Django tests could not be executed in this workspace because the ZIP's included virtual environment points to a macOS Python executable that is unavailable in this Linux environment, and the active Python environment does not have Django installed. Run `python manage.py test reports` inside the project's working virtual environment before deployment.
