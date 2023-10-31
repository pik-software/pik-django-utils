def get_guid_value(data: dict):
    guid_keys = ('guid', 'request_uid')
    for guid_key in guid_keys:
        if guid_key in data:
            return data[guid_key]
    return None
