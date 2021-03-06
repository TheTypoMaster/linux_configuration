import types

def is_sequence(obj):
    return hasattr(obj, '__getitem__') and not isinstance(obj, basestring)

def is_mapping(obj):
    return is_sequence(obj) and hasattr(obj, 'keys')

def is_set(obj):
    return hasattr(obj, '__contains__') and not isinstance(obj, basestring)

def get_primitive_types():
    primitive_types = {t:getattr(types, t) for t in types.__dict__.keys() if t.endswith('Type') }
    for str_type in types.StringTypes:
        assert issubclass(str_type, basestring)
    primitive_types['StringType'] = basestring
    return primitive_types

