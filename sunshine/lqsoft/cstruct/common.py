#!/usr/bin/env python
# -*- coding: utf-8

__author__="lreqc"
__date__ ="$2009-07-19 07:48:34$"

import sunshine.lqsoft.cstruct.constraints as const
import struct,sys

def log(msg):
    sys.stderr.write(msg+'\n')


class ICField(object):

    def add_constraint(self, constr):
        pass

    def before_pack(self, obj, offset, **opts):
        pass

    def pack(self, obj, offset, **opts):
        pass

    def unpack(self, obj, data, pos):
        pass

    def get_value(self, obj, current_value):
        pass

    def set_value(self, obj, new_value):
        pass


class CField(ICField):

    KEYWORDS = {
        'offset': const.OffsetConstraint,
        'prefix': const.PrefixConstraint,
    }
    
    def __init__(self, idx, default=None, **kwargs):
        self.idx = idx
        self.default = default
        self.constraints = []        
        self.ommit = []

        for (key,value) in kwargs.iteritems():
            #if key == 'nullable':
            #    continue
                
            if key.endswith('__ommit'):
                key = key[:-7]
                self.ommit.append(key)

            constr = self.KEYWORDS[key](value)
            constr.keyword = key
            self.add_constraint(constr)

        # if there is an ommit field, the field is nullable
        # if there is no ommit field, the field can't be null
        self.nullable = bool(self.ommit)

    def add_constraint(self, constr):
        # add constraint
        # lame version - should be a balanced tree
        index = 0
        length = len(self.constraints)
        while index < length \
          and self.constraints[index].priority <= constr.priority:
            index += 1
        self.constraints.insert(index, constr)

    def _before_unpack(self, opts):
        """Prepare the data for unpacking."""
        for c in self.constraints:
            if not c.before_unpack(opts):
                if c.keyword in self.ommit:
                    opts['__ommit'] = True
                    break
                raise UnpackException('Data buffer failed to satisfy constraint: ' + str(c), c)


    def before_pack(self, obj, offset, **opts):
        """Pack dry-run, so that the field can update depencies"""
        value = getattr(obj, self.name)
        opts.update({'field': self, 'obj': obj, 'value': value, 'offset': offset })

        if (value == None) and self.nullable:
            return 0 # field is ommited

        for c in reversed(self.constraints):
            c.before_pack(opts)

        return struct.calcsize(self._format_string(opts))
        
    def pack(self, obj, offset, **opts):
        """Pack the field into a byte array"""
        value = getattr(obj, self.name)
        
        if (value == None) and self.nullable:
            return '' # field is ommited

        opts.update({'field': self, 'obj': obj, 'value': value, 'offset': offset})
        for c in reversed(self.constraints):
            c.pack(opts)

        return struct.pack( self._format_string(opts), value)

    def unpack(self, obj, data, pos):
        """Unpack the given byte buffer into this field, starting at pos"""
        # before we unpack we need to check things like:
        #  * is the field at given offset ? (yes, this always comes first)
        #  * does the field prefix match ?
        #  * any other stuff the user wants to check
        opts = {'obj': obj, 'data': data, 'offset': pos}
        self._before_unpack(opts)
        
        if not opts.get('__ommit', False):
            return self._retrieve_value(opts)
        else:
            return (None, pos)

    def _format_string(self, opts):
        """The format string for the default retrieval method"""
        return ''

    def _retrieve_value(self, opts):
        #print opts
        fmt = self._format_string(opts)
        fmt_len = struct.calcsize(fmt)
        v = struct.unpack_from(fmt, opts['data'], opts['offset'])
        return (v, opts['offset'] + fmt_len)

    def get_value(self, obj, current_value):
        return current_value

    def set_value(self, obj, new_value):
        # enable niling the field
        if (new_value == None) and self.nullable:
            return None

        # the new value is not yet set on the object
        opts = {'field': self, 'obj': obj, 'value': new_value}      
  
        # trigger constraints
        for constr in self.constraints:
            constr.on_value_set(opts)
            
        return opts['value']

    def __str__(self):
        return str(self.name)

