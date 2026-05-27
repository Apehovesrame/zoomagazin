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


def index(request):
    """Главная страница магазина"""
    # Берем 3 последних добавленных товара для блока "Новинки"
    latest_products = Product.objects.all().order_by('-id')[:3]
    return render(request, 'store/index.html', {'latest_products': latest_products})

def user_logout(request):
    """Выход пользователя из системы"""
    logout(request)
    return redirect('store:index')


def catalog(request):
    """Каталог товаров с поиском, категориями, брендами, сортировкой и умным подбором"""

    # 1. Сбор базовых параметров из GET-запроса
    query = request.GET.get('q', '')
    selected_category = request.GET.get('category', '')
    selected_brand = request.GET.get('brand', '')  # НОВОЕ: бренд
    sort_by = request.GET.get('sort', 'newest')  # НОВОЕ: сортировка

    # Параметры умного подбора
    species = request.GET.get('species')
    age = request.GET.get('age')
    weight = request.GET.get('weight')
    activity = request.GET.get('activity')

    # 2. Базовый QuerySet с подсчетом рейтинга
    products = Product.objects.annotate(
        avg_rating=Avg('reviews__rating'),
        review_count=Count('reviews', distinct=True)
    )

    # 3. Применяем текстовый поиск
    if query:
        products = products.filter(Q(name__icontains=query))

    # 4. Применяем фильтр по категориям и брендам
    if selected_category:
        products = products.filter(category=selected_category)
    if selected_brand:  # НОВОЕ: фильтрация по бренду
        products = products.filter(brand=selected_brand)

    # 5. Алгоритм Умного подбора (твоя логика без изменений)
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

    # 6. НОВОЕ: Применяем сортировку контента
    if sort_by == 'price_asc':
        products = products.order_by('price')
    elif sort_by == 'price_desc':
        products = products.order_by('-price')
    elif sort_by == 'rating':
        # Сортируем по рейтингу. Сначала высокие, товары без рейтинга (NULL) — в самый конец
        products = products.order_by(F('avg_rating').desc(nulls_last=True), '-review_count')
    else:  # newest (по умолчанию)
        products = products.order_by('-id')

    # 7. Списки уникальных категорий и брендов для селектов в шаблоне
    categories = Product.objects.exclude(category__isnull=True).exclude(category__exact='').values_list('category',
                                                                                                        flat=True).distinct()
    brands = Product.objects.exclude(brand__isnull=True).exclude(brand__exact='').values_list('brand',
                                                                                              flat=True).distinct()  # НОВОЕ

    # 8. Пагинация
    paginator = Paginator(products, 9)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'query': query,
        'categories': categories,
        'brands': brands,  # НОВОЕ
        'selected_category': selected_category,
        'selected_brand': selected_brand,  # НОВОЕ
        'current_sort': sort_by,  # НОВОЕ
        'is_filtered': bool(species or age or weight or activity)
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
            rating_stats.append({
                'star': star,
                'count': count,
                'percent': percent
            })

    if request.method == 'POST' and request.user.is_authenticated:
        form = ReviewForm(request.POST)
        if form.is_valid():
            review = form.save(commit=False)
            review.product = product
            review.user = request.user
            review.save()
            messages.success(request, 'Спасибо за ваш отзыв!')
            return redirect('store:product_detail', product_id=product.id)
    else:
        form = ReviewForm()

    return render(request, 'store/product_detail.html', {
        'product': product,
        'reviews': reviews,
        'avg_rating': avg_rating,
        'total_reviews_count': total_reviews_count,
        'current_filter': review_filter,
        'rating_stats': rating_stats,
        'form': form
    })


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

def add_to_cart(request, product_id):
    """Добавление товара в корзину (с учетом указанного количества)"""
    cart = request.session.get('cart', {})
    product_id_str = str(product_id)

    # Если данные пришли из формы (POST), берем количество. Иначе по умолчанию 1.
    if request.method == 'POST':
        quantity = int(request.POST.get('quantity', 1))
    else:
        quantity = 1

    if product_id_str in cart:
        cart[product_id_str] += quantity
    else:
        cart[product_id_str] = quantity

    request.session['cart'] = cart
    return redirect('store:cart')


def update_cart(request, product_id):
    """Обновление точного количества товара прямо из корзины"""
    if request.method == 'POST':
        cart = request.session.get('cart', {})
        product_id_str = str(product_id)
        quantity = int(request.POST.get('quantity', 1))

        if quantity > 0:
            cart[product_id_str] = quantity  # Устанавливаем новое значение
        else:
            if product_id_str in cart:
                del cart[product_id_str]  # Если ввели 0, удаляем товар

        request.session['cart'] = cart

    return redirect('store:cart')

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



def order_create(request):
    cart = request.session.get('cart', {})
    if not cart:
        return redirect('store:catalog')

    if request.method == 'POST':
        form = OrderCreateForm(request.POST)
        if form.is_valid():
            # Создаем объект заказа, но пока не сохраняем в БД (commit=False)
            order = form.save(commit=False)
            if request.user.is_authenticated:
                order.user = request.user
            order.save()

            # Переносим товары из корзины в OrderItem
            for p_id, quantity in cart.items():
                product = get_object_or_404(Product, id=int(p_id))
                OrderItem.objects.create(
                    order=order,
                    product=product,
                    price_at_purchase=product.price,
                    quantity=quantity
                )

            # Очищаем корзину после успешного заказа
            request.session['cart'] = {}

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
            }
        form = OrderCreateForm(initial=initial_data)

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
def edit_pet(request, pet_id):
    # Достаем питомца, проверяя, что он принадлежит текущему пользователю
    pet = get_object_or_404(Pet, id=pet_id, user=request.user)

    if request.method == 'POST':
        # instance=pet говорит Django, что нужно обновить существующую запись, а не создавать новую
        form = PetForm(request.POST, request.FILES, instance=pet)
        if form.is_valid():
            form.save()
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


@user_passes_test(is_store_admin, login_url='store:index')
def manager_orders(request):
    """Страница управления заказами для администратора"""
    orders = Order.objects.all().order_by('-created_at')
    status_choices = Order.STATUS_CHOICES

    return render(request, 'store/manager_orders.html', {
        'orders': orders,
        'status_choices': status_choices
    })


@require_POST
@user_passes_test(is_store_admin, login_url='store:index')
def change_order_status(request, order_id):
    """Быстрое изменение статуса заказа менеджером"""
    order = get_object_or_404(Order, id=order_id)
    new_status = request.POST.get('status')

    valid_statuses = [choice[0] for choice in Order.STATUS_CHOICES]
    if new_status in valid_statuses:
        order.status = new_status
        order.save()
        messages.success(request, f'Статус заказа №{order.id} успешно изменен на «{new_status}»')
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
            new_post.save()

            # Логика загрузки нескольких фото
            files = request.FILES.getlist('images_input')
            for f in files:
                ImageGallery.objects.create(post=new_post, image=f)

            # АВТОМАТИЧЕСКИЙ ПАРСИНГ ХЕШТЕГОВ
            hashtags = re.findall(r'#(\w+)', new_post.text)
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

    # Защита: редактировать может ТОЛЬКО автор
    if post.author != request.user:
        messages.error(request, "У вас нет прав для редактирования этого поста.")
        return redirect('store:community')

    if request.method == 'POST':
        form = PostForm(request.POST, instance=post)
        if form.is_valid():
            form.save()

            # Сохранение новых фото в галерею
            files = request.FILES.getlist('images_input')
            for f in files:
                ImageGallery.objects.create(post=post, image=f)

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