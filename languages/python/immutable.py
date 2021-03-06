from collections import Mapping, namedtuple
from typescheck import is_sequence, is_mapping, is_set, get_primitive_types

_PYTHON_PRIMITIVE_TYPES=tuple(get_primitive_types().values())

def recur_freeze_containers(mutable_obj, ignoredtypes=_PYTHON_PRIMITIVE_TYPES):
    """
    dict -> namedtuple (!WARNING! keys can only be [a-zA-Z][a-zA-Z0-9_]*)
    list -> tuple
    set -> frozenset
   """
    if is_mapping(mutable_obj):
        copy = dict(mutable_obj)
        items = copy.iteritems()
    elif is_sequence(mutable_obj):
        copy = list(mutable_obj)
        items = zip(xrange(0, len(copy)), copy)
    elif is_set(mutable_obj):
        return frozenset(mutable_obj)
    elif isinstance(mutable_obj, ignoredtypes):
        return mutable_obj
    else:
        raise TypeError("Cannot freeze {!r} of unsupported data type {}".format(mutable_obj, type(mutable_obj)))

    for k,v in items:
        copy[k] = recur_freeze_containers(v, ignoredtypes)

    if is_mapping(copy):
        return _dict2NamedTuple(copy)
    elif is_sequence(copy):
        return tuple(copy)

def recur_unfreeze_containers(frozen_obj, ignoredtypes=_PYTHON_PRIMITIVE_TYPES):
    """
    namedtuple -> dict
    tuple -> list
    frozenset -> set
    """
    if hasattr(frozen_obj, '_asdict'):
        new = frozen_obj._asdict()
        items = new.iteritems()
    elif is_sequence(frozen_obj):
        new = list(frozen_obj)
        items = zip(xrange(0, len(new)), new)
    elif is_set(frozen_obj):
        return set(frozen_obj)
    elif isinstance(frozen_obj, ignoredtypes):
        return frozen_obj
    else:
        raise TypeError("Cannot unfreeze {!r} of unsupported data type {}".format(frozen_obj, type(frozen_obj)))

    for k,v in items:
        new[k] = recur_unfreeze_containers(v, ignoredtypes)

    return new

def _dict2NamedTuple(d):
    NTFromDict = namedtuple('_NTFromDict', d.keys())
    return NTFromDict(**d)


# !WARNING! frozendcit are not pythonic, see: http://www.python.org/dev/peps/pep-0416/

# 'Whitelist' approach
# Credits :
#   Thibault Toledano for the original closure idea
#   http://code.activestate.com/recipes/576540/
# PROS
#   REALLY read-only, as values in closures cannot be re-assigned (see below) and it uses a builtin read-only data structure
#   dict(freeze_dict(a_dict)) == a_dict
#   the object passed as a parameter doesn't need to be a dict, just to support dict "cast" (an additionnal tmp copy will then be made)
#       e.g. freeze_dict(freeze_dict(a_dict))
# CONS
#   4 blacklisted keys that also are a memory overhead
#   slight access cost overhead due to the wrapping class (but dictproxy is as fast as dict)
#   freeze_dict({}).__class__ != freeze_dict({}).__class__
#   not isinstance(freeze_dict({}), dict)
# EXTENSIONS
#   could be made hashable
#   could implement items/iteritems more efficiently (collections.Mapping return (key, self[key]), which cost a lookup each time)

_DICTPROXY_EXTRA_KEYS = tuple(type('',(),{}).__dict__.keys())
def freeze_dict(original_dict):
    if not isinstance(original_dict, dict):
        original_dict = dict(original_dict)
    for key in _DICTPROXY_EXTRA_KEYS:
        if key in original_dict:
            raise ValueError("frozendict cannot contain '{}' as a key (blacklisted keys : {})".format(key, _DICTPROXY_EXTRA_KEYS))
    dict_proxy = type('',(),original_dict).__dict__
    class TmpFrozenDict(Mapping):
        def __getitem__(self, key):
            if key in _DICTPROXY_EXTRA_KEYS:
                raise KeyError(key)
            return dict_proxy[key]
        def __iter__(self):
            return (k for k in dict_proxy if k not in _DICTPROXY_EXTRA_KEYS)
        def __len__(self):
            return len(dict_proxy) - len(_DICTPROXY_EXTRA_KEYS)
        def __repr__(self):
            return "freeze_dict({!r})".format({k:self[k] for k in self})
    return TmpFrozenDict()

# Closure are not writable:
#   foo.func_closure = None # TypeError: readonly attribute
#   foo.func_closure[0] = None # TypeError: 'tuple' object does not support item assignment
#   foo.func_closure[0].cell_contents = None # AttributeError: attribute 'cell_contents' of 'cell' objects is not writable


# 'Blacklist' approach
# FROM: http://code.activestate.com/recipes/414283-frozen-dictionaries/
# PROS
#   same memory usage as a dict
#   isinstance(frozendict({}), dict)
#   hashable
# CONS
#   not REALLY read-only, can be hacked
class frozendict(dict):
    def __new__(cls, *args, **kwargs):
        new = dict.__new__(cls)
        dict.__init__(new, *args, **kwargs)
        new._cached_hash = hash(tuple(sorted(new.items())))
        return new

    def __init__(self, *args, **kwargs):
        pass # could be used to modify the frozen dictionary ; ignored because it will be called once on initialization

    def _blocked_attribute(obj):
        raise AttributeError, "A frozendict cannot be modified."
    _blocked_attribute = property(_blocked_attribute)

    __delitem__ = __setitem__ = clear = _blocked_attribute
    pop = popitem = setdefault = update = _blocked_attribute

    def __hash__(self):
        return self._cached_hash

    def __repr__(self):
        return "frozendict({})".format(dict.__repr__(self))
