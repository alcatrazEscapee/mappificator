
from typing import Mapping, MutableMapping, Any, Set, Callable


def append_mapping(a: MutableMapping, b: Mapping):
    for k, v in b.items():
        if k not in a:
            a[k] = v


def invert_mapping(d: Mapping) -> Mapping[Any, Set]:
    """ Given a mapping a : A -> B, not necessarily injective, returns the map a' : B -> P{A} such that ∀ x ∈ A, x ∈ (a' ∘ a)(x) """
    f = dict()
    for k, v in d.items():
        if v not in f:
            f[v] = {k}
        else:
            f[v].add(k)
    return f


def compose_mapping(a: Mapping, b: Mapping) -> Mapping:
    """ Given a : A -> B, and b : B -> C, returns the composition (a ∘ b) : A -> C """
    c = dict()
    for k, v in a.items():
        c[k] = b[v]
    return c


def compose_fuzzy_mapping(a: Mapping[Any, Set], b: Mapping) -> Mapping[Any, Set]:
    """ Given a : A -> P{B} and b : B -> C, returns the composition c : A -> P{C} given by ∀ x ∈ A, c(x) = {b(y) : y ∈ a(x)} """
    c = dict()
    for k, vs in a.items():
        if k not in c:
            ls = set()
            c[k] = ls
        else:
            ls = c[k]
        for v in vs:
            ls.add(b[v])
    return c


def filter_keys(m: Mapping, keys: Set, inverse: bool = False) -> Mapping:
    """ Given m : A -> B, returns the restriction a | keys, or a | keys' if inverse """
    return dict((k, v) for k, v in m.items() if (k in keys) != inverse)


def filter_values(m: Mapping, values: Set, inverse: bool = False) -> Mapping:
    """ Given m : A -> B, returns the restriction on the codomain a | {x ∈ A : m(a) ∉ values }, ' if inverse """
    return dict((k, v) for k, v in m.items() if (v in values) != inverse)


def filter_mapping(m: Mapping, predicate: Callable[[Any, Any], bool]) -> Mapping:
    """ Given m : A -> B, and predicate : A x B -> bool, returns the restriction m' : {x : ∀ x ∈ A, predicate(a, m(a)) } -> B """
    return dict((k, v) for k, v in m.items() if predicate(k, v))
