from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Person
from .tasks import update_person_info


@receiver(post_save, sender=Person)
def person_created_or_updated(sender, instance, created, **kwargs):
    if created:
        update_person_info.delay(instance.id)
