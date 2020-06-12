from typing import Optional, Set


class SourceSet:

    def __init__(self, fields: Optional[Set] = None, methods: Optional[Set] = None, params: Optional[Set] = None):
        self.fields = fields if fields is not None else set()
        self.methods = methods if methods is not None else set()
        self.params = params if params is not None else set()

    def __str__(self):
        return 'SourceSet: Methods = %d, Fields = %d, Params = %d' % (len(self.methods), len(self.fields), len(self.params))
