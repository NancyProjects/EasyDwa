from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import path
from store import views
urlpatterns = [
 path('admin/',admin.site.urls),path('login/',auth_views.LoginView.as_view(template_name='login.html'),name='login'),path('logout/',auth_views.LogoutView.as_view(),name='logout'),
 path('',views.dashboard,name='dashboard'),path('products/',views.products,name='products'),path('products/new/',views.product_edit,name='product_new'),path('products/<int:pk>/edit/',views.product_edit,name='product_edit'),
 path('stock/',views.stock,name='stock'),path('sales/new/',views.new_sale,name='new_sale'),path('sales/',views.sales,name='sales'),path('sales/<int:pk>/',views.receipt,name='receipt'),path('sales/<int:pk>/return/',views.return_item,name='return_item'),path('reports/',views.reports,name='reports')]
