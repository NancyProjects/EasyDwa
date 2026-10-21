from django import forms
from .models import Product
class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = ['name','sku','barcode','category','author','supplier','cost_price','selling_price','stock','reorder_level','active']
    def clean_barcode(self):
        return self.cleaned_data['barcode'] or None
