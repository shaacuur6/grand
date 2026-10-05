from django import forms
from .models import Expense, ExpenseCategory

class ExpenseCategoryForm(forms.ModelForm):
    class Meta:
        model = ExpenseCategory
        fields = ['name', 'active']
        widgets = {'name': forms.TextInput(attrs={'class': 'form-control'}), 'active': forms.CheckboxInput(attrs={'class': 'form-check-input'})}

class ExpenseForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        qs = ExpenseCategory.objects.filter(active=True)
        if self.instance and self.instance.pk and self.instance.category_id:
            qs = ExpenseCategory.objects.filter(pk=self.instance.category_id) | qs
        self.fields["category"].queryset = qs.distinct().order_by("name")

    class Meta:
        model = Expense
        fields = ['category', 'description', 'amount', 'date', 'payment_method', 'reference', 'notes']
        widgets = {
            'category': forms.Select(attrs={'class': 'form-select'}),
            'description': forms.TextInput(attrs={'class': 'form-control'}),
            'amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0.01'}),
            'date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'payment_method': forms.Select(attrs={'class': 'form-select'}),
            'reference': forms.TextInput(attrs={'class': 'form-control'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

    def clean_amount(self):
        amount = self.cleaned_data['amount']
        if amount <= 0:
            raise forms.ValidationError('Amount must be greater than zero.')
        return amount
