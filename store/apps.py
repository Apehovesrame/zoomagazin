from django.apps import AppConfig

class StoreConfig(AppConfig):  # Название класса у тебя может быть другим (например, UsersConfig)
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'store'  # Твое имя приложения

    # ДОБАВЛЯЕМ ЭТОТ МЕТОД:
    def ready(self):
        import store.signals  # Вместо 'store' укажи имя папки твоего приложения