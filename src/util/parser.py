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
        self.length = len(self.text)
        self.pointer = 0

    def expect(self, expected: str, error: bool = True) -> bool:
        """
        Expects a string.
        Errors if the string was not found.
        """
        length = len(expected)
        actual = self.peek(length, error=False)  # error has more context here
        if actual == expected:
            self.advance(length)
            return True
        elif error:
            self.error('Expected %s, got %s' % (repr(expected), repr(actual)))
        return False

    def accept(self, option: str) -> bool:
        """
        Accepts a string if present.
        Returns true if the string was found
        """
        return self.expect(option, False)

    def accept_from(self, chars: Set[str]) -> str:
        """
        Accepts characters from the given set until either the end of the text, or a character not in the set is reached.
        Returns the string that was accepted.
        """
        if '' in chars:  # empty string is returned by peek() when end of input is reached. Cannot silently accept it
            raise ValueError('Cannot accept from an empty string')
        seq = ''
        c = self.peek(error=False)
        while c in chars:
            seq += c
            self.advance()
            c = self.peek(error=False)
        return seq

    def accept_identifier(self) -> str:
        return self.accept_from(Parser.IDENTIFIER)

    def accept_integer(self) -> int:
        return int(self.accept_from(Parser.NUMERIC))

    def accept_until(self, terminal: str) -> str:
        """
        Accepts characters up until the terminal.
        Returns the accepted sequence, minus the terminal.
        """
        return self.accept_until_including(terminal, False)

    def accept_until_including(self, terminal: str, include_terminal: bool = True) -> str:
        """
        Accepts characters up until and including the provided terminal.
        Returns the accepted sequence.
        """
        length = len(terminal)
        seq = ''
        while self.peek(length) != terminal:
            seq += self.peek()
            self.advance()
        if include_terminal:
            seq += terminal
            self.advance(length)
        return seq

    def accept_method_descriptor(self) -> Tuple[str, List[str], str]:
        """ Scans a java method descriptor. Returns the return type, parameter types, and the entire descriptor """
        self.expect('(')
        desc = '('
        params = []
        while self.peek() != ')':
            param = self.accept_descriptor()
            desc += param
            params.append(param)
        self.expect(')')
        desc += ')'
        ret_type = self.accept_descriptor()
        desc += ret_type
        return ret_type, params, desc

    def accept_descriptor(self) -> str:
        """ Scans a single element of a java method descriptor. Returns the element. """
        identifier = ''
        while self.peek() == '[':
            self.expect('[')
            identifier += '['
        if self.peek() == 'L':
            identifier += self.accept_until_including(';')
        else:
            identifier += self.peek()
            self.pointer += 1
        return identifier

    # Internal / Utility

    def end(self) -> bool:
        """ If the pointer is at the end of the text. """
        return self.pointer >= len(self.text)

    def finish(self):
        """ Errors if the parser is not at the end of the text. """
        if not self.end():
            self.error('Unexpected trailing characters: %s' % repr(self.peek(20, False)))

    def advance(self, amount: int = 1):
        """ Advance the parser's pointer by the provided amount. """
        if self.pointer + amount > self.length:
            self.error('Tried to advance off the end of the input')
        self.pointer += amount

    def peek(self, length: int = 1, error: bool = True) -> str:
        """ Peeks at the next {length} characters in the text. """
        if self.pointer + length > len(self.text):
            if error:
                self.error('Tried to peek off the end of the input')
            else:
                return self.text[self.pointer:]
        else:
            return self.text[self.pointer:self.pointer + length]

    def error(self, message: Optional[str] = None):
        """ Triggers a parser error with basic diagnostic information """
        raise ParserError(self, message)


class ParserError(RuntimeError):
    def __init__(self, parser: Parser, message: str):
        lines = parser.text.split('\n')
        count = line_no = 0
        line = ''
        for line_no, line in enumerate(lines):
            if count + len(line) + 1 < parser.pointer:  # +1 for the newline that gets stripped out
                count += len(line) + 1
            else:  # pointer is in this line
                break

        p = parser.pointer - count
        lhs = repr(line[:p])[:-1]
        rhs = repr(line[p:])[1:]
        target = ' ' * len(lhs) + '^' + ' ' * (len(rhs) - 1)
        if message is None:
            message = 'Unknown error'

        self.parser_error_message = message
        self.target_line = line
        self.target_line_no = 1 + line_no
        self.target_col = p

        super(ParserError, self).__init__('\n'.join([
            'Parser encountered an error',
            repr(line),
            target,
            message,
            '  at line %d, col %d' % (self.target_line_no, self.target_col)
        ]))