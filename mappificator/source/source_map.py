from typing import Mapping, Optional, Set, Callable, Any

import mappificator.util.mapping_util as mapping_util

from mappificator.source.source_set import SourceSet


class SourceMap:
    """ This encapsulates a map form a SourceSet to another SourceSet

    All mappable fields (classes, fields, methods, and parameters) are stored as dictionaries
    This provides convenience methods for manipulating the overall mapping, as well as viewing the domain and codomain of this map

    Due to the nature of this class, it is always a surjective mapping from A -> B. It may or may not be injective, so the act of performing an inverse results in a InverseSourceMap, which can be transformed into a SourceMap if desired
    """

    def __init__(self, fields: Optional[Mapping] = None, methods: Optional[Mapping] = None, params: Optional[Mapping] = None, classes: Optional[Mapping] = None):
        self.fields = fields if fields is not None else dict()
        self.methods = methods if methods is not None else dict()
        self.params = params if params is not None else dict()
        self.classes = classes if classes is not None else dict()

    def keys(self) -> 'SourceSet':
        """ Returns the source set for the domain of this mapping """
        return SourceSet(set(self.fields.keys()), set(self.methods.keys()), set(self.params.keys()), set(self.classes.keys()))

    def values(self) -> 'SourceSet':
        """ Returns the SourceSet for the codomain of this mapping """
        return SourceSet(set(self.fields.values()), set(self.methods.values()), set(self.params.values()), set(self.classes.values()))

    def filter_keys(self, keys: 'SourceSet', inverse: bool = False) -> 'SourceMap':
        """ Returns a new SourceMap which restricts the domain to a subset of the provided SourceSet """
        return SourceMap(
            mapping_util.filter_keys(self.fields, keys.fields, inverse),
            mapping_util.filter_keys(self.methods, keys.methods, inverse),
            mapping_util.filter_keys(self.params, keys.params, inverse),
            mapping_util.filter_keys(self.classes, keys.classes, inverse))

    def filter_values(self, values: 'SourceSet', inverse: bool = False) -> 'SourceMap':
        """ Returns a new SourceMap which restricts the codomain to a subset of the provided SourceSet """
        return SourceMap(
            mapping_util.filter_values(self.fields, values.fields, inverse),
            mapping_util.filter_values(self.methods, values.methods, inverse),
            mapping_util.filter_values(self.params, values.params, inverse),
            mapping_util.filter_values(self.classes, values.classes, inverse))

    def filter(self, predicate: Callable[[Any, Any], bool]):
        return SourceMap(
            mapping_util.filter_mapping(self.fields, predicate),
            mapping_util.filter_mapping(self.methods, predicate),
            mapping_util.filter_mapping(self.params, predicate),
            mapping_util.filter_mapping(self.classes, predicate))

    def inverse(self) -> 'FuzzySourceMap':
        return FuzzySourceMap(
            mapping_util.invert_mapping(self.fields),
            mapping_util.invert_mapping(self.methods),
            mapping_util.invert_mapping(self.params),
            mapping_util.invert_mapping(self.classes))

    def compose(self, other: 'SourceMap') -> 'SourceMap':
        return SourceMap(
            mapping_util.compose_mapping(self.fields, other.fields),
            mapping_util.compose_mapping(self.methods, other.methods),
            mapping_util.compose_mapping(self.params, other.params),
            mapping_util.compose_mapping(self.classes, other.classes))

    def __str__(self):
        return 'SourceMap: Methods = %d, Fields = %d, Params = %d, Classes = %d' % (len(self.methods), len(self.fields), len(self.params), len(self.classes))


class FuzzySourceMap(SourceMap):
    """ This is a SourceMap which has been inverted but may not be invertible.

    For each mappable field, given a source map f : A -> B, this represents a map g : B -> P{A} where P{} is the power set of A
    """

    def __init__(self, fields: Optional[Mapping] = None, methods: Optional[Mapping] = None, params: Optional[Mapping] = None, classes: Optional[Mapping] = None):
        super().__init__(fields, methods, params, classes)

    def inverse(self) -> 'SourceMap':
        raise RuntimeError('Cannot invert a fuzzy mapping as it is not a functional mapping')

    def compose(self, other: 'SourceMap') -> 'FuzzySourceMap':
        return FuzzySourceMap(
            mapping_util.compose_fuzzy_mapping(self.fields, other.fields),
            mapping_util.compose_fuzzy_mapping(self.methods, other.methods),
            mapping_util.compose_fuzzy_mapping(self.params, other.params),
            mapping_util.compose_fuzzy_mapping(self.classes, other.classes))

    def select(self, selector: Optional[Callable[[Set], Any]] = None) -> 'SourceMap':
        """ Using the provided selection strategy, converts this to a functional mapping by only referencing individual values in the codomain. """
        def peek(s: Set) -> Any:
            for x in s:
                return x
        if selector is None:
            selector = peek
        return SourceMap(
            dict((k, selector(v)) for k, v in self.fields.items()),
            dict((k, selector(v)) for k, v in self.methods.items()),
            dict((k, selector(v)) for k, v in self.params.items()),
            dict((k, selector(v)) for k, v in self.classes.items()))

    def invertible(self) -> bool:
        return all((len(x) == 1 for x in self.fields.values())) and all(len(x) == 1 for x in self.methods.values()) and all(len(x) == 1 for x in self.params.values()) and all(len(x) == 1 for x in self.classes.values())



