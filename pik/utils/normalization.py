import re
import unicodedata
from cucco import Cucco


NFC_FORM = 'NFC'

NUMBER_SIGN = '№'

NORMALIZATIONS = [
    'remove_extra_white_spaces',
    'replace_emojis',
    'remove_accent_marks',
    ('replace_symbols', {'form': NFC_FORM, 'excluded': [NUMBER_SIGN]})]


def normalize(text: str) -> str:
    """
    Text normalization.

    >>> normalize("ООО  'ВЫМПЕЛКОМ' ")
    "ООО 'ВЫМПЕЛКОМ'"
    >>> normalize('ЗАО "ЮВЕЛИРНЫЙ завод')
    'ЗАО "ЮВЕЛИРНЫЙ завод'
    >>> normalize("ОАО 'ЁЛКИ и ПАЛКИ' ")
    "ОАО 'ЁЛКИ и ПАЛКИ'"
    >>> normalize('Столовая №1')
    'Столовая №1'

    :param text: some hand typed text
    :return: normalized text
    """
    return _CUCCO.normalize(text, NORMALIZATIONS)


class CustomCucco(Cucco):
    @staticmethod
    def remove_accent_marks(text, excluded=None):
        # We need to use NFC (Normalization Form Canonical Composition) for
        # normalize composite cyrillic symbols like "Й", "Ё" or "№"

        """Remove accent marks from input text.

        This function removes accent marks in the text, but leaves
        unicode characters defined in the 'excluded' parameter.

        Args:
            text: The text to be processed.
            excluded: Set of unicode characters to exclude.

        Returns:
            The text without accent marks.
        """
        if excluded is None:
            excluded = set()

        return unicodedata.normalize(
            NFC_FORM, ''.join(
                c for c in unicodedata.normalize(NFC_FORM, text)
                if unicodedata.category(c) != 'Mn' or c in excluded))


_CUCCO = CustomCucco()


def company_name_normalization(name: str) -> str:
    """
    Company name normalization

    >>> company_name_normalization("ООО  'ВЫМПЕЛКОМ' ")
    'ООО ВЫМПЕЛКОМ'
    >>> company_name_normalization('ЗАО "ЮВЕЛИРНЫЙ завод')
    'ЗАО ЮВЕЛИРНЫЙ ЗАВОД'
    >>> company_name_normalization('ООО ПИК-Комфорт')
    'ООО ПИК-КОМФОРТ'
    >>> company_name_normalization('ООО ПИК\u2015Комфорт')
    'ООО ПИК-КОМФОРТ'
    >>> company_name_normalization('ООО ПИК - Комфорт')
    'ООО ПИК-КОМФОРТ'
    >>> company_name_normalization('ООО ПИК - - Комфорт')
    'ООО ПИК-КОМФОРТ'
    >>> company_name_normalization('Районный Ёлочный рынок')
    'РАЙОННЫЙ ЁЛОЧНЫЙ РЫНОК'
    >>> company_name_normalization('ZAO “Interfax”')
    'ЗАО INTERFAX'

    :param name: company name
    :return: normalized company name
    """
    name = normalize(name)
    name = _CUCCO.replace_punctuation(name, excluded='-')
    name = re.sub(r'[\u2010-\u2017]', '-', name)
    name = re.sub(r'\s*-\s*', '-', name)
    name = re.sub(r'[-]+', '-', name)
    name = ' '.join(re.findall(r'[\w-]+', name))
    name = name.replace('IP ', 'ИП ')  # Individual entrepreneur
    name = name.replace('OOO ', 'ООО ')  # Limited liability company
    name = name.replace('ZAO ', 'ЗАО ')  # Private joint-stock company
    name = name.replace('ANO ', 'АНО ')  # Autonomous non-profit organization
    name = name.replace('GP ', 'ГП ')  # Unitary state enterprise
    name = name.replace('GUP ', 'ГУП ')  # Unitary state enterprise
    name = name.replace('PK ', 'ПК ')  # Production Cooperative
    name = name.replace('PP ', 'ПП ')  # Political party
    return name.upper()
