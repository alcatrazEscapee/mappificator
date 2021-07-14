from unittest import TestCase

from util import utils


class UtilsTests(TestCase):

    def test_convert_type_to_descriptor(self):
        self.assertEqual(utils.convert_type_to_descriptor('int'), 'I')
        self.assertEqual(utils.convert_type_to_descriptor('boolean[][]'), '[[Z')
        self.assertEqual(utils.convert_type_to_descriptor('java/util/String'), 'Ljava/util/String;')
        self.assertEqual(utils.convert_type_to_descriptor('package/Class[]'), '[Lpackage/Class;')

    def test_convert_descriptor_to_type(self):
        self.assertEqual(utils.convert_descriptor_to_type('I'), ('int', 0))
        self.assertEqual(utils.convert_descriptor_to_type('[[Z'), ('boolean', 2))
        self.assertEqual(utils.convert_descriptor_to_type('Ljava/util/String;'), ('java/util/String', 0))
        self.assertEqual(utils.convert_descriptor_to_type('[Lpackage/Class'), ('package/Class', 1))

    def test_remap_descriptor(self):
        remap = {'a': 'ClassA', 'b': 'simple/ClassB', 'c': 'easy/ClassC'}
        self.assertEqual(utils.remap_descriptor('I', remap), 'I')
        self.assertEqual(utils.remap_descriptor('[[Z', remap), '[[Z')
        self.assertEqual(utils.remap_descriptor('Labc;', remap), 'Labc;')
        self.assertEqual(utils.remap_descriptor('[[Ld/e/f;', remap), '[[Ld/e/f;')
        self.assertEqual(utils.remap_descriptor('La;', remap), 'LClassA;')
        self.assertEqual(utils.remap_descriptor('[Lb;', remap), '[Lsimple/ClassB;')

    def test_remap_method_descriptor(self):
        remap = {'a': 'ClassA', 'b': 'simple/ClassB', 'c': 'easy/ClassC'}
        self.assertEqual(utils.remap_method_descriptor('()V', remap), '()V')
        self.assertEqual(utils.remap_method_descriptor('([I[[JZ)V', remap), '([I[[JZ)V')
        self.assertEqual(utils.remap_method_descriptor('(La;)La;', remap), '(LClassA;)LClassA;')
        self.assertEqual(utils.remap_method_descriptor('([Lb;Lnope;)Lother;', remap), '([Lsimple/ClassB;Lnope;)Lother;')
        self.assertEqual(utils.remap_method_descriptor('(Lsimple;)Lc;', remap), '(Lsimple;)Leasy/ClassC;')
        self.assertEqual(utils.remap_method_descriptor('([La;)[[La;', remap), '([LClassA;)[[LClassA;')

    def test_split_method_descriptor(self):
        self.assertEqual(utils.split_method_descriptor('()V'), ('V', []))
        self.assertEqual(utils.split_method_descriptor('(IJSZ)V'), ('V', ['I', 'J', 'S', 'Z']))
        self.assertEqual(utils.split_method_descriptor('(La;I[Lb;)Lc;'), ('Lc;', ['La;', 'I', '[Lb;']))
