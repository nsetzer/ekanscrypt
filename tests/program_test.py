import unittest
from ekanscrypt.program import Program

class ParserTestCase(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        pass

    @classmethod
    def tearDownClass(cls):
        pass

    def setUp(self):
        super().setUp()

    def tearDown(self):
        super().tearDown()

    def test_001_operator_unary_int(self):

        prog = Program()

        tests = [
            ( "+", "3", 3),
            ( "-", "3", -3),
            ( "~", "3", -4),
        ]

        for op, b, expected in tests:
            text = "%s %s" % (op, b)
            rv = prog.execute_text(text)
            self.assertEqual(rv['_'], expected, "%s === %s" % (text, expected))

    def test_001_operator_binary_int(self):


        prog = Program()

        tests = [
            ("2", "+", "3", 5),
            ("2", "-", "3", -1),
            ("6", "*", "7", 42),
            ("2", "**", "8", 256),


            # ("0", "@", "0", 0),

        ]

        for a, op, b, expected in tests:
            text = "%s %s %s" % (a, op, b)
            rv = prog.execute_text(text)
            self.assertEqual(rv['_'], expected, "%s === %s" % (text, expected))

    def test_002_operator_unary_float(self):

        prog = Program()

        epsilon = 0.000001

        tests = [
            ( "+", "3.0", 3.0),
            ( "-", "3.0", -3.0),
        ]

        for op, b, expected in tests:
            text = "%s %s" % (op, b)
            rv = prog.execute_text(text)
            self.assertTrue(abs(rv['_'] - expected) < epsilon,
                "%s === %s +/- %s" % (text, expected, epsilon))

    def test_002_operator_binary_float(self):

        prog = Program()

        epsilon = 0.000001

        tests = [
            ( "1.0", "+", "3.0", 4.0),
            ( "1.0", "-", "3.0", -2.0),
            ("8", "/", "2", 4.0),
            ("8", "//", "2", 4),
            ("8", "%", "2", 0),
        ]

        for a, op, b, expected in tests:
            text = "%s %s %s" % (a, op, b)
            rv = prog.execute_text(text)
            self.assertTrue(abs(rv['_'] - expected) < epsilon,
                "%s === %s +/- %s" % (text, expected, epsilon))

    def test_003_operator_unary_logical(self):

        prog = Program()

        tests = [
            ( "!", "true", False),
            ( "!", "false", True),
        ]

        for op, b, expected in tests:
            text = "%s %s" % (op, b)
            rv = prog.execute_text(text)
            self.assertEqual(rv['_'], expected, "%s === %s result: %s" % (text, expected, rv['_']))

    def test_003_operator_binary_logical(self):


        prog = Program()

        tests = [
            ("true", "&&", "false", False),
            ("true", "&&", "true", True),
            ("false", "&&", "false", False),
            ("false", "&&", "true", False),
            ("true", "||", "false", True),
            ("true", "||", "true", True),
            ("false", "||", "false", False),
            ("false", "||", "true", True),

            ("1", "&&", "0", 0),
            ("0", "||", "1", 1),

            ("1", "&&", "2", 2),
            ("1", "||", "2", 1),

            ("0xFF", "&", "0xAA", 0xAA),
            ("0xA0", "|", "0x0A", 0xAA),
            ("0xAA", "^", "0xBB", 0x11),
            ("0x01", "<<", "1", 0x02),
            ("0x02", ">>", "1", 0x01),
        ]

        for a, op, b, expected in tests:
            text = "%s %s %s" % (a, op, b)
            rv = prog.execute_text(text)
            self.assertEqual(rv['_'], expected, "%s === %s result: %s" % (text, expected, rv['_']))

    def test_004_operator_comparison(self):

        prog = Program()

        tests = [
            ("0", "==", "0", True),
            ("0", "==", "1", False),
        ]

        for a, op, b, expected in tests:
            text = "%s %s %s" % (a, op, b)
            rv = prog.execute_text(text)
            self.assertEqual(rv['_'], expected, "%s === %s result: %s" % (text, expected, rv['_']))

    def test_005_assignment(self):

        prog = Program()

        tests = [
            ("a=5; a", 5),
            ("a,b=0,1; a", 0),
            ("a,b=0,1; b", 1),

            ("a=10; a+=1; a", 11),
            ("a=10; a-=1; a", 9),
            ("a=10; a*=2; a", 20),
            ("a=10; a**=2; a", 100),
            ("a=11; a/=2; a", 5.5), # TODO fixme
            ("a=10; a//=2; a", 5),
            ("a=11; a%=2; a", 1),
            #("a=0; a@=0; a", 0),
            ("a=0x02; a<<=1; a", 0x04),
            ("a=0x02; a>>=1; a", 0x01),
            ("a=0xFF; a&=0xAA; a", 0xAA),
            ("a=0x55; a|=0xAA; a", 0xFF),
            ("a=0xFF; a^=0xAA; a", 0x55),
        ]
        for text, expected in tests:
            rv = prog.execute_text(text)
            self.assertEqual(rv['_'], expected, "%s === %s result: %s" % (text, expected, rv['_']))

    def test_006_shell(self):

        prog = Program()

        tests = [
            ("x = exec python '-V';", (0,None, None)),
            ("x = exec false;", (1,None, None))
        ]

        for text, expected in tests:
            text = "%s; x.run()" % text
            print(text)
            rv = prog.execute_text(text)
            actual = rv['_']
            self.assertEqual(len(actual), 3)
            for i, (a, e) in enumerate(zip(actual, expected)):
                if e is not None:
                    self.assertEqual(a, e, "%d: %s != %s" % (i, a ,e))

    # with(f:io.open('./tmp', 'w')){f.write('test');}

    # TODO: (a,b,(c,(d,e)),f)=(1,2,(3,(4,5)),6); print(a,b,c,d,e,f)
def main():
    unittest.main()

if __name__ == '__main__':
    main()
