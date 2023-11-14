from unittest.mock import Mock, patch

from pik.api.filters import StandardizedOrderingFilter
from pik.api.openapi.openapi import EnumNamesAutoSchema


mocked_operation = {
    'parameters': [{
        'name': 'ordering',
        'schema': {'enum': ['field1', 'field2']}}]}


@patch('pik.api.openapi.openapi.EnumNamesAutoSchema.get_model_field_label',
       Mock(return_value='Название поля'))
@patch('pik.api.openapi.openapi.EnumNamesAutoSchema.view',
       Mock(**{'filterset_class.declared_filters': {
           'ordering': StandardizedOrderingFilter(
               fields=(('field1', 'field1'), ('field2', 'field2')))}}))
@patch('rest_framework.schemas.openapi.AutoSchema.get_operation',
       Mock(return_value=mocked_operation))
def test_enum_names_auto_schema():
    auto_schema = EnumNamesAutoSchema()
    operation = auto_schema.get_operation('/api/v1/testview-list/', 'GET')

    assert len(operation['parameters']) == 1
    assert operation['parameters'][0]['name'] == 'ordering'
    assert operation['parameters'][0]['schema']['x-enumNames'] == [
        'Название поля', 'Название поля']
