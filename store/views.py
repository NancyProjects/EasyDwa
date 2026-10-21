from collections import defaultdict
from decimal import Decimal, InvalidOperation
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import F, Sum
from django.http import HttpResponseBadRequest
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from .forms import ProductForm
from .models import Product, Sale, SaleItem, StockMovement

def money(value):
    try:
        v = Decimal(str(value))
        if not v.is_finite() or v < 0 or v.as_tuple().exponent < -2: raise ValueError
        return v
    except (InvalidOperation, ValueError, TypeError): raise ValueError('Enter a valid amount in GHS (up to two decimal places).')

def whole(value):
    try:
        if not str(value).isdigit(): raise ValueError
        return int(value)
    except (ValueError, TypeError): raise ValueError('Quantity must be a whole number.')

@login_required
def dashboard(request):
    today = timezone.localdate()
    daily = Sale.objects.filter(created_at__date=today).aggregate(total=Sum('total'))['total'] or 0
    return render(request,'dashboard.html',{'product_count':Product.objects.filter(active=True).count(),'low':Product.objects.filter(active=True,stock__lte=F('reorder_level')).order_by('stock')[:12],'daily':daily,'sales_count':Sale.objects.filter(created_at__date=today).count()})

@login_required
def products(request):
    q = request.GET.get('q','').strip()
    rows = Product.objects.all().order_by('name')
    if q:
        from django.db.models import Q
        rows = rows.filter(Q(name__icontains=q)|Q(sku__icontains=q)|Q(barcode__icontains=q))
    return render(request,'products.html',{'rows':rows,'q':q})

@login_required
def product_edit(request,pk=None):
    product = get_object_or_404(Product,pk=pk) if pk else None
    form = ProductForm(request.POST or None,instance=product)
    if product: form.fields['stock'].disabled = True
    if request.method=='POST' and form.is_valid():
        with transaction.atomic():
            item = form.save(commit=False)
            initial_stock = item.stock if not product else None
            if product:
                old = Product.objects.select_for_update().get(pk=pk)
                # Stock changes must go through stock movement screen.
                item.stock = old.stock
            item.save()
            if initial_stock:
                StockMovement.objects.create(product=item,change=initial_stock,reason='opening',user=request.user)
        messages.success(request,'Product saved.')
        return redirect('products')
    return render(request,'form.html',{'form':form,'title':'Edit product' if product else 'Add product','hint':'Use Stock to change quantities after creating a product.'})

@login_required
def stock(request):
    if request.method=='POST':
        try:
            qty = whole(request.POST.get('quantity'))
            if not qty: raise ValueError('Quantity must be greater than zero.')
            reason = request.POST.get('reason')
            if reason not in ('receive','adjust_add','adjust_remove'): raise ValueError('Select a movement type.')
            with transaction.atomic():
                p = Product.objects.select_for_update().get(pk=request.POST.get('product'))
                change = -qty if reason=='adjust_remove' else qty
                if p.stock+change < 0: raise ValueError('Cannot remove more than the available stock.')
                p.stock += change
                p.save(update_fields=['stock'])
                StockMovement.objects.create(product=p,change=change,reason='receive' if reason=='receive' else 'adjust',reference=request.POST.get('reference','')[:80],note=request.POST.get('note','')[:240],user=request.user)
            messages.success(request,'Stock updated.')
            return redirect('stock')
        except (ValueError, Product.DoesNotExist) as exc: messages.error(request,str(exc) if isinstance(exc,ValueError) else 'Product not found.')
    return render(request,'stock.html',{'products':Product.objects.filter(active=True).order_by('name'),'movements':StockMovement.objects.select_related('product','user').order_by('-id')[:50]})

