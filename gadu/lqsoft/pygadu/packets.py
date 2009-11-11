# -*- coding: utf-8
__author__="lreqc"
__date__ ="$2009-07-14 01:04:28$"

class Resolver(object):
    __by_ID_in = {}
    __by_ID_out = {}
    __by_class = {}
    __by_name = {}

    @classmethod
    def packet(cls, id, is_out):
        def decorator(pcls):
            dict = cls.__by_ID_out if is_out else cls.__by_ID_in
            conflict = dict.get(id, None)
        
            if conflict is not None:
                raise ValueError("ID %d for packet %s conflicts with %s" \
                    % (id,pcls.__name__,conflict.__name__) )
            if dict.has_key(pcls):
                raise ValueError("Every class can have only ONE ID.")

            dict[id] = pcls
            cls.__by_class[pcls] = (id, is_out)
            cls.__by_name[pcls.__name__] = pcls
            pcls.packet_id = id
            return pcls
        
        return decorator
    
    @classmethod
    def list_packets(cls):
        print "Listing packets:"
        for (klass, (id, is_out)) in sorted(cls.__by_class.iteritems(), key=lambda k: (k[1][1],k[1][0])):
            print klass.__name__, hex(id), "(%s)" % (is_out and "OUT" or "IN")

    @classmethod
    def by_name(cls, name):
        return cls.__by_name[name]
    
    @classmethod
    def by_IDi(cls, id):
        return cls.__by_ID_in[id]

    @classmethod
    def by_IDo(cls, id):
        return cls.__by_ID_out[id]


def inpacket(id):
    return Resolver.packet(id, False)

def outpacket(id):
    return Resolver.packet(id, True)