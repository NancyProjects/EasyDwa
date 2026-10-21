from django.contrib import admin
from .models import Product, Sale, SaleItem, StockMovement
@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('sku','name','category','stock','selling_price','active')
    search_fields = ('sku','name','barcode')
    readonly_fields = ('stock',)
@admin.register(Sale)
class SaleAdmin(admin.ModelAdmin):
    list_display = ('id','created_at','total','payment_method')
    readonly_fields = ('created_at','payment_method','discount','total','user')
    def has_add_permission(self,request): return False
    def has_change_permission(self,request,obj=None): return False
@admin.register(SaleItem)
class SaleItemAdmin(admin.ModelAdmin):
    list_display = ('sale','product','quantity','returned_quantity')
    def has_add_permission(self,request): return False
    def has_change_permission(self,request,obj=None): return False
@admin.register(StockMovement)
class StockMovementAdmin(admin.ModelAdmin):
    list_display = ('created_at','product','change','reason','reference')
    def has_add_permission(self,request): return False
    def has_change_permission(self,request,obj=None): return False
