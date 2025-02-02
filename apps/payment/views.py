from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic import ListView, DetailView
from django.contrib import messages
from .models import Product, Category, Transaction, OrderItem
import midtransclient
from django.conf import settings
import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
import uuid
from django.urls import reverse
import re

class ProductListView(ListView):
    model = Product
    template_name = 'products/product_list.html'
    context_object_name = 'products'
    
    def get_queryset(self):
        queryset = Product.objects.all()
        category_slug = self.request.GET.get('category')
        
        if category_slug:
            queryset = queryset.filter(category__slug=category_slug)
            
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['categories'] = Category.objects.all()
        return context

class ProductDetailView(DetailView):
    model = Product
    template_name = 'products/product_detail.html'
    context_object_name = 'product'

def cart_view(request):
    cart = request.session.get('cart', {})
    cart_items = []
    total = 0
    cart_updated = False
    
    for product_id, quantity in list(cart.items()):
        product = get_object_or_404(Product, id=product_id)
        if not product.is_available:
            del cart[product_id]
            cart_updated = True
            messages.warning(request, f'Produk {product.name} telah dihapus dari keranjang karena tidak tersedia')
            continue
            
        subtotal = product.price * quantity
        total += subtotal
        cart_items.append({
            'product': product,
            'quantity': quantity,
            'subtotal': subtotal
        })
    
    if cart_updated:
        request.session['cart'] = cart
    
    return render(request, 'cart/cart.html', {
        'cart_items': cart_items,
        'total': total
    })

