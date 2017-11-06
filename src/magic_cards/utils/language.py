from __future__ import unicode_literals

from magic_cards.models import MAGIC_LANGUAGES


def convert_language_name_to_code(name):
    """
    Given a language name (e.g. "English") returns the corresponding language code (e.g. "en"),
    suitable for passing as the value for ForeignPrinting.language.

    :return: str or None
    """
    languages = {
        'English': 'en',
        'Simplified Chinese': 'zh-hans',
        'Chinese Simplified': 'zh-hans',
        'Traditional Chinese': 'zh-hant',
        'Chinese Traditional': 'zh-hant',
        'French': 'fr',
        'German': 'de',
        'Italian': 'it',
        'Japanese': 'ja',
        'Korean': 'ko',
        'Portuguese': 'pt',
        'Portuguese (Brazil)': 'pt',
        'Russian': 'r',
        'Spanish': 'es',
    }
    return languages.get(name)
