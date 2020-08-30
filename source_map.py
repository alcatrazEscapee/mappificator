from typing import Mapping, Optional, Tuple, Iterable

from source_set import SourceSet


class SourceMap:

    @staticmethod
    def compose_direct(a_to_b: 'SourceMap', b_to_c: 'SourceMap') -> 'SourceMap':
        a_to_c_maps = [dict(), dict(), dict()]
        for a_to_b_map, b_to_c_map, a_to_c_map in zip(a_to_b.maps(), b_to_c.maps(), a_to_c_maps):
            for a, b in a_to_b_map.items():
                if b in b_to_c_map:
                    a_to_c_map[a] = b_to_c_map[b]
        return SourceMap(*a_to_c_maps)

    @staticmethod
    def compose_layered(priority_maps: Iterable['SourceMap']) -> 'SourceMap':
        maps = [dict(), dict(), dict()]
        for i, value_map in enumerate(maps):
            keys = set(k for v in priority_maps for k in v.maps()[i])
            priority_value_maps = [p.maps()[i] for p in priority_maps]
            for key in keys:
                for priority_map in priority_value_maps:
                    if key in priority_map:
                        value_map[key] = priority_map[key]
                        break
        return SourceMap(*maps)

    def __init__(self, fields: Optional[Mapping] = None, methods: Optional[Mapping] = None, params: Optional[Mapping] = None):
        super().__init__()
        self.fields = fields if fields is not None else dict()
        self.methods = methods if methods is not None else dict()
        self.params = params if params is not None else dict()

    def maps(self) -> Tuple[Mapping, Mapping, Mapping]:
        return self.fields, self.methods, self.params

    def compose(self, other: 'SourceMap') -> 'SourceMap':
        return SourceMap.compose_direct(self, other)

    def keys(self) -> 'SourceSet':
        return SourceSet(set(self.fields.keys()), set(self.methods.keys()), set(self.params.keys()))

    def values(self) -> 'SourceSet':
        return SourceSet(set(self.fields.values()), set(self.methods.values()), set(self.params.values()))

    def compare_to(self, source: 'SourceSet') -> str:
        return 'SourceMap Compare: Methods = %d / %d (%2.2f%%), Fields = %d / %d (%2.2f%%), Params = %d / %d (%2.2f%%)' % (
            len(self.methods), len(source.methods), 100 * len(self.methods) / len(source.methods),
            len(self.fields), len(source.fields), 100 * len(self.fields) / len(source.fields),
            len(self.params), len(source.params), 100 * len(self.params) / len(source.params)
        )

    def __str__(self):
        return 'SourceMap: Methods = %d, Fields = %d, Params = %d' % (len(self.methods), len(self.fields), len(self.params))