def add_to_cart(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    
    if not product.is_available:
        messages.error(request, f'Maaf, produk {product.name} sedang tidak tersedia')
        return redirect('apps:product_list')
        
    cart = request.session.get('cart', {})
    cart[str(product_id)] = cart.get(str(product_id), 0) + 1
    request.session['cart'] = cart
    messages.success(request, 'Produk berhasil ditambahkan ke keranjang!')
    return redirect('apps:cart')

def remove_from_cart(request, product_id):
    cart = request.session.get('cart', {})
    if str(product_id) in cart:
        del cart[str(product_id)]
        request.session['cart'] = cart
    return redirect('apps:cart')

@require_http_methods(["GET", "POST"])
def checkout(request):
    # Pastikan session sudah dibuat
    if not request.session.session_key:
        request.session.create()
        
    cart = request.session.get('cart', {})
    if not cart:
        messages.error(request, 'Keranjang Anda kosong!')
        return redirect('apps:cart')
    
    # Validasi ketersediaan produk
    unavailable_products = []
    for product_id in cart.keys():
        product = get_object_or_404(Product, id=product_id)
        if not product.is_available:
            unavailable_products.append(product.name)
    
    if unavailable_products:
        messages.error(request, f'Produk berikut tidak tersedia: {", ".join(unavailable_products)}')
        return redirect('apps:cart')

    # Check for pending transaction
    pending_transaction = Transaction.objects.filter(
        customer_email=request.session.get('customer_email', ''),
        transaction_status='pending'
    ).order_by('-transaction_time').first()

    if pending_transaction:
        # Get order items for pending transaction
        order_items = OrderItem.objects.filter(transaction=pending_transaction)
        cart_items = []
        total = 0
        
        for item in order_items:
            subtotal = item.price * item.quantity
            total += subtotal
            cart_items.append({
                'product': item.product,
                'quantity': item.quantity,
                'subtotal': subtotal
            })

        if request.method == 'POST':
            try:
                # Jika pembayaran cash, redirect ke halaman konfirmasi cash
                if pending_transaction.payment_type == 'Cash':
                    request.session['transaction_id'] = pending_transaction.id
                    return JsonResponse({
                        'payment_type': 'Cash',
                        'order_id': pending_transaction.order_id,
                        'redirect_url': reverse('apps:payment_cash_confirmation')
                    })

                # Jika cashless, lanjutkan dengan Midtrans
                snap = midtransclient.Snap(
                    is_production=settings.MIDTRANS_IS_PRODUCTION,
                    server_key=settings.MIDTRANS_SERVER_KEY
                )
                
                # Buat order_id baru untuk transaksi Midtrans
                new_order_id = str(uuid.uuid4())
                
                # Update order_id transaksi yang ada
                pending_transaction.order_id = new_order_id
                pending_transaction.save()

                transaction_params = {
                    'transaction_details': {
                        'order_id': new_order_id,
                        'gross_amount': int(pending_transaction.gross_amount)
                    },
                    'customer_details': {
                        'first_name': pending_transaction.customer_name,
                        'email': pending_transaction.customer_email,
                        'phone': pending_transaction.customer_phone
                    },
                    'credit_card': {
                        'secure': True
                    }
                }
                
                transaction_token = snap.create_transaction_token(transaction_params)
                return JsonResponse({
                    'payment_type': 'Cashless',
                    'token': transaction_token,
                    'order_id': new_order_id
                })

            except Exception as e:
                return JsonResponse({
                    'error': f'Terjadi kesalahan: {str(e)}'
                }, status=500)

        return render(request, 'checkout/checkout.html', {
            'cart_items': cart_items,
            'total': total,
            'midtrans_client_key': settings.MIDTRANS_CLIENT_KEY,
            'midtrans_is_production': settings.MIDTRANS_IS_PRODUCTION,
            'pending_transaction': pending_transaction
        })

    # If no pending transaction, proceed with normal checkout
    cart = request.session.get('cart', {})
    if not cart:
        messages.error(request, 'Keranjang Anda kosong!')
        return redirect('apps:cart')
        
    # Prepare cart items and total
    cart_items = []
    total = 0
    for product_id, quantity in cart.items():
        product = get_object_or_404(Product, id=product_id)
        subtotal = product.price * quantity
        total += subtotal
        cart_items.append({
            'product': product,
            'quantity': quantity,
            'subtotal': subtotal
        })

    if request.method == 'POST':
        try:
            name = request.POST.get('name')
            email = request.POST.get('email')
            phone = request.POST.get('phone')
            payment_type = request.POST.get('payment_type', 'Cashless')
            
            if not all([name, email, phone]):
                return JsonResponse({
                    'error': 'Semua field harus diisi'
                }, status=400)

            request.session['customer_email'] = email
            order_id = str(uuid.uuid4())
            
            # Buat transaksi dengan session_id
            transaction = Transaction.objects.create(
                session_id=request.session.session_key,
                order_id=order_id,
                gross_amount=total,
                transaction_status='pending',
                payment_type=payment_type,
                customer_name=name,
                customer_email=email,
                customer_phone=phone
            )
            
            # Buat order items
            for item in cart_items:
                OrderItem.objects.create(
                    transaction=transaction,
                    product=item['product'],
                    quantity=item['quantity'],
                    price=item['product'].price
                )

            # Jika pembayaran cash
            if payment_type == 'Cash':
                request.session['cart'] = {}
                request.session['transaction_id'] = transaction.id
                return JsonResponse({
                    'payment_type': 'Cash',
                    'order_id': order_id,
                    'redirect_url': reverse('apps:payment_cash_confirmation')
                })

            # Jika cashless, lanjutkan dengan Midtrans
            snap = midtransclient.Snap(
                is_production=settings.MIDTRANS_IS_PRODUCTION,
                server_key=settings.MIDTRANS_SERVER_KEY
            )
                
            # Create Midtrans transaction parameters
            transaction_params = {
                'transaction_details': {
                    'order_id': order_id,
                    'gross_amount': int(total)
                },
                'customer_details': {
                    'first_name': name,
                    'email': email,
                    'phone': phone
                },
                'credit_card': {
                    'secure': True
                }
            }
            
            # Create Midtrans transaction token
            try:
                transaction_token = snap.create_transaction_token(transaction_params)
                
                # Clear cart
                request.session['cart'] = {}
                
                return JsonResponse({
                    'token': transaction_token,
                    'order_id': order_id
                })
            except Exception as e:
                transaction.delete()  # Rollback transaction if Midtrans fails
                return JsonResponse({
                    'error': f'Gagal membuat transaksi Midtrans: {str(e)}'
                }, status=500)
                
        except Exception as e:
            return JsonResponse({
                'error': f'Terjadi kesalahan: {str(e)}'
            }, status=500)
        
    return render(request, 'checkout/checkout.html', {
        'cart_items': cart_items,
        'total': total,
        'midtrans_client_key': settings.MIDTRANS_CLIENT_KEY,
        'midtrans_is_production': settings.MIDTRANS_IS_PRODUCTION
    })

@csrf_exempt
def payment_notification(request):
    if request.method == 'POST':
        notification = json.loads(request.body)
        transaction = get_object_or_404(Transaction, order_id=notification['order_id'])
        transaction.transaction_status = notification['transaction_status']
        transaction.payment_type = notification.get('payment_type', '')
        transaction.save()
        return JsonResponse({'status': 'OK'})

def payment_success(request):
    transaction_id = request.session.get('transaction_id')
    transaction = None
    if transaction_id:
        transaction = get_object_or_404(Transaction, id=transaction_id)
    return render(request, 'payments/payment_status.html', {
        'status': 'success',
        'transaction': transaction
    })

def payment_pending(request):
    transaction_id = request.session.get('transaction_id')
    transaction = None
    if transaction_id:
        transaction = get_object_or_404(Transaction, id=transaction_id)
    return render(request, 'payments/payment_status.html', {
        'status': 'pending',
        'transaction': transaction
    })

def payment_error(request):
    transaction_id = request.session.get('transaction_id')
    transaction = None
    if transaction_id:
        transaction = get_object_or_404(Transaction, id=transaction_id)
    return render(request, 'payments/payment_status.html', {
        'status': 'error',
        'transaction': transaction
    })

def landing_page(request):
    # Ambil kategori yang dipilih dari URL
    category_slug = request.GET.get('category')
    
    # Filter produk berdasarkan kategori
    if category_slug:
        featured_products = Product.objects.filter(
            category__slug=category_slug,
        )
    else:
        featured_products = Product.objects.filter(
            is_featured=True,
        )[:6]  # Batasi 6 produk featured
    
    categories = Category.objects.all()
    
    context = {
        'featured_products': featured_products,
        'categories': categories,
        'current_category': category_slug
    }
    return render(request, 'landing_page.html', context)

@require_http_methods(["POST"])
@csrf_exempt
def update_transaction_status(request):
    if not request.session.session_key:
        request.session.create()
        
    if request.method == 'POST':
        data = json.loads(request.body)
        order_id = data.get('order_id')
        status = data.get('status')
        
        try:
            transaction = Transaction.objects.get(
                order_id=order_id,
                session_id=request.session.session_key
            )
            transaction.transaction_status = status
            transaction.save()
            
            # Hitung ulang jumlah notifikasi untuk session ini
            notification_count = Transaction.objects.filter(
                session_id=request.session.session_key,
                transaction_status__in=['pending', 'process']
            ).count()
            
            return JsonResponse({
                'status': 'success',
                'message': f'Status transaksi berhasil diupdate menjadi {status}',
                'notification_count': notification_count
            })
        except Transaction.DoesNotExist:
            return JsonResponse({
                'status': 'error',
                'message': 'Transaksi tidak ditemukan'
            }, status=404)

def payment_cash_confirmation(request):
    transaction_id = request.session.get('transaction_id')
    transaction = None
    if transaction_id:
        transaction = get_object_or_404(Transaction, id=transaction_id)
        
    if transaction.transaction_status == 'success':
        return render(request, 'payments/payment_status.html', {
            'status': 'success',
            'transaction': transaction
        })
    return render(request, 'payments/payment_cash_confirmation.html', {
        'transaction': transaction
    })

def payment_status(request):
    transaction_id = request.session.get('transaction_id')
    status = request.GET.get('status', '')
    transaction = None
    
    if transaction_id:
        transaction = get_object_or_404(Transaction, id=transaction_id)
    
    return render(request, 'payments/payment_status.html', {
        'status': status,
        'transaction': transaction
    })

@require_http_methods(["POST"])
def update_cart(request, product_id):
    try:
        data = json.loads(request.body)
        action = data.get('action')
        
        cart = request.session.get('cart', {})
        product_id_str = str(product_id)
        
        if product_id_str in cart:
            if action == 'increase':
                cart[product_id_str] += 1
            elif action == 'decrease':
                if cart[product_id_str] > 1:
                    cart[product_id_str] -= 1
                else:
                    del cart[product_id_str]
            
            request.session['cart'] = cart
            
            # Hitung subtotal dan total
            product = get_object_or_404(Product, id=product_id)
            quantity = cart.get(product_id_str, 0)
            subtotal = product.price * quantity
            
            # Hitung total keseluruhan
            total = 0
            for pid, qty in cart.items():
                p = get_object_or_404(Product, id=pid)
                total += p.price * qty
            
            return JsonResponse({
                'success': True,
                'quantity': quantity,
                'subtotal': subtotal,
                'total': total,
                'cart_count': sum(cart.values())
            })
            
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)

