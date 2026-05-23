from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import CustomUser
from .models import Order
from .models import Pet
from .models import Product

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
            'name', 'category', 'price', 'image', 'description',
            'target_species', 'target_age', 'min_weight', 'max_weight', 'target_activity'
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Название товара'}),
            'category': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Например: Корма, Игрушки'}),
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