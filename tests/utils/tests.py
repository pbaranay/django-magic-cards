import copy
import json
import os
import unittest

from django.core.management import call_command
from django.db.models import Count
from django.test import TestCase
from django.utils.six import StringIO

from magic_cards.models import Card, CardSubtype, Printing, Set
from magic_cards.utils.import_cards import import_cards, parse_data


class ImportTestBase:

    def check_common_set_constraints(self):
        """
        Checks conditions that are true for most modern sets.
        """
        # Only the basic lands should have multiple printings.
        multiple_printings = Card.objects.annotate(count=Count('printings')).filter(count__gte=2)
        basic_lands = {'Forest', 'Island', 'Mountain', 'Plains', 'Swamp'}
        if multiple_printings:
            self.assertQuerysetEqual(multiple_printings, basic_lands, ordered=False, transform=lambda x: x.name)

        # Every printing has a rarity.
        self.assertFalse(Printing.objects.filter(rarity__isnull=True))
        # No cards of special rarity appear.
        self.assertFalse(Printing.objects.filter(rarity=Printing.Rarity.SPECIAL))
        # Basic lands are marked appropriately.
        for printing in Printing.objects.filter(rarity=Printing.Rarity.BASIC_LAND):
            self.assertIn(printing.card.name, basic_lands)

        # Some printings have flavor text.
        self.assertTrue(Printing.objects.exclude(flavor_text='').exists())


class ImportScriptTests(ImportTestBase, TestCase):

    @unittest.skipIf(
        all([
            os.environ.get("TRAVIS", False),
            any([
                os.environ.get("DJANGO", None) != '1.11',
                os.environ.get("TRAVIS_PYTHON_VERSION", None) != '3.6',
            ]),
        ]),
        "On Travis, only runs on Django 1.11 under Python 3.6")
    def test_import_all_cards(self):
        import_cards()

        self.assertEqual(Set.objects.count(), 214)
        self.assertEqual(Card.objects.count(), 17733)
        self.assertEqual(Printing.objects.count(), 34468)

    def test_import_single_set(self):
        import_cards(["SOM"])

        self.assertEqual(Set.objects.count(), 1)
        scars = Set.objects.first()
        self.assertEqual(scars.name, "Scars of Mirrodin")
        self.assertEqual(scars.code, "SOM")

        self.assertEqual(Card.objects.count(), 234)
        #   234 Distinctly-named cards

        self.assertEqual(Printing.objects.count(), 249)
        #   234 Number of cards
        # +  15 Each of the 5 basic lands has 3 additional arts

        self.check_common_set_constraints()

    def test_import_single_set_with_split_cards(self):
        import_cards(["AKH"])

        self.assertEqual(Set.objects.count(), 1)
        amonkhet = Set.objects.first()
        self.assertEqual(amonkhet.name, "Amonkhet")
        self.assertEqual(amonkhet.code, "AKH")

        self.assertEqual(Card.objects.count(), 287)
        #   239 Distinctly named non-split cards
        # +  15 Top halves of split cards
        # +  15 Bottom halves of split cards
        # +   8 Cards from Planeswalker decks
        # +  10 Dual lands

        self.assertEqual(Printing.objects.count(), 302)
        #   287 Number of cards
        # +  15 Each of the 5 basic lands has 3 additional arts

        self.check_common_set_constraints()

    def test_import_is_idempotent(self):
        """
        Importing the same set additional times has no effect (assuming the same data)
        """
        import_cards(["AKH"])
        import_cards(["AKH"])

        self.assertEqual(Set.objects.count(), 1)
        self.assertEqual(Card.objects.count(), 287)
        self.assertEqual(Printing.objects.count(), 302)

    def test_reimport_sets_without_multiverse_ids(self):
        """
        Even if a set does not have proper multiverse_ids in MTGJSON, importing it
        multiple times has no effect and does not crash.
        """
        import_cards(["CED"])
        card_count = Card.objects.count()
        printing_count = Printing.objects.count()

        import_cards(["CED"])

        self.assertEqual(Set.objects.count(), 1)
        self.assertEqual(Card.objects.count(), card_count)
        self.assertEqual(Printing.objects.count(), printing_count)

    def test_import_betrayers(self):
        """
        Data integrity issues from a bug in MTGJSON are cleaned up by the import process.
        """
        import_cards(["BOK"])

        self.assertEqual(Set.objects.count(), 1)
        betrayers = Set.objects.first()
        self.assertEqual(betrayers.name, "Betrayers of Kamigawa")
        self.assertEqual(betrayers.code, "BOK")

        self.assertEqual(Card.objects.count(), 170)
        #   170 Distinctly-named cards

        self.assertEqual(Printing.objects.count(), 170)
        #   170 Number of cards
        # +   0 Basic lands

        self.check_common_set_constraints()