@login_required
def new_sale(request):
    products = list(Product.objects.filter(active=True).order_by('name'))
    if request.method=='POST':
        try:
            ids = request.POST.getlist('product')
            quantities = request.POST.getlist('quantity')
            if not ids or len(ids)!=len(quantities) or len(ids)>100: raise ValueError('Add at least one valid item.')
            quantities_by_id = defaultdict(int)
            for pid,qty in zip(ids,quantities):
                n = whole(qty)
                if n<1: raise ValueError('Each quantity must be greater than zero.')
                quantities_by_id[int(pid)] += n
            discount = money(request.POST.get('discount','0'))
            payment = request.POST.get('payment_method')
            if payment not in ('cash','momo','card','other'): raise ValueError('Select a payment method.')
            with transaction.atomic():
                locked = Product.objects.select_for_update().filter(pk__in=quantities_by_id,active=True).order_by('pk')
                if locked.count()!=len(quantities_by_id): raise ValueError('One of the products is unavailable.')
                subtotal = Decimal('0.00')
                for p in locked:
                    if p.stock<quantities_by_id[p.pk]: raise ValueError(f'Insufficient stock for {p.name}. Available: {p.stock}.')
                    subtotal += p.selling_price*quantities_by_id[p.pk]
                if discount>subtotal: raise ValueError('Discount cannot exceed subtotal.')
                sale = Sale.objects.create(payment_method=payment,discount=discount,total=subtotal-discount,user=request.user)
                for p in locked:
                    qty = quantities_by_id[p.pk]
                    SaleItem.objects.create(sale=sale,product=p,quantity=qty,unit_price=p.selling_price)
                    p.stock -= qty
                    p.save(update_fields=['stock'])
                    StockMovement.objects.create(product=p,change=-qty,reason='sale',reference=sale.receipt_number,user=request.user)
            return redirect('receipt',pk=sale.pk)
        except (ValueError, Product.DoesNotExist) as exc: messages.error(request,str(exc))
    return render(request,'new_sale.html',{'products':products})

@login_required
def sales(request):
    return render(request,'sales.html',{'rows':Sale.objects.select_related('user').order_by('-id')[:200]})

@login_required
def receipt(request,pk):
    sale = get_object_or_404(Sale.objects.prefetch_related('items__product'),pk=pk)
    subtotal = sum((i.line_total for i in sale.items.all()),Decimal('0.00'))
    return render(request,'receipt.html',{'sale':sale,'subtotal':subtotal})

@login_required
def return_item(request,pk):
    if request.method!='POST': return HttpResponseBadRequest('POST required')
    try:
        qty = whole(request.POST.get('quantity'))
        if qty<1: raise ValueError('Quantity must be greater than zero.')
        with transaction.atomic():
            item = SaleItem.objects.select_for_update().select_related('product').get(pk=request.POST.get('item'),sale_id=pk)
            product = Product.objects.select_for_update().get(pk=item.product_id)
            if qty>item.quantity-item.returned_quantity: raise ValueError('Return quantity exceeds units sold.')
            item.returned_quantity += qty
            item.save(update_fields=['returned_quantity'])
            product.stock += qty
            product.save(update_fields=['stock'])
            StockMovement.objects.create(product=product,change=qty,reason='return',reference=item.sale.receipt_number,note=request.POST.get('note','')[:240],user=request.user)
        messages.success(request,'Returned items added back to stock. Process any refund separately.')
    except (ValueError, SaleItem.DoesNotExist) as exc: messages.error(request,str(exc))
    return redirect('receipt',pk=pk)

@login_required
def reports(request):
    today = timezone.localdate()
    sales = Sale.objects.filter(created_at__date=today)
    total = sales.aggregate(total=Sum('total'))['total'] or Decimal('0.00')
    by_payment = sales.values('payment_method').annotate(amount=Sum('total')).order_by('payment_method')
    low = Product.objects.filter(active=True,stock__lte=F('reorder_level')).order_by('stock')
    return render(request,'reports.html',{'today':today,'total':total,'count':sales.count(),'by_payment':by_payment,'low':low})
