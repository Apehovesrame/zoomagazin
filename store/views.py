from django.db.models import Q
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from .models import Product, OrderItem, Pet, ImageGallery
from .forms import CustomUserCreationForm, UserUpdateForm, OrderCreateForm, PetForm, ProductForm
from django.contrib.auth import logout
from django.contrib import messages
from django.contrib.auth.decorators import user_passes_test
from django.shortcuts import render, redirect, get_object_or_404
from django.core.paginator import Paginator
from .models import Order
from django.views.decorators.http import require_POST
import re
from .models import Post, Comment, Tag
from django.db.models import Avg, Q
from .forms import CustomUserCreationForm, UserUpdateForm, OrderCreateForm, PetForm, ProductForm, PostForm, CommentForm, ReviewForm
from django.urls import reverse
from django.http import JsonResponse
from django.db.models import Avg, Count, F
from django.core.mail import send_mail
from django.conf import settings
import datetime
from django.utils import timezone
from .forms import OrderCancelForm



def index(request):
    """Главная страница магазина"""
    latest_products = Product.objects.annotate(
        avg_rating=Avg('reviews__rating'),
        review_count=Count('reviews', distinct=True)
    ).order_by('-id')[:3]

    return render(request, 'store/index.html', {'latest_products': latest_products})

def user_logout(request):
    """Выход пользователя из системы"""
    logout(request)
    return redirect('store:index')


def catalog(request):
    """Каталог товаров с поиском, категориями, брендами, ценой, сортировкой и умным подбором"""

    # 1. Сбор базовых параметров из GET-запроса
    query = request.GET.get('q', '')
    selected_category = request.GET.get('category', '')
    selected_brands = request.GET.getlist('brand')  # ТЕПЕРЬ ЭТО СПИСОК (для галочек)
    sort_by = request.GET.get('sort', 'popular')  # ПОПУЛЯРНОЕ ПО УМОЛЧАНИЮ
    min_price = request.GET.get('min_price', '')  # МИН. ЦЕНА
    max_price = request.GET.get('max_price', '')  # МАКС. ЦЕНА

    # Параметры умного подбора
    species = request.GET.get('species')
    age = request.GET.get('age')
    weight = request.GET.get('weight')
    activity = request.GET.get('activity')

    # 2. Базовый QuerySet с подсчетом рейтинга
    products = Product.objects.annotate(
        avg_rating=Avg('reviews__rating'),
        review_count=Count('reviews', distinct=True)
    ).filter(stock__gt=0)

    # 3. Применяем текстовый поиск
    if query:
        products = products.filter(Q(name__icontains=query))

    # 4. Применяем фильтры по категориям, БРЕНДАМ и ЦЕНЕ
    if selected_category:
        products = products.filter(category=selected_category)

    if selected_brands:
        products = products.filter(brand__in=selected_brands)  # Поиск по нескольким брендам сразу

    if min_price:
        products = products.filter(price__gte=min_price)  # Цена ОТ
    if max_price:
        products = products.filter(price__lte=max_price)  # Цена ДО

    # 5. Алгоритм Умного подбора
    if species or age or weight or activity:
        if species:
            products = products.filter(
                Q(target_species=species) | Q(target_species__isnull=True) | Q(target_species=''))
        if age:
            products = products.filter(Q(target_age=age) | Q(target_age__isnull=True) | Q(target_age=''))
        if activity:
            products = products.filter(
                Q(target_activity=activity) | Q(target_activity__isnull=True) | Q(target_activity=''))
        if weight:
            try:
                w = float(weight.replace(',', '.'))
                products = products.filter(
                    (Q(min_weight__isnull=True) | Q(min_weight__lte=w)) &
                    (Q(max_weight__isnull=True) | Q(max_weight__gte=w))
                )
            except ValueError:
                pass

    # 6. Применяем сортировку контента
    if sort_by == 'newest':
        products = products.order_by('-id')
    elif sort_by == 'price_asc':
        products = products.order_by('price')
    elif sort_by == 'price_desc':
        products = products.order_by('-price')
    elif sort_by == 'rating':
        products = products.order_by(F('avg_rating').desc(nulls_last=True), '-review_count')
    else:  # popular (Популярное — сортировка по числу отзывов)
        products = products.order_by('-review_count', F('avg_rating').desc(nulls_last=True))
        sort_by = 'popular'

    # 7. Списки уникальных категорий и брендов для фильтров
    categories = Product.objects.exclude(category__isnull=True).exclude(category__exact='').values_list('category',
                                                                                                        flat=True).distinct()
    brands = Product.objects.exclude(brand__isnull=True).exclude(brand__exact='').values_list('brand',
                                                                                              flat=True).distinct()

    # 8. Пагинация
    paginator = Paginator(products, 9)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'query': query,
        'categories': categories,
        'brands': brands,
        'selected_category': selected_category,
        'selected_brands': selected_brands,  # Передаем список выбранных брендов
        'current_sort': sort_by,
        'min_price': min_price,
        'max_price': max_price,
        'is_filtered': bool(species or age or weight or activity or min_price or max_price or selected_brands)
    }
    return render(request, 'store/catalog.html', context)


