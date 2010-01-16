#!/usr/bin/env python
# -*- coding: utf-8

import unittest
import struct

from lqsoft.cstruct.common import CStruct
from lqsoft.cstruct.fields.complex import *
from lqsoft.cstruct.fields.numeric import IntField, UIntField
from lqsoft.cstruct.fields.text import NullStringField
from lqsoft.cstruct.constraints import *

__author__="lreqc"
__date__ ="$2009-07-21 00:43:44$"

class ArrayFieldTest(unittest.TestCase):

    def setUp(self):
        self.svalue = [1,1,2,3,5,8]
        self.slen = len(self.svalue)
        self.sdata = struct.pack("<"+str(self.slen)+"i", *self.svalue)
        # self.sdata_ext = struct.pack("<I", self.slen) + self.sdata

    def testArrayPack(self):
        class TestStruct(CStruct):
            array = ArrayField(0, length = self.slen, subfield=IntField(0))

        s = TestStruct(array=self.svalue)
        try:
            s.array[1] = 'ala ma kota' # this should fail
            self.fail('Integer array accepted a string')
        except ValueError:
            pass

        self.assertEqual( s.array , self.svalue)
        self.assertEqual( s.pack(), self.sdata)

    def testArrayUnpack(self):
        class TestStruct(CStruct):
            array = ArrayField(0, length = self.slen, subfield=IntField(0))

        s, offset = TestStruct.unpack(self.sdata)

        self.assertEqual(s.array, self.svalue)
        for i in xrange(0, self.slen):
            self.assertEqual( s.array[i], self.svalue[i])

class StructFieldTest(unittest.TestCase):
    
    def setUp(self):
        class InnerStruct(CStruct):
            one = IntField(0, default=13)
            two = IntField(1, default=42)

        class OuterStruct(CStruct):
            pad = NullStringField(0, default='KOT\0')
            inner = StructField(1, struct=InnerStruct)
            post = UIntField(2, default=0xbebafeca)

        self.OuterStruct = OuterStruct
        self.InnerStruct = InnerStruct

        self.inner = InnerStruct()
        self.inner_data = self.inner.pack()

    def testAccess(self):        
        s = self.OuterStruct(inner=self.inner)
        self.assertEqual(s.pad, 'KOT\0')
        self.assertEqual(s.post, 0xbebafeca)
        self.assertEqual(s.inner, self.inner)

    def testPack(self):
        s = self.OuterStruct(inner=self.inner)
        data = s.pack()
        print repr(data)
        self.assertEqual( data[4:-4], self.inner_data )

    def testGaduMsgOut(self):
        from lqsoft.pygadu.network import *
        import time

        html_text = """<span style="color:#000000; font-family:'MS Shell Dlg 2'; font-size:12pt; ">ala</span>"""
        rcpt = 1849224
        klass = MessageOutPacket
        attrs = StructMsgAttrs()
        attrs.richtext = StructRichText()

        payload = StructMessage(klass=StructMessage.CLASS.CHAT, \
            html_message=html_text, plain_message='ala\0', \
            attrs = attrs)

        packet = klass( recipient=rcpt, seq=int(time.time()), content=payload)
        data = packet.as_packet()
        print
        for (i, b) in enumerate(data):           
            print '%02x' % ord(b),
            if (i+1)%8 == 0: print

        print packet.content.offset_plain
        print repr(data[8+packet.content.offset_plain:])
        print packet.content.offset_attrs

if __name__ == '__main__':
    import lqsoft.cstruct.test.test_complex
    
    suite = unittest.TestLoader().loadTestsFromName('StructFieldTest.testGaduMsgOut', lqsoft.cstruct.test.test_complex)
    unittest.TextTestRunner(verbosity=2).run(suite)