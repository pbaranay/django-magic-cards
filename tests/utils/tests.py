from django.core.management import call_command
from django.db.models import Count
from django.test import TestCase
from django.utils.six import StringIO

from magic_cards.models import Card, Printing, Set
from magic_cards.utils.initial_import import import_cards


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


class ImportScriptTests(ImportTestBase, TestCase):

    def test_import_all_cards(self):
        import_cards()

        self.assertEqual(Set.objects.count(), 213)
        self.assertEqual(Card.objects.count(), 17478)
        self.assertEqual(Printing.objects.count(), 34169)

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