def product_detail(request, product_id):
    """Страница карточки товара с отзывами и рейтингом"""
    product = get_object_or_404(Product, id=product_id)

    # 1. Базовый запрос отзывов
    reviews = product.reviews.all().order_by('-created_at')
    total_reviews_count = reviews.count()

    # 2. Новая логика фильтрации (Высокие / Низкие)
    review_filter = request.GET.get('review_filter', 'all')
    if review_filter == 'high':
        reviews = reviews.filter(rating__gte=4)  # 4 и 5 звезд
    elif review_filter == 'low':
        reviews = reviews.filter(rating__lte=3)  # 1, 2 и 3 звезды

    # 3. Подсчет средней оценки
    avg_rating = product.reviews.aggregate(Avg('rating'))['rating__avg']

    # 4. Сбор статистики для шкалы (прогресс-бары)
    rating_stats = []
    if total_reviews_count > 0:
        for star in range(5, 0, -1):  # Цикл от 5 до 1
            count = product.reviews.filter(rating=star).count()
            percent = (count / total_reviews_count) * 100
            rating_stats.append({'star': star, 'count': count, 'percent': percent})

    existing_review = None
    if request.user.is_authenticated:
        existing_review = product.reviews.filter(user=request.user).first()

    if request.method == 'POST' and request.user.is_authenticated:
        form = ReviewForm(request.POST, instance=existing_review)
        if form.is_valid():
            review = form.save(commit=False)
            review.product = product
            review.user = request.user
            review.save()

            if existing_review:
                messages.success(request, 'Ваш отзыв успешно обновлен!')
            else:
                messages.success(request, 'Спасибо за ваш отзыв!')
            return redirect('store:product_detail', product_id=product.id)
    else:
        form = ReviewForm(instance=existing_review) if existing_review else ReviewForm()

    return render(request, 'store/product_detail.html', {
        'product': product,
        'reviews': reviews,
        'avg_rating': avg_rating,
        'total_reviews_count': total_reviews_count,
        'current_filter': review_filter,
        'rating_stats': rating_stats,
        'form': form,
        'existing_review': existing_review  # Передаем в шаблон
    })

@login_required
def delete_review(request, review_id):
    """Удаление отзыва автором или администратором"""
    from .models import Review
    review = get_object_or_404(Review, id=review_id)
    product_id = review.product.id

    # Проверка прав: текущий юзер — автор отзыва ИЛИ он админ/персонал
    if review.user == request.user or request.user.is_staff or getattr(request.user, 'role', '') == 'admin':
        review.delete()
        messages.success(request, 'Отзыв успешно удален.')
    else:
        messages.error(request, 'У вас нет прав для удаления этого отзыва.')

    return redirect('store:product_detail', product_id=product_id)


@login_required
def reply_review(request, review_id):
    """Добавление ответа администратора на отзыв"""
    from .models import Review
    review = get_object_or_404(Review, id=review_id)

    # Проверка прав менеджера/администратора
    if request.user.is_staff or getattr(request.user, 'role', '') == 'admin':
        if request.method == 'POST':
            reply_text = request.POST.get('reply_text', '').strip()
            if reply_text:
                review.admin_reply = reply_text
                review.save()
                messages.success(request, 'Ответ на отзыв успешно опубликован.')
            else:
                messages.error(request, 'Текст ответа не может быть пустым.')
    else:
        messages.error(request, 'Только администратор может отвечать на отзывы.')

    return redirect('store:product_detail', product_id=review.product.id)

def register(request):
    """Регистрация нового пользователя"""
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)  # Сразу авторизуем после регистрации
            return redirect('store:index')
    else:
        form = CustomUserCreationForm()
    return render(request, 'store/register.html', {'form': form})


@login_required
def profile(request):
    orders = request.user.orders.all().order_by('-created_at')
    pets = request.user.pets.all()

    context = {
        'orders': orders,
        'pets': pets,
    }
    return render(request, 'store/profile.html', context)


