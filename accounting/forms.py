from decimal import Decimal
from django import forms
from django.forms import inlineformset_factory
from .models import Account, AccountingPeriod, JournalEntry, JournalLine, SupplierPayment, InventoryMovement

class BootstrapMixin:
    def boot(self):
        for f in self.fields.values():
            if isinstance(f.widget, forms.CheckboxInput): f.widget.attrs.setdefault('class','form-check-input')
            elif isinstance(f.widget, (forms.Select, forms.SelectMultiple)): f.widget.attrs.setdefault('class','form-select')
            else: f.widget.attrs.setdefault('class','form-control')

class AccountForm(BootstrapMixin, forms.ModelForm):
    class Meta: model=Account; fields=['code','name','account_type','parent','active','opening_balance']
    def __init__(self,*a,**k): super().__init__(*a,**k); self.boot()

class PeriodForm(BootstrapMixin, forms.ModelForm):
    class Meta: model=AccountingPeriod; fields=['name','start_date','end_date','status']; widgets={'start_date':forms.DateInput(attrs={'type':'date'}),'end_date':forms.DateInput(attrs={'type':'date'})}
    def __init__(self,*a,**k): super().__init__(*a,**k); self.boot()

class JournalForm(BootstrapMixin, forms.ModelForm):
    class Meta: model=JournalEntry; fields=['date','period','reference','description']; widgets={'date':forms.DateInput(attrs={'type':'date'})}
    def __init__(self,*a,**k): super().__init__(*a,**k); self.boot()

class JournalLineForm(BootstrapMixin, forms.ModelForm):
    class Meta: model=JournalLine; fields=['account','debit','credit','description']; widgets={'debit':forms.NumberInput(attrs={'step':'0.01','min':'0'}),'credit':forms.NumberInput(attrs={'step':'0.01','min':'0'})}
    def __init__(self,*a,**k): super().__init__(*a,**k); self.boot()
    def clean(self):
        d=self.cleaned_data.get('debit') or Decimal('0'); c=self.cleaned_data.get('credit') or Decimal('0')
        if d and c: raise forms.ValidationError('Enter a debit OR a credit, not both.')
        return self.cleaned_data

JournalLineFormSet=inlineformset_factory(JournalEntry,JournalLine,form=JournalLineForm,extra=2,can_delete=True)

class SupplierPaymentForm(BootstrapMixin, forms.ModelForm):
    class Meta: model=SupplierPayment; fields=['supplier','date','amount','payment_method','reference','notes']; widgets={'date':forms.DateInput(attrs={'type':'date'}),'amount':forms.NumberInput(attrs={'step':'0.01','min':'0.01'}),'notes':forms.Textarea(attrs={'rows':3})}
    def __init__(self,*a,**k): super().__init__(*a,**k); self.boot()

class InventoryMovementForm(BootstrapMixin, forms.ModelForm):
    class Meta: model=InventoryMovement; fields=['item','date','movement_type','quantity','unit_cost','reference','notes']; widgets={'date':forms.DateInput(attrs={'type':'date'}),'quantity':forms.NumberInput(attrs={'step':'0.01','min':'0.01'}),'unit_cost':forms.NumberInput(attrs={'step':'0.01','min':'0'}),'notes':forms.Textarea(attrs={'rows':3})}
    def __init__(self,*a,**k): super().__init__(*a,**k); self.boot()


class OpeningBalanceForm(BootstrapMixin, forms.Form):
    account=forms.ModelChoiceField(queryset=Account.objects.filter(active=True))
    date=forms.DateField(widget=forms.DateInput(attrs={'type':'date'}))
    amount=forms.DecimalField(min_value=Decimal('0.01'),max_digits=14,decimal_places=2,widget=forms.NumberInput(attrs={'step':'0.01','min':'0.01'}))
    side=forms.ChoiceField(choices=[('debit','Debit'),('credit','Credit')])
    description=forms.CharField(max_length=255,initial='Opening balance')
    def __init__(self,*a,**k): super().__init__(*a,**k); self.boot()
