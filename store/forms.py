from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import CustomUser
from .models import Order
from .models import Product, OrderItem, Pet, Post, Comment, Review

class CustomUserCreationForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = CustomUser
        fields = ('username', 'email', 'first_name', 'last_name')

class UserUpdateForm(forms.ModelForm):
    class Meta:
        model = CustomUser
        fields = ('username', 'email', 'first_name', 'last_name')
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
        }

class OrderCreateForm(forms.ModelForm):
    class Meta:
        model = Order
        fields = ['first_name', 'last_name', 'email', 'phone', 'address', 'city']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Иван'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Иванов'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'example@mail.ru'}),
            'address': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'ул. Пушкина, д. 10, кв. 5'}),
            'city': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Москва'}),
        }

class PetForm(forms.ModelForm):
    class Meta:
        model = Pet
        fields = ['name', 'species', 'breed', 'image', 'age_group', 'weight', 'activity_level']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Кличка'}),
            'species': forms.Select(attrs={'class': 'form-select'}),
            'breed': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Например: Корги, Мейн-кун или Без породы'}),
            'image': forms.FileInput(attrs={'class': 'form-control'}),
            'age_group': forms.Select(attrs={'class': 'form-select'}),
            'weight': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.1'}),
            'activity_level': forms.Select(attrs={'class': 'form-select'}),
        }

class UserUpdateForm(forms.ModelForm):
    class Meta:
        model = CustomUser
        fields = ['first_name', 'last_name', 'email', 'avatar']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Имя'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Фамилия'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Email'}),
            'avatar': forms.FileInput(attrs={'class': 'form-control'}),
        }


SPECIES_CHOICES = [
    ('', 'Не задано (для всех)'),
    ('Кошка', 'Кошка'),
    ('Собака', 'Собака')
]

AGE_CHOICES = [
    ('', 'Не задано (для всех)'),
    ('Щенок/Котенок', 'Щенок/Котенок'),
    ('Взрослый', 'Взрослый'),
    ('Пожилой', 'Пожилой')
]

ACTIVITY_CHOICES = [
    ('', 'Не задано (для всех)'),
    ('Низкая', 'Низкая'),
    ('Средняя', 'Средняя'),
    ('Высокая', 'Высокая')
]


class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = [
            'name', 'category', 'price', 'image', 'description', 'stock', 'brand',
            'target_species', 'target_age', 'min_weight', 'max_weight', 'target_activity'
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Название товара'}),
            'category': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Начните вводить...',
                'list': 'category-list' # Указываем ID списка подсказок
            }),
            'price': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'image': forms.FileInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Описание товара'}),

            # 2. Теперь класс Meta видит эти списки без проблем
            'target_species': forms.Select(choices=SPECIES_CHOICES, attrs={'class': 'form-select'}),
            'target_age': forms.Select(choices=AGE_CHOICES, attrs={'class': 'form-select'}),
            'min_weight': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.1', 'placeholder': 'Мин. вес'}),
            'max_weight': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.1', 'placeholder': 'Макс. вес'}),
            'target_activity': forms.Select(choices=ACTIVITY_CHOICES, attrs={'class': 'form-select'}),
        }

class PostForm(forms.ModelForm):
    class Meta:
        model = Post
        fields = ['image', 'text', 'pet']
        widgets = {
            'text': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                # Меняем плейсхолдер на более универсальный:
                'placeholder': 'Напишите обзор на товар, задайте вопрос или поделитесь фото... Не забудьте #хештеги!'
            }),
            'image': forms.FileInput(attrs={'class': 'form-control'}),
            'pet': forms.Select(attrs={'class': 'form-select'})
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super(PostForm, self).__init__(*args, **kwargs)
        if user:
            self.fields['pet'].queryset = Pet.objects.filter(user=user)
            # Меняем текст пустого выбора, чтобы было понятно, что питомец не обязателен
            self.fields['pet'].empty_label = "Обычный пост (без питомца)"

class CommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        fields = ['text']
        widgets = {
            'text': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'placeholder': 'Написать комментарий...'
            }),
        }

class ReviewForm(forms.ModelForm):
    class Meta:
        model = Review
        fields = ['rating', 'text']
        widgets = {
            # Делаем красивый выпадающий список со звездами
            'rating': forms.Select(choices=[
                (5, '5 ⭐⭐⭐⭐⭐ - Отлично'),
                (4, '4 ⭐⭐⭐⭐ - Хорошо'),
                (3, '3 ⭐⭐⭐ - Нормально'),
                (2, '2 ⭐⭐ - Плохо'),
                (1, '1 ⭐ - Ужасно')
            ], attrs={'class': 'form-select mb-3'}),
            'text': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Поделитесь впечатлениями о товаре. Что понравилось, а что нет?'
            }),
        }