class NotificationView(ListView):
    model = Transaction
    template_name = 'notifications/notification_list.html'
    context_object_name = 'transactions'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Filter transaksi berdasarkan session_id
        unpaid_transactions = Transaction.objects.filter(
            session_id=self.request.session.session_key,
            transaction_status='pending'
        ).order_by('-transaction_time')
        
        # Tambahkan order items untuk setiap transaksi
        unpaid = []
        for transaction in unpaid_transactions:
            order_items = OrderItem.objects.filter(transaction=transaction)
            unpaid.append({
                'transaction': transaction,
                'order_items': order_items
            })
        
        context['unpaid'] = unpaid
        
        # Lakukan hal yang sama untuk transaksi dalam proses
        process_transactions = Transaction.objects.filter(
            session_id=self.request.session.session_key,
            order_status='On Process'
        ).order_by('-transaction_time')
        
        on_process = []
        for transaction in process_transactions:
            order_items = OrderItem.objects.filter(transaction=transaction)
            on_process.append({
                'transaction': transaction,
                'order_items': order_items
            })
            
        context['on_process'] = on_process
        
        # Dan untuk transaksi yang selesai
        completed_transactions = Transaction.objects.filter(
            session_id=self.request.session.session_key,
            order_status='Completed'
        ).order_by('-transaction_time')
        
        completed = []
        for transaction in completed_transactions:
            order_items = OrderItem.objects.filter(transaction=transaction)
            completed.append({
                'transaction': transaction,
                'order_items': order_items
            })
            
        context['completed'] = completed
        
        context['midtrans_client_key'] = settings.MIDTRANS_CLIENT_KEY
        context['midtrans_is_production'] = settings.MIDTRANS_IS_PRODUCTION
        
        return context
        

