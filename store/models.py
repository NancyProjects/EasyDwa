from django.conf import settings
from django.db import models
from django.core.validators import MinValueValidator
from decimal import Decimal

class Product(models.Model):
    BOOK = 'book'
    STATIONERY = 'stationery'
    name = models.CharField(max_length=160)
    sku = models.CharField(max_length=60, unique=True)
    barcode = models.CharField(max_length=80, blank=True, unique=True, null=True)
    category = models.CharField(max_length=20, choices=[(BOOK,'Book'),(STATIONERY,'Stationery')])
    author = models.CharField(max_length=100, blank=True)
    supplier = models.CharField(max_length=120, blank=True)
    cost_price = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(0)])
    selling_price = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(0)])
    stock = models.PositiveIntegerField(default=0)
    reorder_level = models.PositiveIntegerField(default=5)
    active = models.BooleanField(default=True)
    def __str__(self): return f'{self.sku} — {self.name}'

class StockMovement(models.Model):
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name='movements')
    change = models.IntegerField()
    reason = models.CharField(max_length=20, choices=[('opening','Opening'),('receive','Received'),('sale','Sale'),('return','Return'),('adjust','Adjustment')])
    reference = models.CharField(max_length=80, blank=True)
    note = models.CharField(max_length=240, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)

class Sale(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    payment_method = models.CharField(max_length=20, choices=[('cash','Cash'),('momo','Mobile money'),('card','Card'),('other','Other')])
    discount = models.DecimalField(max_digits=12,decimal_places=2,default=Decimal('0.00'))
    total = models.DecimalField(max_digits=12,decimal_places=2)
    user = models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.SET_NULL,null=True)
    @property
    def receipt_number(self): return f'BS-{self.id:06d}'

class SaleItem(models.Model):
    sale = models.ForeignKey(Sale,on_delete=models.PROTECT,related_name='items')
    product = models.ForeignKey(Product,on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField()
    unit_price = models.DecimalField(max_digits=12,decimal_places=2)
    returned_quantity = models.PositiveIntegerField(default=0)
    @property
    def line_total(self): return self.quantity * self.unit_price
