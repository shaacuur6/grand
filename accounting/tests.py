from decimal import Decimal
from django.test import TestCase
from .models import Account, AccountingPeriod, JournalEntry, JournalLine

class AccountingModelTests(TestCase):
    def test_journal_line_defaults(self):
        a=Account.objects.create(code='9999',name='Test Cash',account_type=Account.ASSET)
        p=AccountingPeriod.objects.create(name='Test Period',start_date='2026-01-01',end_date='2026-01-31')
        e=JournalEntry.objects.create(date='2026-01-15',period=p,description='Test')
        JournalLine.objects.create(entry=e,account=a,debit=Decimal('100.00'))
        self.assertEqual(e.total_debit,Decimal('100.00'))
