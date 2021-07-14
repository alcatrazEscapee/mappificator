# A simple lexical scanner / parser, for simple text based parsing
# Supports many common requirements for all mapping formats

from typing import Optional, Set, Tuple, List


class Parser:
    """
    A simple lexical scanner / parser which is able to handle reading sequentially from strings.
    Provides several convenience methods for scanning, as well as basic error handling and reporting
    """

    NUMERIC = set('0123456789')
    ALPHA = set('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ')
    SYMBOLS = set('/-_$()[]<>.,;')
    IDENTIFIER = NUMERIC | ALPHA | SYMBOLS

    def __init__(self, text: str):
        self.text = text
        self.pointer = 0

    def end(self) -> bool:
        """ If the pointer is at the end of the text """
        return self.pointer >= len(self.text)

    def next(self) -> str:
        """ Get the character at the parser's current pointer """
        return self.text[self.pointer]

    def scan_until(self, end: str, include_end: bool = True) -> str:
        """ Scans until the provided end sequence is reached, returning the substring up to that point. """
        identifier = ''
        while not self.end():
            if self.try_scan(end):
                if include_end:
                    identifier += end
                break
            identifier += self.next()
            self.pointer += 1
        return identifier

    def scan(self, expected: str):
        if not self.try_scan(expected):
            actual = repr(self.text[self.pointer:min(len(self.text), self.pointer + len(expected))])
            self.error('Expected %s, got %s' % (repr(expected), actual))

    def try_scan(self, expected: str) -> bool:
        """ Returns True if the substring at the parser's pointer matches the expected string """
        size = len(expected)
        if self.pointer + size > len(self.text):
            return False
        elif self.text[self.pointer:self.pointer + size] == expected:
            self.pointer += size
            return True
        else:
            return False

    def scan_identifier(self, chars: Optional[Set[str]] = None) -> str:
        """ Scans a sequence of characters from the provided character set. """
        if chars is None:
            chars = Parser.IDENTIFIER
        identifier = ''
        while not self.end():
            c = self.text[self.pointer]
            if c in chars:
                identifier += c
                self.pointer += 1
            else:
                return identifier
        return identifier

    def scan_java_method_descriptor(self) -> Tuple[str, List[str], str]:
        """ Scans a java method descriptor. Returns the return type, parameter types, and the entire descriptor """
        self.scan('(')
        desc = '('
        params = []
        while self.next() != ')':
            param = self.scan_type()
            desc += param
            params.append(param)
        self.scan(')')
        desc += ')'
        ret_type = self.scan_type()
        desc += ret_type
        return ret_type, params, desc

    def scan_type(self) -> str:
        """ Scans a single element of a java method descriptor. Returns the element. """
        identifier = ''
        while self.next() == '[':
            self.scan('[')
            identifier += '['
        if self.next() == 'L':
            identifier += self.scan_until(';')
        else:
            identifier += self.next()
            self.pointer += 1
        return identifier

    def error(self, error_msg: str):
        """ Triggers a parser error with basic diagnostic information """
        lines = self.text.split('\n')
        count = 0
        for line_no, line in enumerate(lines):
            if count + len(line) + 1 < self.pointer:  # +1 for the newline that gets stripped out
                count += len(line) + 1
            else:  # pointer is in this line
                p = self.pointer - count
                lhs = repr(line[:p])[:-1]
                rhs = repr(line[p:])[1:]
                target = ' ' * len(lhs) + '^' + ' ' * (len(rhs) - 1)
                raise RuntimeError('\n'.join([
                    'Parser encountered an error',
                    repr(line),
                    target,
                    error_msg,
                    '  at line %d, col %d' % (1 + line_no, p)
                ]))