@login_required
def edit_profile(request):
    """Редактирование личных данных пользователя"""
    if request.method == 'POST':
        # Передаем request.FILES для загрузки аватарки!
        form = UserUpdateForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Ваш профиль успешно обновлен!')
            return redirect('store:profile')
    else:
        # Предзаполняем форму текущими данными
        form = UserUpdateForm(instance=request.user)

    return render(request, 'store/edit_profile.html', {'form': form})


@login_required
def delete_avatar(request):
    if request.method == 'POST':
        user = request.user
        if user.avatar:
            # Удаляем файл с сервера
            user.avatar.delete()
            # Обнуляем поле в базе
            user.avatar = None
            user.save()
            messages.success(request, 'Аватар успешно удален.')
    return redirect('store:edit_profile')

def remove_from_cart(request, product_id):
    """Удаление товара из корзины"""
    cart = request.session.get('cart', {})
    product_id_str = str(product_id)

    if product_id_str in cart:
        del cart[product_id_str]
        request.session['cart'] = cart

    return redirect('store:cart')

def view_cart(request):
    """Отображение страницы корзины"""
    cart = request.session.get('cart', {})
    cart_items = []
    total_price = 0

    # Проходим по всем товарам в сессии, достаем их из базы и считаем сумму
    for p_id, quantity in cart.items():
        product = get_object_or_404(Product, id=int(p_id))
        item_total = product.price * quantity
        total_price += item_total
        cart_items.append({
            'product': product,
            'quantity': quantity,
            'item_total': item_total
        })

    context = {
        'cart_items': cart_items,
        'total_price': total_price,
    }
    return render(request, 'store/cart.html', context)


def add_to_cart(request, product_id):
    """Добавление товара в корзину (с защитой от превышения остатков)"""
    cart = request.session.get('cart', {})
    product_id_str = str(product_id)
    product = get_object_or_404(Product, id=product_id)

    # Определяем добавляемое количество
    if request.method == 'POST':
        quantity = int(request.POST.get('quantity', 1))
    else:
        quantity = 1

    current_qty = cart.get(product_id_str, 0)

    # ПРОВЕРКА: Если то, что уже в корзине + то, что хотят добавить, превышает склад
    if current_qty + quantity > product.stock:
        messages.error(
            request,
            f'Невозможно добавить товар в таком количестве! На складе осталось всего {product.stock} шт. '
            f'(В вашей корзине уже находится {current_qty} шт.)'
        )
        return redirect(request.META.get('HTTP_REFERER', 'store:catalog'))

    cart[product_id_str] = current_qty + quantity
    request.session['cart'] = cart
    messages.success(request, 'Товар успешно добавлен в корзину.')
    return redirect('store:cart')


def update_cart(request, product_id):
    """Обновление точного количества товара прямо из корзины (с защитой от превышения)"""
    if request.method == 'POST':
        cart = request.session.get('cart', {})
        product_id_str = str(product_id)
        quantity = int(request.POST.get('quantity', 1))
        product = get_object_or_404(Product, id=product_id)

        # ПРОВЕРКА: Предотвращаем ручной ввод числа, превышающего склад
        if quantity > product.stock:
            messages.warning(request,
                             f'Количество товара было автоматически уменьшено до доступного остатка: {product.stock} шт.')
            cart[product_id_str] = product.stock
        elif quantity > 0:
            cart[product_id_str] = quantity  # Устанавливаем новое значение
        else:
            if product_id_str in cart:
                del cart[product_id_str]  # Если ввели 0 или меньше, удаляем товар

        request.session['cart'] = cart

    return redirect('store:cart')


