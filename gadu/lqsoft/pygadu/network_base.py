# -*- coding: utf-8
__author__="lreqc"
__date__ ="$2009-07-14 01:07:32$"

from gadu.lqsoft.pygadu.packets import inpacket, outpacket

from gadu.lqsoft.cstruct.common import CStruct
from gadu.lqsoft.cstruct.fields import complex, numeric

from gadu.lqsoft.utils import Enum

PACKET_HEADER_LENGTH = 8

class GaduPacketHeader(CStruct):
    """Struktura opisująca nagłówek pakietu w GG"""
    msg_type        = numeric.UIntField(0)
    msg_length      = numeric.UIntField(1)

    def __str__(self):
        return '[GGHDR: type=%d, length %d]' % (self.msg_type, self.msg_length)

class GaduPacket(CStruct):
    """Wspólna nadklasa dla wszystkich wiadomości w GG"""
    def as_packet(self):
        data = self.pack()
        hdr = GaduPacketHeader(msg_type=self.packet_id, msg_length=len(data))
        return hdr.pack() + data

    def __str__(self):
        return self.__class__.__name__

#
# INCOMING PACKETS
#
@inpacket(0x01)
class WelcomePacket(GaduPacket):
    seed = numeric.IntField(0)

@inpacket(0x05)
class MessageAckPacket(GaduPacket): #SendMsgAck
    MSG_STATUS = Enum({
        'BLOCKED': 0x0001, 'DELIVERED': 0x0002,
        'QUEUED': 0x0003, 'MBOXFULL': 0x0004,
        'NOT_DELIVERED': 0x0006
    })

    msg_status  = numeric.IntField(0)
    recipient   = numeric.IntField(1)
    seq         = numeric.IntField(2)

@inpacket(0x09)
class LoginFailedPacket(GaduPacket):
    pass

@inpacket(0x0b)
class DisconnectPacket(GaduPacket):
    pass

@inpacket(0x14)
class NeedEmailPacket(GaduPacket):
    pass

@inpacket(0x0d)
class UnavailbleAckPacket(GaduPacket):
    pass

@inpacket(0x07)
class PongPacket(GaduPacket):
    pass

#
# OUTGOING PACKETS
#

class StructNotice(CStruct): # Notify
    TYPE = Enum({
        'BUDDY':    0x01,
        'FRIEND':   0x02,
        'IGNORE':  0x04
    })
    
    uin             = numeric.UIntField(0)
    type            = numeric.UByteField(1, default=0x03)

    def __str__(self):
        return "%d[%d]" (self.uin, self.type)

@outpacket(0x0f)
class NoticeFirstPacket(GaduPacket): #NotifyFirst
    contacts        = complex.ArrayField(0, complex.StructField(0, struct=StructNotice), length=-1)

@outpacket(0x10)
class NoticeLastPacket(GaduPacket): #NotifyLast
    contacts        = complex.ArrayField(0, complex.StructField(0, struct=StructNotice), length=-1)

@outpacket(0x12)
class NoNoticesPacket(GaduPacket):
    pass

@outpacket(0x0d)
class AddNoticePacket(GaduPacket):
    contact        = complex.StructField(0, struct=StructNotice)

@outpacket(0x0e)
class RemoveNoticePacker(GaduPacket):
    contact        = complex.StructField(0, struct=StructNotice)

@outpacket(0x08)
class PingPacket(GaduPacket):
    pass
