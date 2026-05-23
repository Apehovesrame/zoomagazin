from django.shortcuts import render, get_object_or_404
from django.db.models import Q
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect
from .models import Product, OrderItem, Pet
from .forms import CustomUserCreationForm, UserUpdateForm, OrderCreateForm, PetForm
from django.contrib.auth import logout


def index(request):
    """Главная страница магазина (здесь будет форма помощника)"""
    return render(request, 'store/index.html')

def user_logout(request):
    """Выход пользователя из системы"""
    logout(request)
    return redirect('store:index')

def catalog(request):
    """Каталог товаров и логика алгоритма подбора корма"""
    # Изначально берем все товары из базы
    products = Product.objects.all()

    # Считываем параметры из формы Помощника (если пользователь её заполнил)
    species = request.GET.get('species')
    age = request.GET.get('age')
    weight = request.GET.get('weight')
    activity = request.GET.get('activity')

    # Если хотя бы один параметр передан — запускаем алгоритм подбора
    if species or age or weight or activity:
        # Ищем только в категории "Корма"
        products = products.filter(category='Корма')

        # 1. Фильтр по виду (совпадает ИЛИ товар универсальный)
        if species:
            products = products.filter(
                Q(target_species=species) | Q(target_species__isnull=True) | Q(target_species=''))

        # 2. Фильтр по возрасту
        if age:
            products = products.filter(Q(target_age=age) | Q(target_age__isnull=True) | Q(target_age=''))

        # 3. Фильтр по активности
        if activity:
            products = products.filter(
                Q(target_activity=activity) | Q(target_activity__isnull=True) | Q(target_activity=''))

        # 4. Фильтр по весу питомца
        if weight:
            try:
                w = float(weight.replace(',', '.'))
                # Подходит, если вес питомца больше минимального (или мин. не задан)
                # И меньше максимального (или макс. не задан)
                products = products.filter(
                    (Q(min_weight__isnull=True) | Q(min_weight__lte=w)) &
                    (Q(max_weight__isnull=True) | Q(max_weight__gte=w))
                )
            except ValueError:
                pass  # Если ввели не число, игнорируем вес

    context = {
        'products': products,
        'is_filtered': bool(species or age or weight or activity)
        # Флаг, чтобы показать сообщение "Вот что мы подобрали"
    }
    return render(request, 'store/catalog.html', context)


def product_detail(request, product_id):
    """Страница карточки конкретного товара"""
    product = get_object_or_404(Product, id=product_id)
    return render(request, 'store/product_detail.html', {'product': product})


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
def smart_catalog(request, pet_id):
    """Каталог, отфильтрованный под конкретного питомца (Умный подбор)"""
    # Ищем питомца, убеждаясь, что он принадлежит именно этому пользователю
    pet = get_object_or_404(Pet, id=pet_id, user=request.user)

    # Изначально берем все товары из категории "Корма"
    products = Product.objects.filter(category='Корма')

    # Алгоритм подбора: ищем товары, где параметры совпадают или не указаны (универсальные)
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

    context = {
        'products': products,
        'active_pet': pet,  # Передаем питомца, чтобы написать "Корм для Барсика"
        'is_filtered': True  # Используем твой флаг для красивого отображения
    }
    return render(request, 'store/catalog.html', context)