def order_create(request):
    """Оформление заказа с валидацией остатков и блокировкой изменения почты"""
    cart = request.session.get('cart', {})
    if not cart:
        return redirect('store:catalog')

    # ФИНАЛЬНАЯ ПРОВЕРКА: Не раскупили ли товар, пока клиент заполнял форму заказа
    for p_id, quantity in cart.items():
        product = get_object_or_404(Product, id=int(p_id))
        if product.stock < quantity:
            messages.error(
                request,
                f'Извините, пока вы оформляли заказ, товар "{product.name}" закончился или его осталось меньше. '
                f'Доступно на складе: {product.stock} шт. Пожалуйста, измените состав корзины.'
            )
            return redirect('store:cart')

    # Выделяем текущего пользователя для передачи в форму
    current_user = request.user if request.user.is_authenticated else None

    if request.method == 'POST':
        # Передаем POST-данные и именованный аргумент user
        form = OrderCreateForm(request.POST, user=current_user)
        if form.is_valid():
            order = form.save(commit=False)

            if request.user.is_authenticated:
                order.user = request.user
                # Жесткая безопасность: принудительно пишем Email из аккаунта, игнорируя любые подмены
                order.email = request.user.email

            order.save()

            # Переносим товары из корзины в OrderItem + списываем остатки со склада
            for p_id, quantity in cart.items():
                product = get_object_or_404(Product, id=int(p_id))
                OrderItem.objects.create(
                    order=order,
                    product=product,
                    price_at_purchase=product.price,
                    quantity=quantity
                )

                # Списание остатков
                if product.stock >= quantity:
                    product.stock -= quantity
                else:
                    product.stock = 0
                product.save()

            # Очищаем корзину после успешного заказа
            request.session['cart'] = {}

            # --- БЛОК ОТПРАВКИ EMAIL УВЕДОМЛЕНИЯ КЛИЕНТУ ---
            if order.email:
                subject = f'Ваш заказ №{order.id} успешно оформлен — Зоомагазин'
                message = (
                    f'Здравствуйте, {order.first_name}!\n\n'
                    f'Спасибо за ваш заказ в нашем зоомагазине!\n'
                    f'Номер вашего заказа: {order.id}.\n'
                    f'Сумма заказа: {order.get_total_cost()} руб.\n\n'
                    f'Ваш заказ принят в работу. Мы пришлем вам уведомление, когда его статус изменится.\n'
                    f'Отслеживать статус заказа можно в вашем личном кабинете.'
                )
                try:
                    from django.core.mail import send_mail
                    from django.conf import settings
                    send_mail(
                        subject=subject,
                        message=message,
                        from_email=settings.DEFAULT_FROM_EMAIL,
                        recipient_list=[order.email],
                        fail_silently=False,
                    )
                except Exception as e:
                    print(f"Ошибка отправки приветственного письма: {e}")
            # --- КОНЕЦ БЛОКА ОТПРАВКИ ---

            messages.success(request, 'Заказ успешно оформлен!')
            return render(request, 'store/order_created.html', {'order': order})
    else:
        # Предзаполняем данные, если пользователь вошел в систему
        initial_data = {}
        if request.user.is_authenticated:
            initial_data = {
                'first_name': request.user.first_name,
                'last_name': request.user.last_name,
                'email': request.user.email,
                # НОВОЕ: Подтягиваем город и адрес из профиля
                'city': getattr(request.user, 'city', ''),
                'address': getattr(request.user, 'address', ''),
            }

        form = OrderCreateForm(initial=initial_data, user=current_user)

    return render(request, 'store/order_checkout.html', {'form': form})


@login_required
def add_pet(request):
    if request.method == 'POST':
        # ВАЖНО: передаем request.FILES для загрузки фото
        form = PetForm(request.POST, request.FILES)
        if form.is_valid():
            pet = form.save(commit=False)
            pet.user = request.user
            pet.save()

            # Сохраняем фото в галерею
            files = request.FILES.getlist('images_input')
            for f in files:
                ImageGallery.objects.create(pet=pet, image=f)

            messages.success(request, f'Питомец {pet.name} успешно добавлен в ваш профиль!')
            return redirect('store:profile')
    else:
        form = PetForm()
    return render(request, 'store/add_pet.html', {'form': form})


@login_required
def delete_pet(request, pet_id):
    """Удаление питомца из профиля"""
    # Ищем питомца, строго проверяя, что он принадлежит текущему пользователю
    pet = get_object_or_404(Pet, id=pet_id, owner=request.user)

    # Сохраняем имя для красивого уведомления
    pet_name = pet.name
    pet.delete()

    messages.success(request, f'Питомец "{pet_name}" успешно удален из вашего профиля.')
    return redirect('store:profile')

@login_required
def delete_pet_image(request, image_id):
    """Удаление конкретной фотографии питомца из галереи"""
    image = get_object_or_404(ImageGallery, id=image_id)
    pet = image.pet

    # Безопасность: проверяем, что питомец принадлежит текущему пользователю
    if pet.user != request.user:
        messages.error(request, "У вас нет прав для удаления этого фото.")
        return redirect('store:profile')

    image.delete()
    messages.success(request, 'Фотография питомца успешно удалена.')

    # Возвращаем пользователя обратно на страницу редактирования
    return redirect('store:edit_pet', pet_id=pet.id)

