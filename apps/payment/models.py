from django.db import models
from django.utils.text import slugify
from django.contrib.sessions.models import Session

class Category(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True, blank=True, editable=False)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name_plural = "Categories"

class Product(models.Model):
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='products')
    name = models.CharField(max_length=200)
    slug = models.SlugField(unique=True, blank=True, editable=False)
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    image = models.ImageField(upload_to='products/')
    is_available = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_featured = models.BooleanField(default=False)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

class Transaction(models.Model):
    session_id = models.CharField(max_length=255, null=True, blank=True)
    TRANSACTION_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('success', 'Success'),
        ('failure', 'Failure')
    ]
    PAYMENT_TYPE_CHOICES = [
        ('Cash', 'Cash'),
        ('Cashless', 'Cashless')
    ]
    ORDER_STATUS_CHOICES = [
        ('pending payment', 'Pending Payment'),
        ('On Process', 'On Process'),
        ('Completed', 'Completed'),
    ]
    order_id = models.CharField(max_length=255, unique=True)
    gross_amount = models.DecimalField(max_digits=10, decimal_places=2)
    transaction_status = models.CharField(max_length=50, choices=TRANSACTION_STATUS_CHOICES)
    payment_type = models.CharField(max_length=50, choices=PAYMENT_TYPE_CHOICES)
    transaction_time = models.DateTimeField(auto_now_add=True)
    products = models.ManyToManyField(Product, through='OrderItem')
    customer_name = models.CharField(max_length=200)
    customer_email = models.EmailField()
    customer_phone = models.CharField(max_length=20)
    order_status = models.CharField(max_length=50, choices=ORDER_STATUS_CHOICES, default='pending payment')
    
    def __str__(self):
        return self.order_id + ' - ' + self.customer_name + ' - ' + self.transaction_status
      
    def save(self, *args, **kwargs):
        if not self.session_id:
            session = Session.objects.get(session_key=self.request.session.session_key)
            self.session_id = session.session_key
        if self.order_status == 'Completed':
            self.order_status = 'Completed'
        elif self.transaction_status == 'success':
            self.order_status = 'On Process'
        
        super().save(*args, **kwargs)

class OrderItem(models.Model):
    transaction = models.ForeignKey(Transaction, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.IntegerField(default=1)
    price = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.product.name} - {self.quantity}"
