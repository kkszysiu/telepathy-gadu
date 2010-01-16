#!/usr/bin/env python
# -*- coding: utf-8

__author__ = "Łukasz Rekucki"
__date__ = "$2009-07-19 09:50:34$"

from sunshine.lqsoft.cstruct.common import CField, CStruct
from sunshine.lqsoft.cstruct.fields.numeric import UIntField
from sunshine.lqsoft.cstruct.fields.complex import StructField

from sunshine.lqsoft.cstruct.constraints import *

def string_padder(opts):
    pad = opts['padding']
    opts['value'] += pad*'\x00'

class StringField(CField):    
    KEYWORDS = dict(CField.KEYWORDS,
        length= lambda lv: LengthConstraint(\
            length=lv, padding_func=string_padder) )

    def __init__(self, idx, default='', length=0, **kwargs):
        CField.__init__(self, idx, default, **dict(kwargs, length=length) )
        
    def _format_string(self, opts):
        if opts['length'] == -1:
            opts['length'] = len(opts['data']) - opts['offset']
            
        return '<'+str(opts['length'])+'s'

    def _retrieve_value(self, opts):
         (v, offset) = CField._retrieve_value(self, opts)
         return (v[0], offset)

  
class NullStringField(CField):
    KEYWORDS = dict(CField.KEYWORDS,
        max_length= lambda lv: MaxLengthConstraint(length=lv) )
            
    def _format_string(self, opts):
        return '<'+str(opts['length'])+'s'

    def _before_unpack(self, opts):
        CField._before_unpack(self, opts)
        try:
            opts['length'] = opts['data'].index('\0', opts['offset']) - opts['offset'] + 1
            if opts.has_key('max_length'):
                opts['length'] = min(opts['max_length'], opts['length'])
        except ValueError:
            raise UnpackException("Unterminated null string occured.")

    def before_pack(self, obj, offset, **opts):
        value = getattr(obj, self.name)
        return CField.before_pack(self,obj, offset, length=len(value), **opts)

    def pack(self, obj, offset, **opts):
        value = getattr(obj, self.name)
        return CField.pack(self, obj, offset, length=len(value), **opts)

    def _retrieve_value(self, opts):
        (v, offset) = CField._retrieve_value(self, opts)
        return (v[0], offset)

    def set_value(self, obj, value):
        if not isinstance(value, str) or value[-1] != '\0':
            raise ValueError("NullStringField value must a string with last character == '\\0'.")
        
        return CField.set_value(self, obj, value)

class CStruct_VarString(CStruct):
    length = UIntField(0)
    text = StringField(1, length='length')

class VarcharField(StructField):
    def __init__(self, idx, default='', **opts):        
        if isinstance(default, str):
            default = CStruct_VarString(text=default)            
        StructField.__init__(self, idx, CStruct_VarString, default, **opts)