@login_required
def edit_pet(request, pet_id):
    # Достаем питомца, проверяя, что он принадлежит текущему пользователю
    pet = get_object_or_404(Pet, id=pet_id, user=request.user)

    if request.method == 'POST':
        # ИСПРАВЛЕНО: Добавили request.FILES вторым аргументом, чтобы фото успешно прилетало на сервер
        form = PetForm(request.POST, request.FILES, instance=pet)
        if form.is_valid():
            form.save()

            # Если пользователь при редактировании прикрепил новые фото в галерею — сохраняем их
            files = request.FILES.getlist('images_input')
            for f in files:
                ImageGallery.objects.create(pet=pet, image=f)

            messages.success(request, f'Данные питомца {pet.name} успешно обновлены!')
            return redirect('store:profile')
    else:
        form = PetForm(instance=pet)

    return render(request, 'store/edit_pet.html', {'form': form, 'pet': pet})


@login_required
def pet_detail(request, pet_id):
    # Получаем питомца
    pet = get_object_or_404(Pet, id=pet_id)

    # Получаем только посты ЭТОГО питомца
    posts = Post.objects.filter(pet=pet).select_related('author', 'pet').prefetch_related('tags', 'likes').annotate(
        num_likes=Count('likes', distinct=True),
        num_comments=Count('comments', distinct=True)
    ).order_by('-created_at')

    return render(request, 'store/pet_detail.html', {
        'pet': pet,
        'posts': posts,
    })

@login_required
def smart_catalog(request, pet_id):
    """Каталог, отфильтрованный под конкретного питомца (Умный подбор)"""
    pet = get_object_or_404(Pet, id=pet_id, user=request.user)

    products = Product.objects.filter(category='Корма').order_by('-id')

    products = products.filter(
        Q(target_species=pet.species) | Q(target_species__isnull=True) | Q(target_species='')
    ).filter(
        Q(target_age=pet.age_group) | Q(target_age__isnull=True) | Q(target_age='')
    ).filter(
        Q(min_weight__lte=pet.weight) | Q(min_weight__isnull=True)
    ).filter(
        Q(max_weight__gte=pet.weight) | Q(max_weight__isnull=True)
    ).filter(
        Q(target_activity=pet.activity_level) | Q(target_activity__isnull=True) | Q(target_activity='')
    )

    # ДОБАВИЛИ ПАГИНАЦИЮ И СЮДА ТОЖЕ
    paginator = Paginator(products, 9)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,  # Теперь передаем page_obj, как и требует шаблон
        'active_pet': pet,
        'is_filtered': True
    }
    return render(request, 'store/catalog.html', context)


# Проверяем, является ли пользователь администратором магазина
def is_store_admin(user):
    return user.is_authenticated and user.role == 'admin'


# Защищаем страницу: пустит только тех, кто прошел проверку is_store_admin
@user_passes_test(is_store_admin, login_url='store:index')
def manager_dashboard(request):
    """Главная страница панели управления магазином"""
    # Получаем все товары, чтобы вывести их в таблицу
    products = Product.objects.all().order_by('-id')

    context = {
        'products': products
    }
    return render(request, 'store/manager_dashboard.html', context)

@user_passes_test(is_store_admin, login_url='store:index')
def add_product(request):
    """Добавление нового товара администратором магазина"""
    if request.method == 'POST':
        # Обязательно передаем request.FILES для загрузки изображения товара
        form = ProductForm(request.POST, request.FILES)
        if form.is_valid():
            product = form.save()

            files = request.FILES.getlist('images_input')
            for f in files:
                 ImageGallery.objects.create(product=product, image=f)

            messages.success(request, f'Товар «{product.name}» успешно добавлен!')
            return redirect('store:manager_dashboard')
    else:
        form = ProductForm()

    categories = Product.objects.values_list('category', flat=True).distinct()

    return render(request, 'store/add_product.html', {
        'form': form,
        'categories': categories
    })


@user_passes_test(is_store_admin, login_url='store:index')
def edit_product(request, product_id):
    """Редактирование существующего товара"""
    product = get_object_or_404(Product, id=product_id)

    if request.method == 'POST':
        # instance=product указывает, что мы обновляем запись, а не создаем новую
        form = ProductForm(request.POST, request.FILES, instance=product)
        if form.is_valid():
            form.save()

            files = request.FILES.getlist('images_input')
            for f in files:
                ImageGallery.objects.create(product=product, image=f)

            messages.success(request, f'Товар «{product.name}» успешно обновлен!')
            return redirect('store:manager_dashboard')
    else:
        form = ProductForm(instance=product)

    categories = Product.objects.values_list('category', flat=True).distinct()
    return render(request, 'store/edit_product.html', {
        'form': form,
        'product': product,
        'categories': categories
    })


