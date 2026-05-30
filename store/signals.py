from django.db.models.signals import pre_save
from django.dispatch import receiver
from .models import Order

@receiver(pre_save, sender=Order)
def restore_stock_on_cancellation(sender, instance, **kwargs):
    # Если это новый заказ (еще нет в базе), то отменять нечего, выходим
    if not instance.pk:
        return

    try:
        # Берем старую версию заказа из базы данных до сохранения
        old_order = Order.objects.get(pk=instance.pk)
    except Order.DoesNotExist:
        return

    # ПРОВЕРКА: Если статус изменился на "Отменен" (cancelled)
    if old_order.status != 'cancelled' and instance.status == 'cancelled':
        # Проходим по всем позициям в этом заказе
        for item in instance.items.all():  # Убедись, что related_name='items' у модели OrderItem
            product = item.product
            # Возвращаем количество купленного товара обратно на склад
            product.stock += item.quantity
            product.save()