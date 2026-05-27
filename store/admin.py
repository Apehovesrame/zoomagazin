from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser, Pet, Product, Order, OrderItem
from .models import Post, Comment, Tag

admin.site.register(Post)
admin.site.register(Comment)
admin.site.register(Tag)

# 1. Настройка отображения пользователей
@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    model = CustomUser
    list_display = ['username', 'email', 'role', 'is_staff']
    # Добавляем поле роли в интерфейс редактирования пользователя
    fieldsets = UserAdmin.fieldsets + (
        ('Дополнительная информация', {'fields': ('role',)}),
    )

# 2. Настройка отображения питомцев
@admin.register(Pet)
class PetAdmin(admin.ModelAdmin):
    list_display = ('name', 'species', 'user', 'age_group', 'weight')
    list_filter = ('species', 'age_group', 'activity_level') # Боковая панель фильтров
    search_fields = ('name', 'user__username')               # Строка поиска


# 3. Настройка отображения товаров
@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'brand', 'category', 'price', 'target_species')
    list_filter = ('category', 'brand', 'target_species')
    search_fields = ('name', 'description', 'brand')

# 4. Вложенное отображение позиций заказа (чтобы товары показывались прямо внутри чека)
class OrderItemInline(admin.TabularInline):
    model = OrderItem
    raw_id_fields = ['product'] # Удобный выбор товара по ID
    extra = 0  # Не показывать лишние пустые строки по умолчанию

# 5. Настройка отображения заказов
@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ['id', 'first_name', 'last_name', 'email', 'phone', 'city', 'paid', 'created_at', 'status']
    list_filter = ['paid', 'created_at', 'status']
    list_editable = ['paid', 'status']
    search_fields = ('id', 'first_name', 'last_name', 'phone')
    inlines = [OrderItemInline]