class MetaStruct(type):
    def __new__(cls, name, bases, cdict):
        fields = []
        #internal_dict = {}
        ndict = {}
        # log('Constructing class: ' + name)

        for (field_name, field_value) in cdict.iteritems():
            if isinstance(field_value, CField):
                field_value.name = field_name
                fields.append(field_value)
                #internal_dict[field_name] = field_value
                ndict[field_name] = property( \
                    MetaStruct.getter_for(field_value), \
                    MetaStruct.setter_for(field_value) )
            else:
                ndict[field_name] = field_value

        klass = type.__new__(cls, name, bases, ndict)

        #old_dict = getattr(klass, '_internal', {})
        #internal_dict.update(old_dict)
        #setattr(klass, '_internal', internal_dict)

        fields.sort(key= lambda item: item.idx)

        order = getattr(klass, '_field_order', [])
        order = order + fields
        setattr(klass, '_field_order', order)
        return klass


    @staticmethod
    def getter_for(field):
        def getter(self):
            return field.get_value(self, getattr(self, '_' + field.name))
        return getter

    @staticmethod
    def setter_for(field):
        def setter(self, value):
            # log("Called setter on %r with %r" % (self, name))
            return setattr(self, '_' + field.name, field.set_value(self, value))
        return setter

class CStruct(object):
    __metaclass__ = MetaStruct

    def __init__(self, **kwargs):
        for field in self._field_order:            
            setattr(self, field.name, kwargs.get(field.name,field.default))

    def _before_pack(self, offset=0):        
        for field in self._field_order:
            offset += field.before_pack(self, offset)
        return offset

    def _pack(self, off=0):
        s = ''
        for field in self._field_order:
            data = field.pack(self, off)
            off += len(data)
            s += data
        return s

    def pack(self, offset=0):
        self._before_pack(offset)
        return self._pack(offset)

    @classmethod
    def unpack(cls, data, offset=0):
        print "Unpacking class %s: offset=%d, total_buf=%d" % (cls.__name__, offset, len(data))
        dict = {}
        dp = ItemWrapper(dict)
        
        for field in cls._field_order:
            print "Unpacking field @%d: %s" % (offset, field.name)
            value, next_offset = field.unpack(dp, data, offset)
            dict[field.name] = value
            offset = next_offset
            print "Unpacked: " + repr(value)

        instance = cls(**dict)
        print "Unpacked: " + str(instance)
        return instance, offset
    
    def __field_value(self, field, default=None):
        return field.get_value(self, getattr(self, '_' + field.name, default))

    def __str__(self):
        buf = "CStruct("
        buf += ','.join( "%s = %r" % (field.name, self.__field_value(field)) \
            for field in self._field_order )
        buf += ")"
        return buf

class ItemWrapper(object):
    """Wraps the given object (usually a dict or a list) with
        accessor methods that turn attribute calls to index calls.
        Also provides a handy way, to attach set/get triggers."""

    def __init__(self, obj):
        self._object = obj
        
    def __getattribute__(self, name):
        # play nice with names startign with '_'
        if name.startswith('_'):
            try:
                return object.__getattribute__(self, name)
            except AttributeError:
                return object.__getattribute__(self._object, name[1:])

        return self._get_action(self, name, self._object[name])

    def __setattr__(self, name, value):
        # play nice :)
        if name.startswith('_'):
            return object.__setattr__(self, name, value)

        self._object[name] = self._set_action(self, name, value)

    def __getitem__(self, name):        
        return self._get_action(self, name, self._object[name])

    def __setitem__(self, name, value):
        self._object[name] = self._set_action(self, name, value)

    def __len__(self):
        return self._object.__len__()

    def _set_action(self, me, name, value):
        return value

    def _get_action(self, me, name, value):
        return value
        
    def __str__(self):
        return str(self._object)

    def __eq__(self, other):
        return self._object.__eq__(other)


class ListItemWrapper(ItemWrapper):

    def __getattribute__(self, name):
        try:
            key = int(name)
            return self._get_action(self, name, self._object[key])
        except ValueError:
            return ItemWrapper.__getattribute__(self, name)
    
    def __setattr__(self, name, value):
        try:
            key = int(name)
            self._object[key] = self._set_action(self, name, value)
        except ValueError:
            return ItemWrapper.__setattr__(self, name, value)    
        
class UnpackException(Exception):
    def __init__(self, msg, constraint):
        Exception.__init__(self, msg)
        self.constraint = constraint

class PackingException(Exception):
    def __init__(self, msg, constraint):
        Exception.__init__(self, msg)
        self.constraint = constraint
