from datetime import date

from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.validators import MinValueValidator, MaxValueValidator


# 1. ПОЛЬЗОВАТЕЛИ (Расширяем стандартную модель Django)
class CustomUser(AbstractUser):
    ROLE_CHOICES = (
        ('client', 'Клиент'),
        ('admin', 'Администратор'),
    )
    role = models.CharField('Роль', max_length=20, choices=ROLE_CHOICES, default='client')

    avatar = models.ImageField('Аватар', upload_to='users_avatars/', blank=True, null=True)

    class Meta:
        verbose_name = 'Пользователь'
        verbose_name_plural = 'Пользователи'

    def __str__(self):
        return self.username


# 2. ПИТОМЦЫ
class Pet(models.Model):
    SPECIES_CHOICES = (('Кошка', 'Кошка'), ('Собака', 'Собака'))
    AGE_CHOICES = (('Щенок/Котенок', 'Щенок/Котенок'), ('Взрослый', 'Взрослый'), ('Пожилой', 'Пожилой'))
    ACTIVITY_CHOICES = (('Низкая', 'Низкая'), ('Средняя', 'Средняя'), ('Высокая', 'Высокая'))

    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='pets', verbose_name='Владелец')
    name = models.CharField('Кличка', max_length=100)
    species = models.CharField('Вид', max_length=50, choices=SPECIES_CHOICES)

    # ВОТ ЭТА СТРОКА ОБЯЗАТЕЛЬНО ДОЛЖНА БЫТЬ:
    breed = models.CharField('Порода', max_length=100, default='Без породы', blank=True)

    age_group = models.CharField('Возрастная группа', max_length=50, choices=AGE_CHOICES)
    weight = models.DecimalField('Вес (кг)', max_digits=5, decimal_places=2)
    activity_level = models.CharField('Активность', max_length=50, choices=ACTIVITY_CHOICES)

    class Meta:
        verbose_name = 'Питомец'
        verbose_name_plural = 'Питомцы'

    image = models.ImageField('Фото питомца', upload_to='pets_images/', blank=True, null=True)

    def __str__(self):
        return f"{self.name} ({self.species}, {self.breed})"


# 3. ТОВАРЫ
class Product(models.Model):
    CATEGORY_CHOICES = (('Корма', 'Корма'), ('Игрушки', 'Игрушки'), ('Аксессуары', 'Аксессуары'))

    name = models.CharField('Название', max_length=200)
    category = models.CharField('Категория', max_length=50, choices=CATEGORY_CHOICES)
    price = models.DecimalField('Цена', max_digits=10, decimal_places=2)
    description = models.TextField('Описание', blank=True, null=True)

    brand = models.CharField(max_length=100, blank=True, null=True, verbose_name="Бренд")

    image = models.ImageField('Фото товара', upload_to='products_images/', blank=True, null=True)

    # Поля для алгоритма подбора (актуально только для кормов)
    target_species = models.CharField('Целевой вид', max_length=50, choices=Pet.SPECIES_CHOICES, blank=True, null=True)
    target_age = models.CharField('Целевой возраст', max_length=50, choices=Pet.AGE_CHOICES, blank=True, null=True)
    min_weight = models.DecimalField('Мин. вес (кг)', max_digits=5, decimal_places=2, blank=True, null=True)
    max_weight = models.DecimalField('Макс. вес (кг)', max_digits=5, decimal_places=2, blank=True, null=True)
    target_activity = models.CharField('Целевая активность', max_length=50, choices=Pet.ACTIVITY_CHOICES, blank=True,
                                       null=True)

    class Meta:
        verbose_name = 'Товар'
        verbose_name_plural = 'Товары'

    def __str__(self):
        return self.name


# 4. ЗАКАЗЫ
class Order(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True, related_name='orders', verbose_name='Клиент')

    # Поля, которые мы используем в форме:
    first_name = models.CharField('Имя', max_length=50)
    last_name = models.CharField('Фамилия', max_length=50)
    email = models.EmailField('Email')
    phone = models.CharField('Телефон', max_length=20)
    address = models.CharField('Адрес доставки', max_length=250)
    city = models.CharField('Город', max_length=100)

    created_at = models.DateTimeField('Дата создания', auto_now_add=True)
    paid = models.BooleanField('Оплачено', default=False)

    # Если хочешь оставить статусы:
    STATUS_CHOICES = (
        ('Новый', 'Новый'),
        ('В обработке', 'В обработке'),
        ('Выполнен', 'Выполнен'),
    )
    status = models.CharField('Статус', max_length=50, choices=STATUS_CHOICES, default='Новый')

    class Meta:
        verbose_name = 'Заказ'
        verbose_name_plural = 'Заказы'

    def __str__(self):
        return f"Заказ №{self.id} ({self.first_name})"

    def get_total_cost(self):
        return sum(item.get_cost() for item in self.items.all())


