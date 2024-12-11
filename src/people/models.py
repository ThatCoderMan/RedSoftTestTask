from django.core.validators import EmailValidator
from django.db import models
from django.db.models import Index
from django.db.models.functions import Lower

NAME_LENGTH = 100
NATIONALITY_LENGTH = 50


class Person(models.Model):
    GENDER_CHOICES = (
        ('male', 'Male'),
        ('female', 'Female'),
    )

    last_name = models.CharField(
        max_length=NAME_LENGTH, null=False, blank=False
    )
    first_name = models.CharField(
        max_length=NAME_LENGTH, null=False, blank=False
    )
    middle_name = models.CharField(
        max_length=NAME_LENGTH, null=True, blank=True
    )
    gender = models.CharField(
        max_length=6,
        choices=GENDER_CHOICES,
        null=True,
    )
    age = models.PositiveIntegerField(null=True)
    nationality = models.CharField(max_length=NATIONALITY_LENGTH, null=True)
    friends = models.ManyToManyField('self', symmetrical=False, blank=True)

    def __str__(self):
        return f'{self.first_name} {self.middle_name} {self.last_name}'

    class Meta:
        unique_together = ('first_name', 'middle_name', 'last_name')
        indexes = [
            Index(Lower('last_name'), name='person_last_name_lower_idx'),
        ]

    @property
    def full_name(self):
        return ' '.join(
            filter(None, [self.last_name, self.first_name, self.middle_name])
        )


class Email(models.Model):
    person = models.ForeignKey(
        Person, related_name='emails', on_delete=models.CASCADE
    )
    email = models.EmailField(validators=[EmailValidator()], unique=True)

    def __str__(self):
        return f'{self.email} ({self.person})'
