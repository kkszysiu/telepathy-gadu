# -*- coding: utf-8
#
__author__= "Łukasz Rekucki (lqc)"
__date__ = "$2009-07-13 17:06:21$"
__doc__ = """Packet structures for Gadu-Gadu 8.0"""

# standard library stuff
import hashlib
import struct

# Cstruct stuff
from gadu.lqsoft.cstruct.common import CStruct
from gadu.lqsoft.cstruct.fields.numeric import *
from gadu.lqsoft.cstruct.fields.text import *
from gadu.lqsoft.cstruct.fields.complex import *



# useful helpers
from gadu.lqsoft.utils import Enum

# base protocol
from gadu.lqsoft.pygadu.packets import inpacket, outpacket
from gadu.lqsoft.pygadu.network_base import GaduPacket

#
# COMMON STRUCTURES
#
class StructStatus(CStruct):
    uin             = IntField(0)
    status          = IntField(1)
    flags           = IntField(2)
    remote_ip       = IntField(3)
    remote_port     = ShortField(4)
    image_size      = ByteField(5)
    reserved01      = ByteField(6)
    reserved02      = IntField(7)
    description     = VarcharField(8)

class StructConference(CStruct):
    attr_type       = ByteField(0, default=0x01)
    rcp_count       = IntField(1)
    recipients      = ArrayField(2, length='rcp_count', subfield=IntField(0))

class StructRichText(CStruct):
    attr_type       = ByteField(0, default=0x02)
    length          = UShortField(1)
    format          = StringField(2, length='length', default='\x00\x00\x08\x00\x00\x00')

class StructMsgAttrs(CStruct):
    conference     = StructField(0, struct=StructConference, prefix__ommit="\x01")

    # additional formating for the plain_message version
    richtext       = StructField(1, struct=StructRichText, prefix__ommit="\x02")


class StructMessage(CStruct):
    CLASS = Enum({
        'QUEUED':   0x0001,
        'MESSAGE':  0x0004,
        'CHAT':     0x0008,
        'CTCP':     0x0010,
        'NOACK':    0x0020,
    })

    klass               = IntField(0)
    offset_plain        = IntField(1) # tekst
    offset_attrs        = IntField(2) # atrybuty

    # the message in HTML (the server sometimes forgets to place the 
    # ending '\0' char, so just cut-off the message at the plain_message offset
    # encoding: utf-8
    html_message        = StringField(3, length=property(\
                    lambda opts: opts['obj'].offset_plain - opts['offset'],\
                    lambda opts, new_value: new_value ) )

    # the message in plain text
    # NOTE: encoding is cp1250
    plain_message       = NullStringField(4, offset='offset_plain')

    # if the message is part of a conference, this includes useful data
    attrs               = StructField(5, struct=StructMsgAttrs, offset='offset_attrs')

#
# PACKETS
#
@outpacket(0x31)
class LoginPacket(GaduPacket):
    uin             = UIntField(0)
    language        = StringField(1, length=2, default='pl')
    hash_type       = UByteField(2, default=0x02)
    login_hash      = StringField(3, length=64)
    status          = UIntField(4, default=0x02)
    flags           = UIntField(5, default=0x03)
    features        = UIntField(6, default=0x37)
    local_ip        = IntField(7)
    local_port      = ShortField(8)
    external_ip     = IntField(9)
    external_port   = ShortField(10)
    image_size      = UByteField(11, default=0xff)
    unknown01       = UByteField(12, default=0x64)
    version         = VarcharField(13, default="Gadu-Gadu Client build 8.0.0.9103")
    description     = VarcharField(14)

    def update_hash(self, password, seed):
        """Uaktualnij login_hash używając algorytmu SHA1"""
        hash = hashlib.new('sha1')
        hash.update(password)
        hash.update(struct.pack('<i', seed))
        self.login_hash = hash.digest()

@inpacket(0x35)
class LoginOKPacket(GaduPacket): #LoginOk80
    reserved       = IntField(0, True)

@inpacket(0x2e)
class MessageInPacket(GaduPacket): #RecvMsg80
    sender              = IntField(0)
    seq                 = IntField(1)
    time                = IntField(2)
    content             = StructField(3, struct=StructMessage)

@outpacket(0x2d)
class MessageOutPacket(GaduPacket):
    recipient           = IntField(0, default=None)
    seq                 = IntField(1)
    content             = StructField(2, struct=StructMessage)

@outpacket(0x38)
class ChangeStatusPacket(GaduPacket): #NewStatus80
    STATUS = Enum({
        'NOT_AVAILBLE':         0x0001,
        'NOT_AVAILBLE_DESC':    0x0015,
        'FFC':                  0x0017,
        'FFC_DESC':             0x0018,
        'AVAILBLE':             0x0002,
        'AVAILBLE_DESC':        0x0004,
        'BUSY':                 0x0003,
        'BUSY_DESC':            0x0005,
        'DND':                  0x0021,
        'DND_DESC':             0x0022,
        'HIDDEN':               0x0014,
        'HIDDEN_DESC':          0x0016,
        'DND':                  0x0021,
        'BLOCKED':              0x0006,
        'MASK_FRIEND':          0x8000,        
        'MASK_GFX':             0x0100,
        'MASK_STATUS':          0x4000,
    })

    status           = IntField(0)
    flags            = IntField(1)
    #description     = VarcharField(2, default='test')
    description_size = UIntField(2)
    description      = StringField(3, length='description_size')

@inpacket(0x36)
class StatusUpdatePacket(GaduPacket): # Status80
    contact         = StructField(0, struct=StructStatus)

@inpacket(0x37)
class StatusNoticiesPacket(GaduPacket): # NotifyReply80
    contacts        = ArrayField(0, length=-1, subfield=StructField(0, struct=StructStatus))

#
# Contact database altering packets
#
@outpacket(0x2f)
class ULRequestPacket(GaduPacket): # UserListReq80
    """Import contact list from the server"""
    TYPE = Enum({
        'PUT':      0x00,
        'PUT_MORE': 0x01,
        'GET':      0x02,
    })

    type    =   ByteField(0)
    data    =   StringField(1, length=-1)

@inpacket(0x30)
class ULReplyPacket(GaduPacket): # UserListReply80
    TYPE = Enum({
        'PUT_REPLY':        0x00,
        'PUT_REPLY_MORE':   0x02,
        'GET_REPLY_MORE':   0x04,
        'GET_REPLY':        0x06,
    })

    type    =   ByteField(0)
    data    =   StringField(1, length=-1)

    @property
    def is_get(self):
        return (self.type & self.TYPE.GET_REPLY_MORE)

    @property
    def is_final(self):
        return (self.type & 0x02)
