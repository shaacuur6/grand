from decimal import Decimal
from django.core.exceptions import ValidationError
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

class Account(models.Model):
    ASSET='asset'; LIABILITY='liability'; EQUITY='equity'; REVENUE='revenue'; COGS='cogs'; EXPENSE='expense'
    TYPES=[(ASSET,'Asset'),(LIABILITY,'Liability'),(EQUITY,'Equity'),(REVENUE,'Revenue'),(COGS,'Cost of Goods Sold'),(EXPENSE,'Expense')]
    code=models.CharField(max_length=20,unique=True)
    name=models.CharField(max_length=150)
    account_type=models.CharField(max_length=20,choices=TYPES)
    parent=models.ForeignKey('self',null=True,blank=True,on_delete=models.PROTECT,related_name='children')
    active=models.BooleanField(default=True)
    opening_balance=models.DecimalField(max_digits=14,decimal_places=2,default=Decimal('0.00'))
    class Meta: ordering=['code']
    def __str__(self): return f'{self.code} - {self.name}'

class AccountingPeriod(models.Model):
    OPEN='open'; CLOSED='closed'
    STATUS=[(OPEN,'Open'),(CLOSED,'Closed')]
    name=models.CharField(max_length=100,unique=True)
    start_date=models.DateField()
    end_date=models.DateField()
    status=models.CharField(max_length=10,choices=STATUS,default=OPEN)
    created_by=models.ForeignKey(User,null=True,blank=True,on_delete=models.SET_NULL)
    class Meta: ordering=['-start_date']
    def clean(self):
        if self.start_date>self.end_date: raise ValidationError('Period start date cannot be after end date.')
    def __str__(self): return self.name

class JournalEntry(models.Model):
    date=models.DateField(default=timezone.localdate)
    period=models.ForeignKey(AccountingPeriod,on_delete=models.PROTECT,related_name='journal_entries')
    reference=models.CharField(max_length=100,blank=True)
    description=models.CharField(max_length=255)
    source_type=models.CharField(max_length=50,blank=True)
    source_id=models.PositiveBigIntegerField(null=True,blank=True)
    posted_by=models.ForeignKey(User,null=True,blank=True,on_delete=models.SET_NULL)
    posted_at=models.DateTimeField(auto_now_add=True)
    is_posted=models.BooleanField(default=True)
    class Meta:
        ordering=['-date','-id']
        constraints=[models.UniqueConstraint(fields=['source_type','source_id'],name='uniq_accounting_source')]
    @property
    def total_debit(self): return self.lines.aggregate(v=models.Sum('debit'))['v'] or Decimal('0')
    @property
    def total_credit(self): return self.lines.aggregate(v=models.Sum('credit'))['v'] or Decimal('0')
    def clean(self):
        if self.is_posted and self.pk and self.total_debit != self.total_credit: raise ValidationError('Posted journal entry must balance.')

class JournalLine(models.Model):
    entry=models.ForeignKey(JournalEntry,on_delete=models.CASCADE,related_name='lines')
    account=models.ForeignKey(Account,on_delete=models.PROTECT,related_name='journal_lines')
    debit=models.DecimalField(max_digits=14,decimal_places=2,default=Decimal('0.00'))
    credit=models.DecimalField(max_digits=14,decimal_places=2,default=Decimal('0.00'))
    description=models.CharField(max_length=255,blank=True)
    class Meta: ordering=['id']
    def clean(self):
        if self.debit<0 or self.credit<0 or (self.debit and self.credit): raise ValidationError('A journal line must have either a debit or a credit amount.')

class SupplierPayment(models.Model):
    METHODS=[('cash','Cash'),('bank','Bank'),('card','Card'),('mobile','Mobile Money'),('other','Other')]
    supplier=models.ForeignKey('purchases.Supplier',on_delete=models.PROTECT,related_name='accounting_payments')
    date=models.DateField(default=timezone.localdate)
    amount=models.DecimalField(max_digits=14,decimal_places=2)
    payment_method=models.CharField(max_length=20,choices=METHODS,default='cash')
    reference=models.CharField(max_length=100,blank=True)
    notes=models.TextField(blank=True)
    created_by=models.ForeignKey(User,null=True,blank=True,on_delete=models.SET_NULL)
    created=models.DateTimeField(auto_now_add=True)
    def __str__(self): return f'{self.supplier} - {self.amount}'

class InventoryMovement(models.Model):
    RECEIPT='receipt'; ISSUE='issue'; ADJUSTMENT='adjustment'
    TYPES=[(RECEIPT,'Receipt'),(ISSUE,'Issue / COGS'),(ADJUSTMENT,'Adjustment')]
    item=models.ForeignKey('purchases.InventoryItem',on_delete=models.PROTECT,related_name='accounting_movements')
    date=models.DateField(default=timezone.localdate)
    movement_type=models.CharField(max_length=20,choices=TYPES)
    quantity=models.DecimalField(max_digits=14,decimal_places=2)
    unit_cost=models.DecimalField(max_digits=14,decimal_places=2)
    reference=models.CharField(max_length=100,blank=True)
    notes=models.TextField(blank=True)
    created_by=models.ForeignKey(User,null=True,blank=True,on_delete=models.SET_NULL)
    def total_cost(self): return self.quantity*self.unit_cost
