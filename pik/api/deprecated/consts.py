TO_DEPRECATED_ORDERING_RULES = {
    'guid': 'uid',
    '-guid': '-uid',
}


TO_ACTUAL_ORDERING_RULES = {
    'uid': 'guid',
    '-uid': '-guid',
}


TO_DEPRECATED_FIELD_RULES = {
    'guid': '_uid',
    'version': '_version',
    'type': '_type',
}


TO_ACTUAL_FIELD_RULES = {
    '_uid': 'guid',
    '_version': 'version',
    '_type': 'type'
}


TO_DEPRECATED_FILTER_RULES = {
    'guid': 'uid',
}


TO_ACTUAL_FILTER_RULES = {
    'uid': 'guid',
}