# 5. ПОЗИЦИИ ЗАКАЗА (Связь M:N)
class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items', verbose_name='Заказ')
    product = models.ForeignKey(Product, on_delete=models.RESTRICT, verbose_name='Товар')
    quantity = models.PositiveIntegerField('Количество', default=1)
    price_at_purchase = models.DecimalField('Цена за шт. при покупке', max_digits=10, decimal_places=2)

    class Meta:
        verbose_name = 'Позиция заказа'
        verbose_name_plural = 'Позиции заказа'

    def __str__(self):
        return f"{self.product.name} ({self.quantity} шт.)"

    def get_cost(self):
        return self.price_at_purchase * self.quantity


# 1. Модель Хештегов
class Tag(models.Model):
    name = models.CharField('Хештег', max_length=50, unique=True)

    class Meta:
        verbose_name = 'Хештег'
        verbose_name_plural = 'Хештеги'

    def __str__(self):
        return f"#{self.name}"


# 2. Модель Поста (Лента новостей и фото)
class Post(models.Model):
    author = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='posts', verbose_name='Автор')

    # Необязательная, но крутая фишка: привязка поста к конкретному питомцу
    pet = models.ForeignKey(Pet, on_delete=models.SET_NULL, null=True, blank=True, related_name='posts',
                            verbose_name='Питомец (опционально)')

    image = models.ImageField('Фотография', upload_to='community/', blank=True, null=True)
    text = models.TextField('Текст поста', max_length=2000)

    # Связь "Многие-ко-Многим" для лайков и тегов
    tags = models.ManyToManyField(Tag, related_name='posts', blank=True, verbose_name='Хештеги')
    likes = models.ManyToManyField(CustomUser, related_name='liked_posts', blank=True, verbose_name='Лайки')

    created_at = models.DateTimeField('Дата публикации', auto_now_add=True)

    class Meta:
        verbose_name = 'Пост'
        verbose_name_plural = 'Посты'
        ordering = ['-created_at']  # Новые посты всегда будут сверху

    def __str__(self):
        return f"Пост от {self.author.username} ({self.created_at | date:'d.m.Y'})"

    # Метод для быстрого подсчета лайков в шаблоне
    def total_likes(self):
        return self.likes.count()


# 3. Модель Комментария
class Comment(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='comments', verbose_name='Пост')
    author = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='user_comments', verbose_name='Автор')
    text = models.TextField('Комментарий', max_length=500)
    created_at = models.DateTimeField('Дата написания', auto_now_add=True)

    class Meta:
        verbose_name = 'Комментарий'
        verbose_name_plural = 'Комментарии'
        ordering = ['created_at']  # Старые комментарии сверху, новые снизу

    def __str__(self):
        return f"Комментарий от {self.author.username} к посту №{self.post.id}"

class Review(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='reviews', verbose_name='Товар')
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, verbose_name='Покупатель')
    rating = models.PositiveSmallIntegerField('Оценка', validators=[MinValueValidator(1), MaxValueValidator(5)])
    text = models.TextField('Отзыв', max_length=1000)
    created_at = models.DateTimeField('Дата создания', auto_now_add=True)

    class Meta:
        verbose_name = 'Отзыв'
        verbose_name_plural = 'Отзывы'
        ordering = ['-created_at'] # Новые отзывы всегда сверху

    def __str__(self):
        return f"Отзыв от {self.user.username} на {self.product.name} ({self.rating} звезд)"


class ImageGallery(models.Model):
    # Эта модель может быть связана с чем угодно
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='images', null=True, blank=True)
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='images', null=True, blank=True)
    pet = models.ForeignKey(Pet, on_delete=models.CASCADE, related_name='images', null=True, blank=True)

    image = models.ImageField('Фото', upload_to='gallery/')
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Фото из галереи'
        verbose_name_plural = 'Галерея'