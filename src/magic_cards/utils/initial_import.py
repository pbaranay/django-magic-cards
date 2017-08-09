import io
import json
import zipfile
from contextlib import closing

import requests
from django.db import transaction

from magic_cards.models import Artist, Card, CardSubtype, CardSupertype, CardType, Printing, Set

MTG_JSON_URL = 'https://mtgjson.com/json/AllSets-x.json.zip'
FALLBACK_MTG_JSON_URL = 'http://mtgjson.com/json/AllSets-x.json.zip'


class Everything:
    """
    Sentinel value for downloading all sets (i.e. skipping nothing).
    """
    pass


def fetch_data():
    try:
        r = requests.get(MTG_JSON_URL)
    except requests.ConnectionError:
        r = requests.get(FALLBACK_MTG_JSON_URL)
    with closing(r), zipfile.ZipFile(io.BytesIO(r.content)) as archive:
        unzipped_files = archive.infolist()
        if len(unzipped_files) != 1:
            raise RuntimeError("Found an unexpected number of files in the MTGJSON archive.")
        data = archive.read(archive.infolist()[0])
    decoded_data = data.decode('utf-8')
    sets_data = json.loads(decoded_data)
    return sets_data


def parse_rarity(string):
    if string == 'Mythic Rare':
        return Printing.Rarity.MYTHIC
    elif string == 'Rare':
        return Printing.Rarity.RARE
    elif string == 'Uncommon':
        return Printing.Rarity.UNCOMMON
    elif string == 'Common':
        return Printing.Rarity.COMMON
    elif string == 'Basic Land':
        return Printing.Rarity.BASIC_LAND
    else:
        return Printing.Rarity.SPECIAL


def parse_data(sets_data, set_codes):
    # Process the data set-by-set
    for code, data in sets_data.items():

        # Skip sets that have not been chosen
        if set_codes is not Everything and code not in set_codes:
            continue

        # Create the set
        magic_set, _ = Set.objects.get_or_create(code=code, name=data['name'])

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
            card, _ = Card.objects.get_or_create(
                name=name, defaults={
                    'mana_cost': mana_cost,
                    'text': text,
                    'power': power,
                    'toughness': toughness,
                })
            supertypes = card_data.get('supertypes', [])
            types = card_data['types']
            subtypes = card_data.get('subtypes', [])
            for supertype_name in supertypes:
                supertype, _ = CardSupertype.objects.get_or_create(name=supertype_name)
                card.supertypes.add(supertype)
            for type_name in types:
                card_type, _ = CardType.objects.get_or_create(name=type_name)
                card.types.add(card_type)
            for subtype_name in subtypes:
                subtype, _ = CardSubtype.objects.get_or_create(name=subtype_name)
                card.subtypes.add(subtype)

            # Printing info
            artist_name = card_data['artist']
            artist, _ = Artist.objects.get_or_create(full_name=artist_name)
            multiverse_id = card_data.get('multiverseid', None)  # Missing on certain sets
            flavor_text = card_data.get('flavor_text', '')
            rarity = card_data['rarity']
            number = card_data.get('number', '')  # Absent on old sets
            Printing.objects.get_or_create(
                card=card,
                set=magic_set,
                rarity=parse_rarity(rarity),
                flavor_text=flavor_text,
                artist=artist,
                number=number,
                multiverse_id=multiverse_id)


@transaction.atomic
def import_cards(set_codes=Everything):
    sets_data = fetch_data()
    parse_data(sets_data, set_codes)


if __name__ == "__main__":
    import_cards()