@user_passes_test(is_store_admin, login_url='store:index')
def delete_product(request, product_id):
    """Удаление товара"""
    product = get_object_or_404(Product, id=product_id)

    if request.method == 'POST':
        name = product.name
        product.delete()
        messages.success(request, f'Товар «{name}» был удален из каталога.')
        return redirect('store:manager_dashboard')

    return render(request, 'store/delete_product.html', {'product': product})


@login_required
def request_order_cancel(request, order_id):
    """Страница опросника и отправка запроса на отмену заказа"""
    order = get_object_or_404(Order, id=order_id, user=request.user)

    # Защита: отменить можно только заказ, который еще в работе
    if order.status != 'in_progress':
        messages.error(request, 'Этот заказ сейчас нельзя отменить.')
        return redirect('store:profile')

    if request.method == 'POST':
        # Создаем форму, привязанную к конкретному объекту заказа (instance=order)
        form = OrderCancelForm(request.POST, instance=order)
        if form.is_valid():
            # Сохраняем причину отмены и меняем статус заказа
            order = form.save(commit=False)
            order.status = 'cancel_requested'
            order.save()

            messages.warning(request,
                             f'Запрос на отмену заказа №{order.id} отправлен администрации. Спасибо, что объяснили причину!')
            return redirect('store:profile')
    else:
        # При первом заходе на страницу создаем пустую форму
        form = OrderCancelForm(instance=order)

    return render(request, 'store/order_cancel.html', {
        'form': form,
        'order': order
    })


@user_passes_test(is_store_admin, login_url='store:index')
def manager_orders(request):
    """Панель управления заказами для администратора с архивом и поиском"""

    # 1. Получаем параметры фильтрации из GET-запроса
    client_query = request.GET.get('client', '').strip()
    date_query = request.GET.get('date', '')
    status_query = request.GET.get('status', '')

    # Base queryset
    orders = Order.objects.all().order_by('-created_at')

    # 2. Применяем фильтры, если они указаны
    if client_query:
        orders = orders.filter(
            Q(first_name__icontains=client_query) |
            Q(last_name__icontains=client_query) |
            Q(user__username__icontains=client_query)
        )
    if date_query:
        orders = orders.filter(created_at__date=date_query)
    if status_query:
        orders = orders.filter(status=status_query)

    # 3. РАЗДЕЛЕНИЕ НА АКТИВНЫЕ И АРХИВ (Выполненные и Отмененные улетают в архив)
    active_orders = orders.exclude(status__in=['completed', 'cancelled'])
    archived_orders = orders.filter(status__in=['completed', 'cancelled'])

    # Список статусов для выпадающего списка в фильтрах
    status_choices = Order.STATUS_CHOICES

    return render(request, 'store/manager_orders.html', {
        'active_orders': active_orders,
        'archived_orders': archived_orders,
        'status_choices': status_choices,
        'client_query': client_query,
        'date_query': date_query,
        'status_query': status_query,
    })


@require_POST
@user_passes_test(is_store_admin, login_url='store:index')
def change_order_status(request, order_id):
    """Быстрое изменение статуса заказа менеджером с уведомлением клиента по Email"""
    order = get_object_or_404(Order, id=order_id)
    new_status = request.POST.get('status')

    valid_statuses = [choice[0] for choice in Order.STATUS_CHOICES]
    if new_status in valid_statuses:
        order.status = new_status
        order.save()

        # Логика отправки уведомления на почту клиента
        if order.email:  # Проверяем, заполнено ли поле email в заказе
            subject = f'Обновление статуса заказа №{order.id} — Зоомагазин'
            message = (
                f'Здравствуйте, {order.first_name} {order.last_name}!\n\n'
                f'Статус вашего заказа №{order.id} изменился.\n'
                f'Новый статус: "{order.get_status_display()}".\n\n'
                f'Вы можете отслеживать изменения в вашем личном кабинете.\n'
                f'Спасибо, что выбрали наш зоомагазин!'
            )

            try:
                send_mail(
                    subject=subject,
                    message=message,
                    from_email=settings.DEFAULT_FROM_EMAIL,  # Отправитель из settings.py (m.zonin@mail.ru)
                    recipient_list=[order.email],  # Почта покупателя
                    fail_silently=False,  # Выбросит исключение, если что-то пойдет не так
                )
                messages.success(
                    request,
                    f'Статус заказа №{order.id} успешно изменен на «{order.get_status_display()}». Уведомление отправлено на {order.email}.'
                )
            except Exception as e:
                # Если упал интернет или Mail.ru заблокировал сессию, менеджер узнает об этом, но статус сохранится
                messages.warning(
                    request,
                    f'Статус заказа №{order.id} изменен на «{order.get_status_display()}», но Email-уведомление не ушло. Ошибка: {e}'
                )
        else:
            messages.success(
                request,
                f'Статус заказа №{order.id} успешно изменен на «{order.get_status_display()}» (Email клиента не указан).'
            )
    else:
        messages.error(request, 'Ошибка: выбран неверный статус.')

    return redirect('store:manager_orders')


