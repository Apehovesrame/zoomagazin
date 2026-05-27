from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

app_name = 'store'

urlpatterns = [
    path('', views.index, name='index'),
    path('catalog/', views.catalog, name='catalog'),
    path('product/<int:product_id>/', views.product_detail, name='product_detail'),

    # Регистрация и Личный кабинет
    path('register/', views.register, name='register'),
    path('profile/', views.profile, name='profile'),

    path('profile/edit/', views.edit_profile, name='edit_profile'),

    path('checkout/', views.order_create, name='order_create'),

    path('profile/add-pet/', views.add_pet, name='add_pet'),
    path('catalog/smart/<int:pet_id>/', views.smart_catalog, name='smart_catalog'),

    path('profile/edit-pet/<int:pet_id>/', views.edit_pet, name='edit_pet'),

    path('manager/', views.manager_dashboard, name='manager_dashboard'),
    path('manager/product/add/', views.add_product, name='add_product'),
    path('manager/product/edit/<int:product_id>/', views.edit_product, name='edit_product'),
    path('manager/product/delete/<int:product_id>/', views.delete_product, name='delete_product'),
    path('manager/orders/', views.manager_orders, name='manager_orders'),
    path('manager/orders/<int:order_id>/status/', views.change_order_status, name='change_order_status'),
    path('manager/product-image/delete/<int:image_id>/', views.delete_product_image, name='delete_product_image'),

    path('community/', views.community, name='community'),
    path('community/like/<int:post_id>/', views.like_post, name='like_post'),
    path('community/comment/<int:post_id>/', views.add_comment, name='add_comment'),
    path('community/edit/<int:post_id>/', views.edit_post, name='edit_post'),
    path('community/delete/<int:post_id>/', views.delete_post, name='delete_post'),

    path('pet/<int:pet_id>/', views.pet_detail, name='pet_detail'),

    path('review/<int:review_id>/delete/', views.delete_review, name='delete_review'),
    path('review/<int:review_id>/reply/', views.reply_review, name='reply_review'),

    path('logout/', views.user_logout, name='logout'),

    # Вход и Выход (используем встроенные CBV Django)
    path('login/', auth_views.LoginView.as_view(template_name='store/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='/'), name='logout'),

    # Маршруты Корзины
    path('cart/', views.view_cart, name='cart'),
    path('cart/add/<int:product_id>/', views.add_to_cart, name='add_to_cart'),
    path('cart/update/<int:product_id>/', views.update_cart, name='update_cart'),
    path('cart/remove/<int:product_id>/', views.remove_from_cart, name='remove_from_cart'),

    # Сброс пароля
    path('password-reset/', auth_views.PasswordResetView.as_view(
        template_name='store/password_reset.html',
        success_url='/password-reset/done/',
        email_template_name='store/password_reset_email.html'
    ), name='password_reset'),
    path('password-reset/done/', auth_views.PasswordResetDoneView.as_view(
        template_name='store/password_reset_done.html'
    ), name='password_reset_done'),
    path('password-reset-confirm/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(
        template_name='store/password_reset_confirm.html',
        success_url='/password-reset-complete/'
    ), name='password_reset_confirm'),
    path('password-reset-complete/', auth_views.PasswordResetCompleteView.as_view(
        template_name='store/password_reset_complete.html'
    ), name='password_reset_complete'),
]