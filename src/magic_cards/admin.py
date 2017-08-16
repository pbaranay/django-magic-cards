from django.contrib import admin

from .models import Card, Set, Printing, CardSupertype, CardType, CardSubtype, Artist


@admin.register(Card)
class CardAdmin(admin.ModelAdmin):
    search_fields = ['name']


@admin.register(Set)
class SetAdmin(admin.ModelAdmin):
    list_display = ['name', 'code']
    search_fields = ['name', 'code']


@admin.register(Printing)
class PrintingAdmin(admin.ModelAdmin):
    search_fields = ['card__name']
    list_filter = ['set']


@admin.register(Artist)
class ArtistAdmin(admin.ModelAdmin):
    search_fields = ['full_name']


@admin.register(CardSupertype)
class CardSupertypeAdmin(admin.ModelAdmin):
    search_fields = ['name']


@admin.register(CardType)
class CardTypeAdmin(admin.ModelAdmin):
    search_fields = ['name']


@admin.register(CardSubtype)
class CardSubtypeAdmin(admin.ModelAdmin):
    search_fields = ['name']
