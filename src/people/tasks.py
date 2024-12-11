from celery import shared_task
from django.apps import apps
from django.db import transaction

from .services.external_api import NameInfoClient


@shared_task
def update_person_info(person_id):
    Person = apps.get_model('people', 'Person')
    person = Person.objects.get(id=person_id)
    person_name = person.full_name

    service = NameInfoClient()
    age = service.get_age(person_name)
    gender = service.get_gender(person_name)
    nationality = service.get_nationality(person_name)
    with transaction.atomic():
        person_locked = Person.objects.select_for_update().get(id=person_id)
        person_locked.age = age
        person_locked.gender = gender
        person_locked.nationality = nationality
        person_locked.save()
