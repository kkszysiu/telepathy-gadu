#!/usr/bin/env python
# -*- coding: utf-8

import unittest
import struct

from lqsoft.cstruct.common import CStruct
from lqsoft.cstruct.fields.numeric import *
from lqsoft.cstruct.constraints import *

__author__ = "lreqc"
__date__ = "$2009-07-21 00:43:44$"

class NumericFieldTest(unittest.TestCase):

    def setUp(self):
        self.ivalue = 42
        self.idata = struct.pack('<i', self.ivalue)

    def test0Pack(self):
        class TestStruct(CStruct):
            intField = NumericField(0, ctype='int')

        s = TestStruct(intField=self.ivalue)
        self.assert_(s.intField == self.ivalue)
        self.assert_( s.pack() == self.idata )

    def test0Unpack(self):
        class TestStruct(CStruct):
            intField = NumericField(0, ctype='int')

        s, offset = TestStruct.unpack(self.idata)
        self.assert_(s.intField == self.ivalue)

    def testPrefixMatch(self):
        class TestStruct(CStruct):
            intField = NumericField(0, ctype='int', prefix=self.idata[0:2])

        v, offset = TestStruct.unpack(self.idata)
        self.assert_(v.intField == self.ivalue)

    def testPrefixMismatch(self):
        class TestStruct(CStruct):
            intField = NumericField(0, ctype='int', prefix=chr(ord(self.idata[0])+13%255))

        try:
            v, offset = TestStruct.unpack(self.idata)            
            self.fail('Invalid prefix accepted by field during unpack.')
        except UnpackException, e:
            if not isinstance(e.constraint, PrefixConstraint):
                self.fail(e.getMessage())
            # otherwise we succeded

    def testPrefixTooLong(self):
        class TestStruct(CStruct):
            intField = NumericField(0, ctype='int', prefix=(self.idata+'\x00') )

        try:
            v, offset = TestStruct.unpack(self.idata)            
            self.fail('Too long prefix accepted by field during unpack.')
        except UnpackException, e:
            if not isinstance(e.constraint, PrefixConstraint):
                self.fail(e.getMessage())
            # otherwise we succeded

    def testPrefixEmpty(self):
        class TestStruct(CStruct):
            intField = NumericField(0, ctype='int', prefix='' )

        v, offset = TestStruct.unpack(self.idata)
        self.assert_(v.intField == self.ivalue)

    def testByteAndShort(self):
        class TestStruct(CStruct):
            byteField = ByteField(0)
            shortField = ShortField(1)
            intField = IntField(2)

        s = TestStruct(byteField=42, shortField=-30000, intField=4000000)
        s2, offset = TestStruct.unpack( s.pack() )

        self.assert_(s2.intField == s.intField)
        self.assert_(s2.byteField == s.byteField)
        self.assert_(s2.shortField == s.shortField)

    def testOffset(self):
        class TestStruct(CStruct):
            f1 = IntField(0, offset=0)
            f2 = IntField(1, offset=4)           

        data = [chr(x) for x in xrange(64)]
        data[16:20] = self.idata
        data = "".join(data)

        v, offset = TestStruct.unpack(data, 16)
        self.assert_(v.f1 == self.ivalue)

    def testOmmitUnpack(self):
        class TestStruct(CStruct):
            f1 = UIntField(0, prefix__ommit='\x00')
            f2 = UIntField(1)
            f3 = IntField(2)

        d = struct.pack("<Ii", 0xcafebabe, 2)
        v, offset = TestStruct.unpack(d)
        self.assertEqual(offset, 8)
        self.assertEqual(v.f1, None)
        self.assertEqual(v.f2, 0xcafebabe)
        self.assertEqual(v.f3, 2)

    def testOmmitPack(self):
        class TestStruct(CStruct):
            f1 = UIntField(0, prefix__ommit='\x00')
            f2 = UIntField(1)
            f3 = IntField(2)

        s = TestStruct(f1=None, f2=2, f3=3)
        self.assertEqual(s.f2, 2)
        self.assertEqual(s.f3, 3)
        self.assertEqual( s.pack(), '\x02\x00\x00\x00\x03\x00\x00\x00')

    def testOmmitPackWithOffset(self):
        class TestStruct(CStruct):
            offset_field = UIntField(0)
            not_important = IntField(1, prefix__ommit='\x02')
            data = IntField(2, offset='offset_field')

        # s = TestStruct(data=0xcafe)
        # s.pack()
        # self.assertEqual(s.offset_field, 8)

        s = TestStruct(not_important=None, data=0xcafe)
        s.pack()
        self.assertEqual(s.offset_field, 4)
        


    def testBoundViolation(self):
        class A(CStruct):
            f = ByteField(0)

        class B(CStruct):
            f = ShortField(1)

        class C(CStruct):
            f = UIntField(2)

        try:
             A(b=5442)
             self.fail("Illegal values accepted for byte field.")
        except:
            return

        try:
             B(f=5645442)
             self.fail("Illegal values accepted for short field.")
        except:
            return

        try:
             C(f=-1)
             self.fail("Illegal values accepted for unsigned integer.")
        except:
            return


if __name__ == '__main__':
    import lqsoft.cstruct.test.test_numeric
    
    suite = unittest.TestLoader().loadTestsFromName('NumericFieldTest.testOmmitPackWithOffset', lqsoft.cstruct.test.test_numeric)
    unittest.TextTestRunner(verbosity=2).run(suite)