@login_required
def community(request):
    """Главная страница Сообщества (Лента) с фильтрацией и сортировкой"""

    # --- БЛОК ОБРАБОТКИ POST (СОЗДАНИЕ ПОСТА) ---
    if request.method == 'POST':
        form = PostForm(request.POST, request.FILES, user=request.user)
        if form.is_valid():
            new_post = form.save(commit=False)
            new_post.author = request.user

            # 1. Берем исходный текст, который ввел пользователь (например: "23456н6543 #Боб #Собака")
            raw_text = new_post.text

            # 2. Ищем все хештеги (поддерживаем и русский, и английский)
            hashtags = re.findall(r'#([а-яА-ЯёЁa-zA-Z0-9_]+)', raw_text)

            # 3. САМОЕ ГЛАВНОЕ: Удаляем хештеги из текста!
            # Заменяем их на пустоту и убираем лишние пробелы по краям
            cleaned_text = re.sub(r'#[а-яА-ЯёЁa-zA-Z0-9_]+', '', raw_text).strip()

            # 4. Присваиваем посту очищенный текст ("23456н6543")
            new_post.text = cleaned_text

            # 5. И только ТЕПЕРЬ сохраняем пост в базу данных!
            new_post.save()

            # Логика загрузки нескольких фото
            files = request.FILES.getlist('images_input')
            for f in files:
                ImageGallery.objects.create(post=new_post, image=f)

            # 6. Привязываем хештеги (чтобы появились синие кнопки снизу)
            for tag_name in hashtags:
                tag, created = Tag.objects.get_or_create(name=tag_name.lower())
                new_post.tags.add(tag)

            messages.success(request, 'Пост успешно опубликован!')
            return redirect('store:community')
    else:
        form = PostForm(user=request.user)

    # --- БЛОК СОРТИРОВКИ И ФИЛЬТРАЦИИ (GET) ---
    # 1. Читаем параметры фильтрации и сортировки из URL
    sort_param = request.GET.get('sort', 'newest')
    filter_param = request.GET.get('filter', 'all')
    tag_filter = request.GET.get('tag')  # сохраняем твой фильтр по тегам

    # 2. Базовый запрос с твоей оптимизацией + подсчет лайков/комментов (annotate)
    posts = Post.objects.select_related('author', 'pet').prefetch_related('tags', 'likes').annotate(
        num_likes=Count('likes', distinct=True),
        num_comments=Count('comments', distinct=True)
    )

    # 3. Применяем фильтр по типу постов / животным
    if tag_filter:
        # Твой старый фильтр по хештегу (если кликнули на #тег)
        posts = posts.filter(tags__name=tag_filter)
    elif filter_param == 'general':
        # Общие темы (где питомец НЕ привязан)
        posts = posts.filter(pet__isnull=True)
    elif filter_param != 'all':
        # Конкретный вид животного (Кошка / Собака), проверяем поле species у связанной модели Pet
        posts = posts.filter(pet__species=filter_param)

    # 4. Применяем логику сортировки
    if sort_param == 'oldest':
        posts = posts.order_by('created_at')
    elif sort_param == 'likes':
        posts = posts.order_by('-num_likes', '-created_at')
    elif sort_param == 'comments':
        posts = posts.order_by('-num_comments', '-created_at')
    else:  # newest (по умолчанию)
        posts = posts.order_by('-created_at')

    return render(request, 'store/community.html', {
        'posts': posts,
        'form': form,
        'tag_filter': tag_filter,
        'current_sort': sort_param,  # Передаем в шаблон, чтобы выпадающий список помнил выбор
        'current_filter': filter_param,  # Передаем в шаблон, чтобы выпадающий список помнил выбор
    })


@login_required
def like_post(request, post_id):
    if request.method == 'POST':
        post = get_object_or_404(Post, id=post_id)

        if request.user in post.likes.all():
            post.likes.remove(request.user)
            liked = False
        else:
            post.likes.add(request.user)
            liked = True

        # Возвращаем JSON-ответ (только данные, без перезагрузки HTML)
        return JsonResponse({
            'liked': liked,
            'likes_count': post.likes.count()
        })
    return JsonResponse({'error': 'Invalid request'}, status=400)