class ImportScriptUpdateTests(TestCase):

    FIXTURES_DIR = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'fixtures')

    def test_update_text(self):
        with open(os.path.join(self.FIXTURES_DIR, 'eyes_in_the_skies.json')) as f:
            final_data = json.load(f)

        original_text = final_data['RTR']['cards'][0]['originalText']
        final_text = final_data['RTR']['cards'][0]['text']

        # Copy the data and munge it into its original state.
        original_data = copy.deepcopy(final_data)
        original_data['RTR']['cards'][0]['text'] = original_text

        # Import the original data.
        parse_data(original_data, ['RTR'])
        eyes_in_the_skies = Card.objects.first()
        self.assertEqual(eyes_in_the_skies.text, original_text)

        # Import the final, updated data.
        parse_data(final_data, ['RTR'])
        eyes_in_the_skies.refresh_from_db()
        self.assertEqual(eyes_in_the_skies.text, final_text)

    def test_update_types(self):
        with open(os.path.join(self.FIXTURES_DIR, 'jackal_pup.json')) as f:
            final_data = json.load(f)

        # Copy the data and munge the types.
        original_data = copy.deepcopy(final_data)
        original_subtype = 'Hound'
        original_data['TMP']['cards'][0]['subtypes'] = [original_subtype]

        # Import the original data.
        parse_data(original_data, ['TMP'])
        jackal_pup = Card.objects.first()
        self.assertEqual(jackal_pup.subtypes.count(), 1)
        self.assertEqual(jackal_pup.subtypes.first().name, original_subtype)

        # Import the final, updated data.
        parse_data(final_data, ['TMP'])
        jackal_pup.refresh_from_db()
        self.assertEqual(jackal_pup.subtypes.count(), 1)
        self.assertEqual(jackal_pup.subtypes.first().name, 'Jackal')
        # The Hound subtype has been deleted.
        self.assertFalse(CardSubtype.objects.filter(name=original_subtype).exists())

    def test_update_loyalty(self):
        """
        Simulates the upgrade process from version 0.2 to version 0.4.
        """
        with open(os.path.join(self.FIXTURES_DIR, 'vraska_the_unseen.json')) as f:
            final_data = json.load(f)

        # Copy the data and munge it to remove the loyalty.
        original_data = copy.deepcopy(final_data)
        del original_data['RTR']['cards'][0]['loyalty']

        # Import the original data.
        parse_data(original_data, ['RTR'])
        vraska = Card.objects.first()
        self.assertIsNone(vraska.loyalty)

        # Import the final, updated data.
        parse_data(final_data, ['RTR'])
        vraska.refresh_from_db()
        self.assertEqual(vraska.loyalty, 5)


class ImportManagementCommandTests(ImportTestBase, TestCase):

    command = 'import_magic_cards'

    def test_import_single_set(self):
        out = StringIO()
        call_command(self.command, 'SOM', stdout=out)
        self.assertEqual(
            "Beginning import of 1 set (SOM).\n"
            "Import complete.\n"
            "Added 1 new Set, 234 new Cards, and 249 new Printings.\n",
            out.getvalue()
        )

        self.assertEqual(Set.objects.count(), 1)
        scars = Set.objects.first()
        self.assertEqual(scars.name, "Scars of Mirrodin")
        self.assertEqual(scars.code, "SOM")

        self.assertEqual(Card.objects.count(), 234)
        self.assertEqual(Printing.objects.count(), 249)
        self.check_common_set_constraints()
