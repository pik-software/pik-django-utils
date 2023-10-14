from pik.utils.case_utils import camel_to_underscore, underscore_to_camel


def convert(value):
    return underscore_to_camel(camel_to_underscore(value))


def test_camel_snake_camel():
    assert convert('fullName') == 'fullName'
    assert convert('fullName1') == 'fullName1'
    assert convert('fullName123') == 'fullName123'
    assert convert('guidCRM') == 'guidCRM'
    assert convert('codeOIDP') == 'codeOIDP'
    assert convert('code1C') == 'code1C'
    assert convert('code1c') == 'code1c'