@login_required
def add_comment(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    if request.method == 'POST':
        text = request.POST.get('text')
        if text:
            comment = Comment.objects.create(post=post, author=request.user, text=text)

            # Если это AJAX запрос, возвращаем данные нового комментария
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': True,
                    'author': comment.author.username,
                    'author_initial': comment.author.username[0].upper(),
                    'text': comment.text,
                    'date': comment.created_at.strftime("%d.%m.%Y %H:%M"),
                    'comments_count': post.comments.count()
                })

    # На случай, если у кого-то отключен JS, оставляем старый редирект как запасной вариант
    from django.urls import reverse
    return redirect(f"{reverse('store:community')}#post-{post.id}")

@user_passes_test(is_store_admin, login_url='store:index')
def delete_product_image(request, image_id):
    image = get_object_or_404(ImageGallery, id=image_id)
    product_id = image.product.id
    image.delete()
    messages.success(request, 'Фотография удалена.')
    return redirect('store:edit_product', product_id=product_id)


@login_required
def edit_post(request, post_id):
    post = get_object_or_404(Post, id=post_id)

    if post.author != request.user:
        messages.error(request, "У вас нет прав для редактирования этого поста.")
        return redirect('store:community')

    # --- БЛОК ОБРАБОТКИ POST (СОЗДАНИЕ ПОСТА) ---
    if request.method == 'POST':
        form = PostForm(request.POST, instance=post)
        if form.is_valid():
            # Просто сохраняем обновленный текст
            updated_post = form.save()

            # Ищем теги
            hashtags = re.findall(r'#([а-яА-ЯёЁa-zA-Z0-9_]+)', updated_post.text)

            # Очищаем старые связи и привязываем новые
            updated_post.tags.clear()
            for tag_name in hashtags:
                tag_obj, _ = Tag.objects.get_or_create(name=tag_name.lower())
                updated_post.tags.add(tag_obj)

            files = request.FILES.getlist('images_input')
            for f in files:
                ImageGallery.objects.create(post=updated_post, image=f)

            messages.success(request, "Пост успешно обновлен!")
            return redirect('store:community')
    else:
        form = PostForm(instance=post)

    return render(request, 'store/edit_post.html', {'form': form, 'post': post})


@login_required
def delete_post(request, post_id):
    post = get_object_or_404(Post, id=post_id)

    # Защита: удалить может АВТОР или АДМИНИСТРАТОР
    if post.author == request.user or request.user.is_staff:
        post.delete()
        messages.success(request, "Пост успешно удален.")
    else:
        messages.error(request, "У вас нет прав для удаления этого поста.")

    return redirect('store:community')

@user_passes_test(is_store_admin, login_url='store:index')
def manager_report(request):
    """Генерация отчета о продажах с графиками"""

    # По умолчанию берем период за последние 30 дней
    today = timezone.now().date()
    default_start = today - datetime.timedelta(days=30)

    # Получаем даты из запроса или берем дефолтные
    start_date_str = request.GET.get('start_date', default_start.strftime('%Y-%m-%d'))
    end_date_str = request.GET.get('end_date', today.strftime('%Y-%m-%d'))

    # Преобразуем строки обратно в объекты дат
    start_date = datetime.datetime.strptime(start_date_str, '%Y-%m-%d').date()
    end_date = datetime.datetime.strptime(end_date_str, '%Y-%m-%d').date()

    # Берем ТОЛЬКО ВЫПОЛНЕННЫЕ заказы за этот период
    orders = Order.objects.filter(
        status='completed',
        created_at__gte=start_date,
        created_at__lt=end_date + datetime.timedelta(days=1)
    )

    # Подготавливаем структуру для графика: список дней с нулевой выручкой
    daily_stats = {}
    delta = end_date - start_date
    for i in range(delta.days + 1):
        day = start_date + datetime.timedelta(days=i)
        daily_stats[day.strftime('%d.%m')] = {'revenue': 0, 'count': 0}

    # Наполняем структуру реальными данными
    for order in orders:
        day_str = order.created_at.strftime('%d.%m')
        if day_str in daily_stats:
            daily_stats[day_str]['revenue'] += order.get_total_cost()
            daily_stats[day_str]['count'] += 1

    # Разбиваем словари на списки для передачи в JavaScript
    dates = list(daily_stats.keys())
    revenues = [stats['revenue'] for stats in daily_stats.values()]
    counts = [stats['count'] for stats in daily_stats.values()]

    context = {
        'start_date': start_date_str,
        'end_date': end_date_str,
        'total_revenue': sum(revenues),
        'total_orders': sum(counts),
        'dates': dates,
        'revenues': revenues,
        'counts': counts,
    }

    return render(request, 'store/manager_report.html', context)