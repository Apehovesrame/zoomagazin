from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import CustomUser
from .models import Order
from .models import Product, OrderItem, Pet, Post, Comment

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
                'placeholder': 'Что нового у вашего пушистого друга? Напишите текст и добавьте #хештеги...'
            }),
            'image': forms.FileInput(attrs={'class': 'form-control'}),
            'pet': forms.Select(attrs={'class': 'form-select'})
        }

    # Маленькая, но важная хитрость: переопределяем инициализацию формы,
    # чтобы в выпадающем списке питомцев пользователь видел ТОЛЬКО СВОИХ животных, а не чужих.
    def __init__(self, *args, **kwargs):
        # Вытаскиваем пользователя из аргументов (мы передадим его из views.py)
        user = kwargs.pop('user', None)
        super(PostForm, self).__init__(*args, **kwargs)
        if user:
            # Фильтруем список питомцев
            self.fields['pet'].queryset = Pet.objects.filter(user=user)
            self.fields['pet'].empty_label = "Написать от своего имени (без привязки к питомцу)"

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