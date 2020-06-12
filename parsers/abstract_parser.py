# A simple lexical scanner / parser, for simple text based parsing
# Supports many common requirements for all mapping formats

from typing import Optional, Set, Tuple


class AbstractParser:
    IDENTIFIER_CHARS = set('ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789/-_$;()[]<>')

    def __init__(self, text: str):
        self.text = text
        self.pointer = 0

    def eof(self) -> bool:
        return self.pointer >= len(self.text)

    def next(self) -> str:
        return self.text[self.pointer]

    def scan_until(self, end: str) -> str:
        identifier = ''
        while not self.eof():
            if self.try_scan(end):
                identifier += end
                break
            identifier += self.next()
            self.pointer += 1
        return identifier

    def scan(self, expected: str):
        if not self.try_scan(expected):
            self.error('Unexpected EoF, expected %s' % repr(expected))

    def try_scan(self, expected: str) -> bool:
        size = len(expected)
        if self.pointer + size > len(self.text):
            return False
        elif self.text[self.pointer:self.pointer + size] == expected:
            self.pointer += size
            return True
        else:
            return False

    def scan_identifier(self, chars: Optional[Set[str]] = None) -> str:
        if chars is None:
            chars = AbstractParser.IDENTIFIER_CHARS
        identifier = ''
        while not self.eof():
            c = self.text[self.pointer]
            if c in chars:
                identifier += c
                self.pointer += 1
            else:
                return identifier

    def scan_java_method_signature(self) -> Tuple[str, int]:
        self.scan('(')
        identifier = '('
        params = 0
        while self.next() != ')':
            identifier += self.scan_type()
            params += 1
        self.scan(')')
        identifier += ')'
        identifier += self.scan_type()
        return identifier, params

    def scan_type(self) -> str:
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

    def error(self, error_msg):
        print('Parser Error: %s' % error_msg)
        line_num = self.text[:self.pointer].count('\n')
        print('Around: %s' % repr(self.text[self.pointer - 3:self.pointer + 3]))
        print('Line %d:\n%s' % (line_num, repr(self.text.split('\n')[line_num])))
        raise RuntimeError('Stacktrace')
