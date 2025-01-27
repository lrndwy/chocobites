from django.urls import path
from apps.payment.views import (
	ProductListView, 
	ProductDetailView,
	cart_view,
	add_to_cart,
	remove_from_cart,
	checkout,
	payment_notification,
	payment_success,
	payment_pending,
	payment_error,
	landing_page,
	update_transaction_status,
	payment_cash_confirmation,
	payment_status,
	update_cart,
	NotificationView,
	create_snap_token
)

app_name = 'apps'

urlpatterns = [
	path('', landing_page, name='landing_page'),
	path('product/', ProductListView.as_view(), name='product_list'),
	path('product/<slug:slug>/', ProductDetailView.as_view(), name='product_detail'),
	path('cart/', cart_view, name='cart'),
	path('cart/add/<int:product_id>/', add_to_cart, name='add_to_cart'),
	path('cart/remove/<int:product_id>/', remove_from_cart, name='remove_from_cart'),
	path('checkout/', checkout, name='checkout'),
	path('payment/notification/', payment_notification, name='payment_notification'),
	path('payment/success/', payment_success, name='payment_success'),
	path('payment/pending/', payment_pending, name='payment_pending'),
	path('payment/error/', payment_error, name='payment_error'),
	path('update-transaction-status/', update_transaction_status, name='update_transaction_status'),
	path('payment/cash-confirmation/', payment_cash_confirmation, name='payment_cash_confirmation'),
	path('payment/status/', payment_status, name='payment_status'),
	path('update-cart/<int:product_id>/', update_cart, name='update_cart'),
	path('notifications/', NotificationView.as_view(), name='notifications'),
	path('create-snap-token/', create_snap_token, name='create_snap_token'),
]
