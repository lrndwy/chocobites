from django.contrib import admin

# Register your models here.
from .models import Category, Product, Transaction, OrderItem

admin.site.register(Category)
admin.site.register(Product) 
admin.site.register(Transaction)
admin.site.register(OrderItem)
