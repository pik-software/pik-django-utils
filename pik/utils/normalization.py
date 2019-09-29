import re
from cucco import Cucco

_CUCCO = Cucco()


NORMALIZATIONS = [
    'remove_extra_white_spaces']


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
