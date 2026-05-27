import re
from django import template
from django.utils.safestring import mark_safe

register = template.Library()

@register.filter(name='hide_hashtags')
def hide_hashtags(text):
    """Вырезает хештеги из текста только для отображения в шаблоне"""
    if not text:
        return ""
    # Находим все хештеги и заменяем их на пустую строку
    clean_text = re.sub(r'#[а-яА-ЯёЁa-zA-Z0-9_]+', '', text)
    # Убираем лишние пробелы и возвращаем
    return clean_text.strip()