from __future__ import unicode_literals

import six
from django.test import TestCase

from magic_cards.models import Artist, Card, Printing, Set
from magic_cards.utils.import_cards import import_cards


class UnicodeTests(TestCase):
    @staticmethod
    def get_text_and_bytes(obj):
        if six.PY2:
            txt = unicode(obj)
            byt = str(obj)
        else:
            txt = str(obj)
            byt = bytes(str(obj), 'utf-8')
        return txt, byt

    def test_name_mixin(self):
        seance = Card.objects.create(name="S\xe9ance")

        txt, byt = self.get_text_and_bytes(seance)
        self.assertEqual(txt, "S\xe9ance")
        self.assertEqual(byt, b"S\xc3\xa9ance")

    def test_printing(self):
        dka = Set.objects.create(name="Dark Ascension", code="DKA")
        seance = Card.objects.create(name="S\xe9ance")
        artist = Artist.objects.create(full_name="David Rapoza")
        printing = Printing.objects.create(set=dka, card=seance, artist=artist)

        txt, byt = self.get_text_and_bytes(printing)
        self.assertEqual(txt, "S\xe9ance (DKA)")
        self.assertEqual(byt, b"S\xc3\xa9ance (DKA)")

    def test_artist(self):
        piotr = Artist.objects.create(full_name="Piotr Jab\u0142o\u0144ski")

        txt, byt = self.get_text_and_bytes(piotr)
        self.assertEqual(txt, "Piotr Jab\u0142o\u0144ski")
        self.assertEqual(byt, b"Piotr Jab\xc5\x82o\xc5\x84ski")


class ImportScriptTests(TestCase):
    def test_long_card_name(self):
        """
        The longest card name can be successfully imported and stored fully in the database.
        """
        import_cards(["UNH"])

        longest_name = "Our Market Research Shows That Players Like Really Long Card Names " \
                       "So We Made this Card to Have the Absolute Longest Card Name Ever Elemental"
        longest_name_card = Card.objects.get(name=longest_name)
        self.assertEqual(longest_name_card.name, longest_name)
        # SQLite does not actually enforce the length of a VARCHAR, but Django will validate
        # if we call full_clean.
        longest_name_card.full_clean()

    def test_planeswalker_loyalty(self):
        import_cards(["AVR"])

        tamiyo = Card.objects.get(name="Tamiyo, the Moon Sage")
        self.assertEqual(tamiyo.loyalty, 4)

        tracker = Card.objects.get(name="Ulvenwald Tracker")
        self.assertIsNone(tracker.loyalty)
