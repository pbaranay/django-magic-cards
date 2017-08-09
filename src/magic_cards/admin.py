from django.contrib import admin

from .models import Card, Set, Printing, CardSupertype, CardType, CardSubtype, Artist

admin.site.register(Card)
admin.site.register(Set)
admin.site.register(Printing)
admin.site.register(CardSupertype)
admin.site.register(CardType)
admin.site.register(CardSubtype)
admin.site.register(Artist)
