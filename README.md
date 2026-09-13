# Grand Hotel & Restaurant HMS — Phase Last

This build consolidates the operational architecture for **Billing, Restaurant, Purchases/Inventory and Reports** and applies centralized role authorization.

## Role architecture

`accounts/constants.py` is the single source of truth:

- `ADMIN_ROLES`: admin
- `MANAGEMENT_ROLES`: admin, manager
- `HOTEL_ROLES`: admin, manager, reception
- `BILLING_ROLES`: admin, manager, reception
- `RESTAURANT_ROLES`: admin, manager, reception, waiter
- `KITCHEN_ROLES`: admin, manager, kitchen
- `REPORT_ROLES`: admin, manager, reception
- `ALL_ROLES`: admin, manager, reception, waiter, kitchen

Views use `RoleRequiredMixin` plus one of these role groups instead of repeating role lists everywhere.

## Billing

- Invoice list with filters
- Invoice detail with room-stay, restaurant and service charges
- Component payment allocation
- Payment entry, edit and delete
- Payment history and receipt/PDF
- Invoice discount management
- Collection/revenue view
- Payment allocations are rebuilt whenever payments or invoice totals change

## Restaurant

- POS for table, guest-room and employee orders
- Menu/category management
- Employee management
- Order list/detail/edit/delete
- QR receipt
- Hotel-room restaurant orders automatically synchronize the guest invoice

## Purchases & inventory

- Supplier management
- Inventory item management
- Purchase header + line-item formset
- Purchase total calculated from line items
- Purchase creation increases inventory stock
- Purchase editing reconciles stock using the old/new line quantities
- Purchase deletion reverses its stock impact
- Low-stock reporting

## Reports

Reporting is centralized in the `reports` app:

- Hotel: check-ins, check-outs, reservations, guest history, occupancy, room status, room revenue, stay ledger, room-type revenue
- Billing: payments, payment methods, invoice summary, outstanding, fully paid, partial, room/service/restaurant paid-vs-pending
- Restaurant: daily/monthly sales, waiter sales, collections, unpaid orders, top foods, category sales, table sales and order history
- Purchases: purchase report, supplier purchase report and low stock
- Restaurant Excel/PDF exports

## Database / migrations

The changes in this build do not alter database models, so no new migration is required for the four apps. Existing data can therefore be retained.

After copying this project into your normal virtual environment, run:

```bash
python manage.py check
python manage.py migrate
python manage.py collectstatic --noinput
```

Then test locally before deploying to the VPS.