@require_http_methods(["POST"])
@csrf_exempt
def create_snap_token(request):
    # Pastikan session sudah dibuat
    if not request.session.session_key:
        request.session.create()
        
    try:
        data = json.loads(request.body)
        
        # Validasi data yang diperlukan
        required_fields = ['order_id', 'amount', 'customer_name', 'customer_email', 'customer_phone']
        for field in required_fields:
            if not data.get(field):
                return JsonResponse({
                    'error': f'Field {field} harus diisi'
                }, status=400)

        # Validasi format email
        if not re.match(r"[^@]+@[^@]+\.[^@]+", data['customer_email']):
            return JsonResponse({
                'error': 'Format email tidak valid'
            }, status=400)
                
        # Buat instance Snap
        snap = midtransclient.Snap(
            is_production=settings.MIDTRANS_IS_PRODUCTION,
            server_key=settings.MIDTRANS_SERVER_KEY
        )
        
        transaction_params = {
            'transaction_details': {
                'order_id': data['order_id'],
                'gross_amount': int(float(data['amount']))
            },
            'customer_details': {
                'first_name': data['customer_name'],
                'email': data['customer_email'],
                'phone': data['customer_phone']
            },
            'credit_card': {
                'secure': True
            }
        }
        
        transaction_token = snap.create_transaction_token(transaction_params)
        
        # Update transaksi dengan session_id jika belum ada
        transaction = Transaction.objects.get(order_id=data['order_id'])
        if not transaction.session_id:
            transaction.session_id = request.session.session_key
            transaction.save()
        
        return JsonResponse({
            'token': transaction_token
        })
        
    except Exception as e:
        return JsonResponse({
            'error': f'Terjadi kesalahan: {str(e)}'
        }, status=500)
