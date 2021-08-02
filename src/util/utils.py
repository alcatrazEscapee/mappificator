from typing import Mapping, Any, Sequence, Dict, TypeVar, Tuple, List

from util.parser import Parser

K = TypeVar('K')
V = TypeVar('V')


def or_else(d: Mapping[K, V], k: K, v: V = None) -> V:
    return d[k] if k in d else v


def filter_none(data: Any) -> Any:
    # Removes all "None" entries in a dictionary, list or tuple, recursively
    if isinstance(data, Dict):
        return dict((key, filter_none(value)) for key, value in data.items() if value is not None)
    elif is_sequence(data):
        return [filter_none(p) for p in data if p is not None]
    elif data is not None:
        return data
    else:
        raise ValueError('None passed to `del_none`, should not be possible.')


def is_sequence(data_in: Any) -> bool:
    return isinstance(data_in, Sequence) and not isinstance(data_in, str)


# Java Utilities


def convert_type_to_descriptor(name: str) -> str:
    """ Converts a java type (such as 'int', 'String', 'bool[]') into the respective descriptor (such as 'I', 'Lnet/java/String;', '[Z')
    Optionally will remap objects using the provided dictionary
    """
    parser = Parser(name)
    for key, desc in JAVA_TYPE_TO_DESCRIPTOR.items():
        if parser.accept(key):
            break
    else:
        desc = 'L%s;' % parser.accept_from(Parser.IDENTIFIER - set('[]'))

    arrays = 0
    while parser.accept('[]'):
        arrays += 1
    return '[' * arrays + desc


def convert_descriptor_to_type(desc: str) -> Tuple[str, int]:
    """ Converts a java descriptor to the java type, in the inverse of convert_descriptor_to_type()
    Returns the type, and the number of array levels (e.g. [[Z would return ('boolean', 2), not 'boolean[][]'
    Optionally will remap objects using the provided dictionary
    """
    parser = Parser(desc)
    arrays = 0
    while parser.accept('['):
        arrays += 1
    key = parser.peek()
    if key in JAVA_DESCRIPTOR_TO_TYPE:
        return JAVA_DESCRIPTOR_TO_TYPE[key], arrays
    else:
        parser.expect('L')
        name = parser.accept_until(';')
        return name, arrays


def remap_descriptor(desc: str, remap: Dict[str, str]) -> str:
    parser = Parser(desc)
    arrays = 0
    while parser.peek() == '[':
        parser.expect('[')
        arrays += 1
    arrays = '[' * arrays
    key = parser.peek()
    if key in JAVA_DESCRIPTOR_TO_TYPE:
        parser.pointer += 1
        return arrays + key
    else:
        parser.expect('L')
        cls = parser.accept_until(';')
        cls = or_else(remap, cls, cls)
        return arrays + 'L%s;' % cls


def remap_method_descriptor(desc: str, remap: Dict[str, str]) -> str:
    """ Remaps a java method descriptor from one class naming scheme to another """
    ret_type, param_types = split_method_descriptor(desc)
    ret_type = remap_descriptor(ret_type, remap)
    param_types = [remap_descriptor(param_type, remap) for param_type in param_types]
    return '(%s)%s' % (''.join(param_types), ret_type)


def split_method_descriptor(desc: str) -> Tuple[str, List[str]]:
    """ Extracts individual elements from a java method descriptor
    Returns the return type, and a list of the parameter types
    """
    parser = Parser(desc)
    ret_type, params, _ = parser.accept_method_descriptor()
    parser.finish()
    return ret_type, params


# Various Java constants

JAVA_KEYWORDS = {'abstract', 'assert', 'boolean', 'break', 'byte', 'case', 'catch', 'char', 'class', 'const', 'continue', 'default', 'do', 'double', 'else', 'enum', 'extends', 'final', 'finally', 'float', 'for', 'goto', 'if', 'implements', 'import', 'instanceof', 'int', 'interface', 'long', 'native', 'new', 'package', 'private', 'protected', 'public', 'return', 'short', 'static', 'strictfp', 'super', 'switch', 'synchronized', 'this', 'throw', 'throws', 'transient', 'try', 'void', 'volatile', 'while', 'true', 'false', 'null'}

JAVA_TYPE_TO_DESCRIPTOR = {
    'byte': 'B',
    'char': 'C',
    'double': 'D',
    'float': 'F',
    'int': 'I',
    'long': 'J',
    'short': 'S',
    'boolean': 'Z',
    'void': 'V'
}
JAVA_DESCRIPTOR_TO_TYPE = dict((v, k) for k, v in JAVA_TYPE_TO_DESCRIPTOR.items())

ACC_STATIC = 8
ACC_SYNTHETIC = 4096
