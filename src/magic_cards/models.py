import random

from django.db import models
from django_light_enums import enum


class NameMixin(object):
    def __str__(self):
        return self.name


class Card(NameMixin, models.Model):
    name = models.CharField(max_length=255, unique=True)
    mana_cost = models.CharField(max_length=63, blank=True)

    supertypes = models.ManyToManyField('CardSupertype')
    types = models.ManyToManyField('CardType')
    subtypes = models.ManyToManyField('CardSubtype')

    text = models.TextField(blank=True)
    power = models.CharField(max_length=7, blank=True)
    toughness = models.CharField(max_length=7, blank=True)


class Set(NameMixin, models.Model):
    name = models.CharField(max_length=63, unique=True)
    code = models.CharField(max_length=8, unique=True)


class PrintingQuerySet(models.QuerySet):
    def random(self, num):
        num = int(num)
        printing_ids = set(self.values_list('id', flat=True))
        random_ids = random.sample(printing_ids, num)
        return self.filter(id__in=random_ids)


class Printing(models.Model):
    class Rarity(enum.Enum):
        MYTHIC = 10
        RARE = 20
        UNCOMMON = 30
        COMMON = 40
        SPECIAL = 50
        BASIC_LAND = 60

    objects = PrintingQuerySet.as_manager()

    card = models.ForeignKey('Card', related_name='printings')
    set = models.ForeignKey('Set', related_name='printings')
    rarity = enum.EnumField(Rarity)
    flavor_text = models.TextField(blank=True)
    artist = models.ForeignKey('Artist', related_name='printings')
    number = models.CharField(max_length=7, blank=True)
    multiverse_id = models.PositiveIntegerField(blank=True, null=True)

    @property
    def image_url(self):
        if self.multiverse_id:
            return 'http://gatherer.wizards.com/Handlers/Image.ashx?multiverseid={}&type=card'.format(
                self.multiverse_id)

    def __str__(self):
        return '{} ({})'.format(self.card, self.set.code)


class CardSupertype(NameMixin, models.Model):
    name = models.CharField(max_length=32, unique=True)


class CardType(NameMixin, models.Model):
    name = models.CharField(max_length=32, unique=True)


class CardSubtype(NameMixin, models.Model):
    name = models.CharField(max_length=32, unique=True)


class Artist(models.Model):
    full_name = models.CharField(max_length=127, unique=True)

    def __str__(self):
        return self.full_name
