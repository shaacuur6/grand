# Payment / Allocation Review

## Findings

1. `PaymentSummaryView` existed, but `booking_payment_summary.html` was empty.
2. The project had two allocation layers:
   - `PaymentAllocation`: generic room/restaurant/service rows, previously unused.
   - `RoomPaymentAllocation`, `RestaurantPaymentAllocation`, `ServicePaymentAllocation`: detailed rows used by `billing/utils.py`.
3. The detailed allocation algorithm was functional, but the summary/receipt UI did not expose the allocation state.
4. `money_tags.py` existed but was loaded explicitly in templates instead of being a Django template builtin.

## Changes

- `PaymentSummaryView` now:
  - synchronizes the invoice and allocations before displaying each booking;
  - displays invoice totals, paid, balance, component-level paid totals, payment history, and unallocated amounts;
  - exposes allocation details for every payment.
- `billing/utils.py` now:
  - keeps detailed allocations as the source of truth;
  - synchronizes `PaymentAllocation` as a compact component summary;
  - provides invoice/payment allocation summary helpers.
- Payment and receipt pages now display allocation information.
- `money` is registered globally through `TEMPLATES[...]["OPTIONS"]["builtins"]`, so templates can use `{{ amount|money }}` without `{% load money_tags %}`.
- Added billing tests for allocation and rebuild behavior.

## Allocation order

Payments are allocated in this order:

1. Room
2. Restaurant orders, oldest first
3. Services, oldest first

Rebuilding allocations always processes payments in `created, id` order.

## Validation

Python bytecode compilation completed successfully.

Full `manage.py check` / Django test execution could not be run in this environment because Django is not installed in the execution environment. Run these commands in the project's virtual environment:

```bash
python manage.py check
python manage.py test billing
```

No database schema migration is required for these changes.
