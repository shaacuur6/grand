from decimal import Decimal
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Sum, Q
from django.shortcuts import redirect, render
from django.urls import reverse_lazy
from django.views.generic import ListView, CreateView, UpdateView, DetailView, TemplateView
from accounts.constants import MANAGEMENT_ROLES
from accounts.mixins import RoleRequiredMixin
from .models import Account, AccountingPeriod, JournalEntry, JournalLine, SupplierPayment, InventoryMovement
from .forms import AccountForm, PeriodForm, JournalForm, JournalLineFormSet, SupplierPaymentForm, InventoryMovementForm, OpeningBalanceForm
from .services import seed_accounts, sync_operational_journals, post_supplier_payment, post_inventory_movement, account, period_for, get_operational_receivables_as_of

class AccountingRoleMixin(LoginRequiredMixin, RoleRequiredMixin): allowed_roles=MANAGEMENT_ROLES

def _date_range(request):
    from django.utils import timezone
    today=timezone.localdate(); start=request.GET.get('start') or today.replace(day=1).isoformat(); end=request.GET.get('end') or today.isoformat()
    return start,end

class AccountingDashboardView(AccountingRoleMixin, TemplateView):
    template_name='accounting/dashboard.html'

    def get_context_data(self, **kwargs):
        c = super().get_context_data(**kwargs)
        seed_accounts()
        start, end = _date_range(self.request)

        # Use the same authoritative P&L calculation as Finance, Profit & Loss,
        # and the accounting statement. This prevents dashboard totals from
        # drifting apart when operational data and posted journals differ.
        from .services import get_profit_loss_statement
        pnl = get_profit_loss_statement(start, end)

        from billing.models import Payment
        customer_collections = Payment.objects.filter(
            created__date__gte=start, created__date__lte=end,
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0')

        ending_receivable = get_operational_receivables_as_of(end)
        from datetime import date, timedelta
        try:
            start_date = date.fromisoformat(start) if isinstance(start, str) else start
        except (TypeError, ValueError):
            start_date = date.today().replace(day=1)
        beginning_receivable = get_operational_receivables_as_of(start_date - timedelta(days=1))
        ar_change = ending_receivable - beginning_receivable

        qs = JournalLine.objects.filter(
            entry__date__gte=start, entry__date__lte=end, entry__is_posted=True
        )
        cash_balance_movement = self._balance_many(['1000', '1010', '1020'], qs)

        c.update(
            start=start, end=end,
            revenue=pnl['total_revenue'],
            revenue_breakdown=pnl['revenue'],
            costs=pnl['cogs'] + pnl['total_expenses'],
            cogs=pnl['cogs'],
            cogs_source=pnl['cogs_source'],
            expenses=pnl['total_expenses'],
            gross_profit=pnl['gross_profit'],
            operating_profit=pnl['operating_profit'],
            profit=pnl['net_profit'],
            receivable=ending_receivable,
            beginning_receivable=beginning_receivable,
            customer_collections=customer_collections,
            ar_change=ar_change,
            revenue_bridge=customer_collections + ar_change,
            cash=cash_balance_movement,
            payable=self._balance('2000', qs),
            accounts=Account.objects.filter(active=True).count(),
            entries=JournalEntry.objects.filter(date__gte=start, date__lte=end).count(),
        )
        return c

    def _balance(self, code, qs):
        a = qs.filter(account__code=code).aggregate(d=Sum('debit'), c=Sum('credit'))
        return (a['d'] or 0) - (a['c'] or 0)

    def _balance_many(self, codes, qs):
        a = qs.filter(account__code__in=codes).aggregate(d=Sum('debit'), c=Sum('credit'))
        return (a['d'] or 0) - (a['c'] or 0)

class SyncView(AccountingRoleMixin, TemplateView):
    def post(self,request,*args,**kwargs):
        result=sync_operational_journals(request.user); messages.success(request,'Accounting journals rebuilt: '+', '.join(f'{v} {k}' for k,v in result.items())+'.'); return redirect('accounting_dashboard')

class AccountListView(AccountingRoleMixin,ListView): model=Account; template_name='accounting/account_list.html'; context_object_name='accounts'
class AccountCreateView(AccountingRoleMixin,CreateView): model=Account; form_class=AccountForm; template_name='accounting/account_form.html'; success_url=reverse_lazy('account_list')
class AccountUpdateView(AccountingRoleMixin,UpdateView): model=Account; form_class=AccountForm; template_name='accounting/account_form.html'; success_url=reverse_lazy('account_list')
class PeriodListView(AccountingRoleMixin,ListView): model=AccountingPeriod; template_name='accounting/period_list.html'; context_object_name='periods'
class PeriodCreateView(AccountingRoleMixin,CreateView): model=AccountingPeriod; form_class=PeriodForm; template_name='accounting/period_form.html'; success_url=reverse_lazy('period_list')
class PeriodUpdateView(AccountingRoleMixin,UpdateView): model=AccountingPeriod; form_class=PeriodForm; template_name='accounting/period_form.html'; success_url=reverse_lazy('period_list')

class JournalListView(AccountingRoleMixin,ListView):
    model=JournalEntry; template_name='accounting/journal_list.html'; context_object_name='entries'; paginate_by=30
    def get_queryset(self):
        qs=super().get_queryset().prefetch_related('lines__account'); q=self.request.GET.get('q','').strip(); start,end=_date_range(self.request)
        qs=qs.filter(date__gte=start,date__lte=end)
        if q: qs=qs.filter(Q(description__icontains=q)|Q(reference__icontains=q)|Q(source_type__icontains=q))
        return qs
class JournalDetailView(AccountingRoleMixin,DetailView): model=JournalEntry; template_name='accounting/journal_detail.html'; context_object_name='entry'
class JournalCreateView(AccountingRoleMixin,CreateView):
    model=JournalEntry; form_class=JournalForm; template_name='accounting/journal_form.html'
    def get_context_data(self,**kwargs):
        c=super().get_context_data(**kwargs); c['formset']=kwargs.get('formset') or JournalLineFormSet(); return c
    def post(self,request,*args,**kwargs):
        self.object=None; form=self.get_form(); fs=JournalLineFormSet(request.POST)
        if form.is_valid() and fs.is_valid():
            total_d=sum((x.cleaned_data.get('debit') or 0) for x in fs if not x.cleaned_data.get('DELETE')); total_c=sum((x.cleaned_data.get('credit') or 0) for x in fs if not x.cleaned_data.get('DELETE'))
            if total_d!=total_c or total_d<=0: messages.error(request,'Journal entry must have equal debit and credit totals greater than zero.'); return render(request,self.template_name,{'form':form,'formset':fs})
            e=form.save(commit=False); e.posted_by=request.user; e.save(); fs.instance=e; fs.save(); messages.success(request,'Journal entry posted.'); return redirect('journal_detail',e.pk)
        return render(request,self.template_name,{'form':form,'formset':fs})

class OpeningBalanceView(AccountingRoleMixin, TemplateView):
    template_name='accounting/opening_balance.html'
    def get_context_data(self, **kwargs):
        c=super().get_context_data(**kwargs); c['form']=kwargs.get('form') or OpeningBalanceForm(); return c
    def post(self, request, *args, **kwargs):
        form=OpeningBalanceForm(request.POST)
        if form.is_valid():
            data=form.cleaned_data; a=data['account']; amt=data['amount']; side=data['side'];
            offset='3000' if a.account_type in ['asset','expense','cogs'] else '3100'
            lines=[(a.code,amt if side=='debit' else 0,amt if side=='credit' else 0,a.name),(offset,amt if side=='credit' else 0,amt if side=='debit' else 0,'Opening balance offset')]
            from .models import JournalEntry, JournalLine
            e=JournalEntry.objects.create(date=data['date'],period=period_for(data['date']),description=data['description'],reference='OPENING',source_type='opening',source_id=None,posted_by=request.user)
            for code,debit,credit,desc in lines:
                JournalLine.objects.create(entry=e,account=account(code),debit=debit,credit=credit,description=desc)
            messages.success(request,'Opening balance posted successfully.'); return redirect('journal_list')
        return render(request,self.template_name,{'form':form})

class SupplierPayablesView(AccountingRoleMixin, TemplateView):
    template_name='accounting/supplier_payables.html'
    def get_context_data(self,**kwargs):
        from purchases.models import Purchase
        from django.db.models import Sum
        c=super().get_context_data(**kwargs); rows=[]
        from .models import SupplierPayment
        for supplier in __import__('purchases.models',fromlist=['Supplier']).Supplier.objects.all().order_by('name'):
            purchased=Purchase.objects.filter(supplier=supplier).aggregate(v=Sum('total_amount'))['v'] or 0
            paid=SupplierPayment.objects.filter(supplier=supplier).aggregate(v=Sum('amount'))['v'] or 0
            if purchased or paid: rows.append({'supplier':supplier,'purchased':purchased,'paid':paid,'balance':purchased-paid})
        c['rows']=rows; c['total_purchased']=sum(r['purchased'] for r in rows); c['total_paid']=sum(r['paid'] for r in rows); c['total_balance']=sum(r['balance'] for r in rows); return c

class InventoryValuationView(AccountingRoleMixin, TemplateView):
    template_name='accounting/inventory_valuation.html'
    def get_context_data(self,**kwargs):
        from purchases.models import InventoryItem, PurchaseItem
        c=super().get_context_data(**kwargs); rows=[]
        for item in InventoryItem.objects.all().order_by('name'):
            agg=PurchaseItem.objects.filter(item=item).aggregate(q=Sum('quantity'),cost=Sum('quantity'))
            total_qty=agg['q'] or 0
            total_cost=PurchaseItem.objects.filter(item=item).aggregate(v=Sum('quantity'))['v'] or 0
            # Weighted average cost from purchase lines.
            lines=PurchaseItem.objects.filter(item=item)
            q=Decimal('0'); cost=Decimal('0')
            for line in lines: q += line.quantity; cost += line.quantity*line.unit_price
            avg=(cost/q) if q else Decimal('0'); value=item.current_stock*avg
            rows.append({'item':item,'stock':item.current_stock,'avg_cost':avg,'value':value})
        c['rows']=rows; c['total_value']=sum(r['value'] for r in rows); return c

class SupplierPaymentListView(AccountingRoleMixin,ListView): model=SupplierPayment; template_name='accounting/supplier_payment_list.html'; context_object_name='payments'
class SupplierPaymentCreateView(AccountingRoleMixin,CreateView):
    model=SupplierPayment; form_class=SupplierPaymentForm; template_name='accounting/supplier_payment_form.html'; success_url=reverse_lazy('supplier_payment_list')
    def form_valid(self,form):
        obj=form.save(commit=False); obj.created_by=self.request.user; obj.save(); post_supplier_payment(obj,self.request.user); messages.success(self.request,'Supplier payment recorded and posted.'); return redirect(self.success_url)

class InventoryMovementListView(AccountingRoleMixin,ListView): model=InventoryMovement; template_name='accounting/inventory_movement_list.html'; context_object_name='movements'
class InventoryMovementCreateView(AccountingRoleMixin,CreateView):
    model=InventoryMovement; form_class=InventoryMovementForm; template_name='accounting/inventory_movement_form.html'; success_url=reverse_lazy('inventory_movement_list')
    def form_valid(self,form):
        obj=form.save(commit=False); obj.created_by=self.request.user
        if obj.movement_type=='issue' and obj.quantity > obj.item.current_stock:
            form.add_error('quantity', f'Cannot issue {obj.quantity}; only {obj.item.current_stock} is in stock.')
            return self.form_invalid(form)
        obj.save()
        if obj.movement_type=='receipt': obj.item.current_stock += obj.quantity
        elif obj.movement_type=='issue': obj.item.current_stock -= obj.quantity
        else: obj.item.current_stock = obj.quantity
        obj.item.save(update_fields=['current_stock'])
        post_inventory_movement(obj,self.request.user); messages.success(self.request,'Inventory movement posted to the ledger.'); return redirect(self.success_url)

class StatementBase(AccountingRoleMixin,TemplateView):
    def get_context_data(self, **kwargs):
        # Keep the double-entry reports in sync with the existing HMS operational
        # modules. Finance/reports read invoices and expenses directly, while the
        # accounting statements read JournalLine. Rebuilding the operational
        # journals here makes the accounting statements reflect the same activity.
        seed_accounts()
        sync_operational_journals(self.request.user)
        return super().get_context_data(**kwargs)

    def rows(self,types,start,end):
        qs=JournalLine.objects.filter(entry__date__gte=start,entry__date__lte=end,entry__is_posted=True,account__account_type__in=types).values('account__code','account__name','account__account_type').annotate(debit=Sum('debit'),credit=Sum('credit')).order_by('account__code')
        rows=[]
        for r in qs:
            if r['account__account_type'] in ['revenue','liability','equity']: balance=(r['credit'] or 0)-(r['debit'] or 0)
            else: balance=(r['debit'] or 0)-(r['credit'] or 0)
            r['balance']=balance; rows.append(r)
        return rows

class TrialBalanceView(StatementBase):
    template_name='accounting/trial_balance.html'
    def get_context_data(self,**kwargs):
        c=super().get_context_data(**kwargs); start,end=_date_range(self.request); rows=self.rows(['asset','liability','equity','revenue','cogs','expense'],start,end); c.update(start=start,end=end,rows=rows,total_debit=sum(r['debit'] or 0 for r in rows),total_credit=sum(r['credit'] or 0 for r in rows)); return c
class ProfitLossView(StatementBase):
    template_name='accounting/profit_loss.html'

    def get_context_data(self, **kwargs):
        c = super().get_context_data(**kwargs)
        start, end = _date_range(self.request)
        from .services import get_profit_loss_statement
        pnl = get_profit_loss_statement(start, end)
        c.update(start=start, end=end, **pnl)
        return c

class BalanceSheetView(StatementBase):
    template_name='accounting/balance_sheet.html'

    def get_context_data(self, **kwargs):
        from datetime import date
        c = super().get_context_data(**kwargs)

        # A balance sheet is a point-in-time statement, not a period statement.
        # Keep accepting the old `end` parameter for bookmarked URLs, but ignore
        # the start date for balance-sheet calculations.
        today = __import__('django.utils.timezone', fromlist=['localdate']).localdate()
        as_of = self.request.GET.get('as_of') or self.request.GET.get('end') or today.isoformat()
        try:
            as_of_date = date.fromisoformat(as_of) if isinstance(as_of, str) else as_of
        except (TypeError, ValueError):
            as_of_date = today
            as_of = today.isoformat()

        # Balance-sheet accounts are cumulative from the beginning of the
        # accounting records through the selected as-of date.
        rows = self.rows(['asset', 'liability', 'equity'], date.min, as_of_date)
        assets = [r for r in rows if r['account__account_type'] == 'asset']

        # Accounts Receivable uses the same operational as-of calculation as
        # Finance, so an old booking paid today is reflected correctly in cash
        # and AR even though the original revenue was earned before the current
        # reporting period.
        operational_ar = get_operational_receivables_as_of(as_of_date)
        for row in assets:
            if row['account__code'] == '1100':
                row['debit'] = operational_ar
                row['credit'] = Decimal('0.00')
                row['balance'] = operational_ar

        liab = [r for r in rows if r['account__account_type'] == 'liability']
        eq = [r for r in rows if r['account__account_type'] == 'equity']

        # Retained earnings on an unclosed ledger are the cumulative net income
        # earned through the balance-sheet date, not just the current report
        # period. This is essential for point-in-time balance sheets: revenue
        # earned in September remains part of equity when a September customer
        # pays in October.
        cumulative_pl = self.rows(
            ['revenue', 'cogs', 'expense'],
            date.min,
            as_of_date,
        )
        revenue = sum(
            r['balance'] for r in cumulative_pl
            if r['account__account_type'] == 'revenue'
        )
        cogs = sum(
            r['balance'] for r in cumulative_pl
            if r['account__account_type'] == 'cogs'
        )
        expenses = sum(
            r['balance'] for r in cumulative_pl
            if r['account__account_type'] == 'expense'
        )
        cumulative_profit = revenue - cogs - expenses

        # Still expose the profit earned during the current calendar/reporting
        # period for reference, but do not use it as the whole equity balance.
        start, _ = _date_range(self.request)
        period_pl = self.rows(['revenue', 'cogs', 'expense'], start, as_of_date)
        period_revenue = sum(
            r['balance'] for r in period_pl
            if r['account__account_type'] == 'revenue'
        )
        period_cogs = sum(
            r['balance'] for r in period_pl
            if r['account__account_type'] == 'cogs'
        )
        period_expenses = sum(
            r['balance'] for r in period_pl
            if r['account__account_type'] == 'expense'
        )
        period_profit = period_revenue - period_cogs - period_expenses

        total_assets = sum(r['balance'] for r in assets)
        total_liabilities = sum(r['balance'] for r in liab)
        total_equity = sum(r['balance'] for r in eq) + cumulative_profit

        c.update(
            as_of=as_of,
            start=start,
            end=as_of,
            assets=assets,
            liabilities=liab,
            equity=eq,
            net_profit=period_profit,
            cumulative_profit=cumulative_profit,
            total_assets=total_assets,
            total_liabilities=total_liabilities,
            total_equity=total_equity,
        )
        return c
class CashFlowView(StatementBase):
    template_name='accounting/cash_flow.html'
    def get_context_data(self,**kwargs):
        c=super().get_context_data(**kwargs); start,end=_date_range(self.request); qs=JournalLine.objects.filter(entry__date__gte=start,entry__date__lte=end,entry__is_posted=True,account__code__in=['1000','1010','1020']); rows=qs.values('account__code','account__name').annotate(debit=Sum('debit'),credit=Sum('credit')); c.update(start=start,end=end,rows=rows,net_cash=sum((r['debit'] or 0)-(r['credit'] or 0) for r in rows)); return c
