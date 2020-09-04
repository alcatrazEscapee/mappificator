from typing import Optional, Set


class SourceSet:

    def __init__(self, fields: Optional[Set] = None, methods: Optional[Set] = None, params: Optional[Set] = None, classes: Optional[Set] = None):
        self.fields = fields if fields is not None else set()
        self.methods = methods if methods is not None else set()
        self.params = params if params is not None else set()
        self.classes = classes if classes is not None else set()

    def compare_to(self, other: 'SourceSet') -> 'SourceSetComparison':
        return SourceSetComparison(self, other)

    def is_empty(self) -> bool:
        return not self.fields and not self.methods and not self.params and not self.classes

    def __str__(self):
        return 'SourceSet: Methods = %d, Fields = %d, Params = %d, Classes = %d' % (len(self.methods), len(self.fields), len(self.params), len(self.classes))


class SourceSetComparison:

    def __init__(self, left: 'SourceSet', right: 'SourceSet'):
        self.left: 'SourceSet' = left
        self.right: 'SourceSet' = right

        self.left_only: 'SourceSet' = SourceSet(left.fields - right.fields, left.methods - right.methods, left.params - right.params, left.classes - right.classes)
        self.right_only: 'SourceSet' = SourceSet(right.fields - left.fields, right.methods - left.methods, right.params - left.params, right.classes - left.classes)
        self.both: 'SourceSet' = SourceSet(left.fields | right.fields, left.methods | right.methods, left.params | right.params, left.classes | right.classes)
