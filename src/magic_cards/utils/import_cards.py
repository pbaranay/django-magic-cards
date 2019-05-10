import io
import json
import zipfile
from contextlib import closing

import requests
from django.db import transaction

from magic_cards.models import Artist, Card, CardSubtype, CardSupertype, CardType, Printing, Set

MTG_JSON_URL = 'https://mtgjson.com/json/AllSets.json.zip'


class Everything:
    """
    Sentinel value for downloading all sets (i.e. skipping nothing).
    """
    pass


def fetch_data():
    r = requests.get(MTG_JSON_URL)
    with closing(r), zipfile.ZipFile(io.BytesIO(r.content)) as archive:
        unzipped_files = archive.infolist()
        if len(unzipped_files) != 1:
            raise RuntimeError("Found an unexpected number of files in the MTGJSON archive.")
        data = archive.read(archive.infolist()[0])
    decoded_data = data.decode('utf-8')
    sets_data = json.loads(decoded_data)
    return sets_data


def parse_rarity(string):
    if string == 'mythic':
        return Printing.Rarity.MYTHIC
    elif string == 'rare':
        return Printing.Rarity.RARE
    elif string == 'uncommon':
        return Printing.Rarity.UNCOMMON
    elif string == 'common':
        return Printing.Rarity.COMMON
    elif string == 'basic land':
        return Printing.Rarity.BASIC_LAND
    else:
        return Printing.Rarity.SPECIAL


class ModelCache(dict):
    def get_or_create(self, model, field, value, **kwargs):
        """
        Retrieves object of class `model` with lookup key `value` from the cache. If not found,
        creates the object based on `field=value` and any other `kwargs`.

        Returns a tuple of `(object, created)`, where `created` is a boolean specifying whether an
        `object` was created.
        """
        result = self[model].get(value.lower())
        created = False
        if not result:
            kwargs[field] = value
            result = model.objects.create(**kwargs)
            self[model][value.lower()] = result
            created = True
        return result, created


def parse_data(sets_data, set_codes):
    # Load supertypes, types, and subtypes into memory
    cache = ModelCache()
    for model in [CardSupertype, CardType, CardSubtype]:
        cache[model] = {obj.name.lower(): obj for obj in model.objects.all()}
    # Load relevant sets into memory
    if set_codes is Everything:
        cache[Set] = {obj.code.lower(): obj for obj in Set.objects.all()}
    else:
        cache[Set] = {obj.code.lower(): obj for obj in Set.objects.filter(code__in=set_codes)}

    # Process the data set-by-set
    for code, data in sets_data.items():

        # Skip sets that have not been chosen
        if set_codes is not Everything and code not in set_codes:
            continue

        # Create the set
        magic_set, set_created = cache.get_or_create(Set, 'code', code, name=data['name'])

        printings_to_create = []

        # Create cards
        all_cards_data = data['cards']
        for card_data in all_cards_data:
            # Skip tokens
            layout = card_data['layout']
            if layout == 'token':
                continue

            # Card info
            name = card_data['name']
            mana_cost = card_data.get('manaCost', '')
            text = card_data.get('text', '')
            power = card_data.get('power', '')
            toughness = card_data.get('toughness', '')
            loyalty = card_data.get('loyalty', None)
            card, created = Card.objects.update_or_create(
                name=name, defaults={
                    'mana_cost': mana_cost,
                    'text': text,
                    'power': power,
                    'toughness': toughness,
                    'loyalty': loyalty,
                })
            supertypes = card_data.get('supertypes', [])
            types = card_data['types']
            subtypes = card_data.get('subtypes', [])
            if not created:
                card.supertypes.clear()
                card.types.clear()
                card.subtypes.clear()
            for supertype_name in supertypes:
                supertype, _ = cache.get_or_create(CardSupertype, 'name', supertype_name)
                card.supertypes.add(supertype)
            for type_name in types:
                card_type, _ = cache.get_or_create(CardType, 'name', type_name)
                card.types.add(card_type)
            for subtype_name in subtypes:
                subtype, _ = cache.get_or_create(CardSubtype, 'name', subtype_name)
                card.subtypes.add(subtype)

            # Printing info
            artist_name = card_data.get('artist') # Missing on certain cards
            if artist_name:
                artist, _ = Artist.objects.get_or_create(full_name=artist_name)
            else:
                artist = None
            multiverse_id = card_data.get('multiverseId', None)  # Missing on certain sets
            flavor_text = card_data.get('flavor', '')
            rarity = card_data['rarity']
            number = card_data.get('number', '')  # Absent on old sets
            # If the Set was just created, we don't need to check if the Printing already exists,
            # and we can leverage bulk_create.
            printing_kwargs = {
                'card': card,
                'set': magic_set,
                'rarity': parse_rarity(rarity),
                'flavor_text': flavor_text,
                'artist': artist,
                'number': number,
                'multiverse_id': multiverse_id
            }
            if set_created:
                printings_to_create.append(Printing(**printing_kwargs))
            else:
                # Use .filter().exists() followed by a create() instead of get_or_create,
                # since these kwargs aren't unique for sets without proper multiverse_ids.
                if not Printing.objects.filter(**printing_kwargs).exists():
                    Printing.objects.create(**printing_kwargs)

        if printings_to_create:
            Printing.objects.bulk_create(printings_to_create)

    # Remove extra Printings caused by data that is duplicated on MTGJSON.
    # https://github.com/mtgjson/mtgjson/issues/388
    if set_codes is Everything or 'BOK' in set_codes:
        bugged_card_names = ['Jaraku the Interloper', 'Scarmaker']
        for name in bugged_card_names:
            extra_printings = Printing.objects.filter(
                set__code='BOK', card__name=name)[1:].values_list(
                    'pk', flat=True)
            Printing.objects.filter(pk__in=list(extra_printings)).delete()

    # Clean up any supertypes, subtypes, and types that have no Cards left.
    for model in [CardSubtype, CardType, CardSupertype]:
        for obj in model.objects.all():
            if obj.card_set.count() == 0:
                obj.delete()


@transaction.atomic
def import_cards(set_codes=Everything):
    sets_data = fetch_data()
    parse_data(sets_data, set_codes)


if __name__ == "__main__":
    import_cards()
