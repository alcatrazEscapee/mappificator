from unittest import TestCase
from typing import Callable, Any

from util.parser import Parser, ParserError


class ParserTests(TestCase):

    def test_peek(self):
        p = Parser('abc')
        self.assertEqual('a', p.peek())
        self.assertEqual('abc', p.peek(3))
        self.assertErrors(lambda: p.peek(5), 'Tried to peek off the end of the input')

    def test_advance(self):
        p = Parser('abcdef')
        self.assertEqual('abc', p.peek(3))
        p.advance()
        self.assertEqual('bcd', p.peek(3))
        p.advance(3)
        self.assertEqual('e', p.peek())
        self.assertErrors(lambda: p.advance(3), 'Tried to advance off the end of the input')

    def test_expect(self):
        p = Parser('words and stuff')
        p.expect('words')
        p.advance()
        self.assertEqual('and', p.peek(3))
        self.assertErrors(lambda: p.expect('words'), 'Expected \'words\', got \'and s\'')

        p.expect('and ')
        self.assertEqual('stuff', p.peek(5))
        self.assertErrors(lambda: p.expect('stuffnthings'), 'Expected \'stuffnthings\', got \'stuff\'')

    def test_accept(self):
        p = Parser('onetwothree')
        self.assertFalse(p.accept('two'))
        self.assertTrue(p.accept('one'))
        self.assertEqual('two', p.peek(3))
        self.assertFalse(p.accept('one'))
        self.assertTrue(p.accept('two'))

    def test_accept_from(self):
        p = Parser('3849+=27893')
        self.assertEqual('3849', p.accept_from(Parser.NUMERIC))
        self.assertEqual('+=', p.peek(2))
        self.assertEqual('', p.accept_from(Parser.NUMERIC))
        self.assertEqual('+=', p.accept_from(set('+=')))
        self.assertEqual('27893', p.peek(5))

    def test_accept_until(self):
        p = Parser('SpecialClassName does StuffAndThings')
        self.assertEqual('SpecialClassName', p.accept_until(' '))
        p.expect(' ')
        self.assertEqual('does', p.peek(4))
        self.assertEqual('', p.accept_until('d'))
        self.assertEqual('does StuffAnd', p.accept_until_including('And'))
        self.assertEqual('Things', p.peek(6))

    def assertErrors(self, action: Callable[[], Any], text: str, line_no: int = 1):
        with self.assertRaises(ParserError) as c:
            action()

        self.assertEqual(c.exception.parser_error_message, text)
        self.assertEqual(c.exception.target_line_no, line_no)
