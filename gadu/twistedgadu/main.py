#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright (c) 2009 Krzysztof 'kkszysiu' Klinikowski

from twisted.internet.protocol import ClientFactory
from twisted.internet.protocol import Protocol
from twisted.internet import reactor, defer
from twisted.python import log
import sys
import struct

from twistedgadu.comm.packets import *

log.startLogging(sys.stdout)

gg_uin = 4634020
gg_passwd = 'xxxxxx'
gg_status = GGStatuses.Avail
gg_desc = 'test'

contacts_list = ContactsList([\
    Contact(uin= 3993939, shown_name= 'Tralala'), \
    Contact(uin= 4668758, shown_name= 'Anna') ])

#contacts_list = ContactsList()

class GGClient(Protocol):
    def __init__(self):
        self.uin = None
        self.password = None
        self.status = None
        self.desc = None
        self._header = True
        self.__local_ip = "127.0.0.1"
        self.__local_port = 1550
        self.__external_ip = "127.0.0.1"
        self.__external_port = 0
        self.__image_size = 255
        self.seed = None

        self.__dispatcher = {
            gadu.GGMsg_Welcome: welcome_callback,
            gadu.GGMsg_LoginOk: loginok_callback
        }

    def sendPacket(self, msg):
        self.transport.write( msg )

    def connectionMade(self):
        Protocol.connectionMade(self)
        self._conn = self.factory._conn
        self.__contacts_list = self.factory._conn.contacts_list
        #self.sendPacket("Hello, world!")
        #self.sendPacket("What a fine day it is.")
        #self.sendPacket(self.end)

    def dataReceived(self, data):
        print 'received data: ', data
        header, rem = GGPacketHeader.unpack(data)
        msg_class = GG_Inbound[header.msg_type]

        # unpack the message
        msg, rem = msg_class.unpack(rem)
        try:
            self.__dispatcher[msg_class](header, msg, rem)
        except Exception, e:
            print e

    def welcome_callback(self, hdr, msg, extra):
        self.seed = msg.seed

        # this does something ?
        d = defer.Deferred()
        d.callback(self.seed)
        d.addCallback(self._conn.on_auth_got_seed)

        self._login()

    def loginok_callback(self, hdr, msg, extra):
        d = defer.Deferred()
        d.callback(None)
        d.addCallback(self._conn.on_authorised)
        self._send_contacts_list()
        self._ping()

    def userlist_callback(self, hdr, msg, extra):
        print 'packet: GGUserListReply'
        d = defer.Deferred()
        d.callback(None)
        d.addCallback(self.on_userlistreply)

    def _login(self, seed):
        print '_login'
        login_msg = GGMsg80_Login(uin=self.__uin)
        login_msg.update_hash(self.password, self.status)

        self.sendPacket( login_msg.as_packet(GG_Outbound.key_for(GGMsg80_Login)) )

    x = """        header = GGHeader()
	header.read(data)
        print 'header.type: ', header.type
#        self.factory.clientReady(self)
	if header.type == GGIncomingPackets.GGWelcome:
            print 'packet: GGWelcome'
            in_packet = GGWelcome()
            in_packet.read(data, header.length)
            self.seed = in_packet.seed
            d = defer.Deferred()
            d.callback(self)
            d.addCallback(self._conn.on_auth_got_seed, self.seed)
            d = None
        elif header.type == GGIncomingPackets.GGLoginOK:
            print 'packet: GGLoginOK'
            d = defer.Deferred()
            d.callback(self)
            d.addCallback(self._conn.on_login_ok)
            self._send_contacts_list()
            print 'wyslano liste kontaktow'
            self._ping()
        elif header.type == GGIncomingPackets.GGLoginFailed:
            print 'packet: GGLoginFailed'
            d = defer.Deferred()
            d.callback(self)
            d.addCallback(self._conn.on_login_failed)
        elif header.type == GGIncomingPackets.GGNeedEMail:
            print 'packet: GGNeedEMail'
            d = defer.Deferred()
            d.callback(self)
            d.addCallback(self._conn.on_need_email)
        elif header.type == GGIncomingPackets.GGDisconnecting:
            print 'packet: GGDisconnecting'
            in_packet = GGDisconnecting()
            in_packet.read(data, header.length)
            d = defer.Deferred()
            d.callback(self)
            d.addCallback(self._conn.on_disconnecting)
        elif header.type == GGIncomingPackets.GGNotifyReply60 or header.type == GGIncomingPackets.GGNotifyReply77:
            in_packet = GGNotifyReply(self.__contacts_list, header.type)
            in_packet.read(data, header.length)
            self.__contacts_list = in_packet.contacts
            d = defer.Deferred()
            d.callback(self)
            d.addCallback(self._conn.on_notify_reply, self.__contacts_list)
        elif header.type == GGIncomingPackets.GGUserListReply:
            print 'packet: GGUserListReply'
            d = defer.Deferred()
            d.callback(None)
            d.addCallback(self.on_userlist_reply)
        else:
            print 'packet: unknown: type %s, length %s' % (header.type, header.length)
"""

    def _send_contacts_list(self):
        """
        Wysyla do serwera nasza liste kontaktow w celu otrzymania statusow.
        Powinno byc uzyte zaraz po zalogowaniu sie do serwera.
        UWAGA: To nie jest eksport listy kontaktow do serwera!
        """
        assert self.__contacts_list  == None or type(self.__contacts_list) == ContactsList
        print 'czas wyslac nasza liste kontaktow :D'
        if self.__contacts_list == None or len(self.__contacts_list) == 0:
            print 'yupp. wysylamy pusta liste kontaktow'
            out_packet = GGListEmpty()
            self.sendPacket(out_packet.get())
            return

        uin_type_list = [] # [(uin, type), (uin, type), ...]
        for contact in self.__contacts_list.data: #TODO: brrrrrrr, nie .data!!!!
            uin_type_list.append((contact.uin, contact.user_type))
        sub_lists = Helpers.split_list(uin_type_list, 400)

        for l in sub_lists[:-1]: #zostawiamy ostatnia podliste
            out_packet = GGNotifyFirst(l)
            self.sendPacket(out_packet.get())
        # zostala juz ostatnia lista do wyslania
        out_packet = GGNotifyLast(sub_lists[-1])
        self.sendPacket(out_packet.get())

    def _ping(self):
        """
        Metoda wysyla pakiet GGPing do serwera
        """
        out_packet = GGPing()
        self.sendPacket(out_packet.get())
        print "[PING]"
        reactor.callLater(96, self._ping)

    """Methods that can be used by user"""
    def login(self, seed, uin, password, status, desc):
        self.uin = uin
        self.password = password
        self.status = status
        self.desc = desc
    	out_packet = GGLogin(self.uin, self.password, self.status, seed, self.desc, self.__local_ip, \
                            self.__local_port, self.__external_ip, self.__external_port, self.__image_size)
        self.sendPacket(out_packet.get())

    def change_status(self, status, description = ""):
            """
            Metoda powoduje zmiane statusu i opisu. Jako parametry przyjmuje nowy status i nowy opis (domyslnie - opis pusty).
            """
            assert type(status) == types.IntType and status in GGStatuses
            assert type(description) == types.StringType and len(description) <= 70

            out_packet  = GGNewStatus(status, description)
            self.sendPacket(out_packet.get())
            self.status = status
            self.desc = description

    def get_actual_status(self):
        return self.status


    def get_actual_status_desc(self):
        return self.desc

class GGClientFactory(ClientFactory):
    protocol = GGClient
    def __init__(self, conn):
        self._conn = conn

    def startedConnecting(self, connector):
	print 'connection started'

    def clientConnectionFailed(self, connector, reason):
        print 'connection failed:', reason.getErrorMessage()
        reactor.stop()

    def clientConnectionLost(self, connector, reason):
        print 'connection lost:', reason.getErrorMessage()
        reactor.stop()

    def buildProtocol(self, addr):
      p = self.protocol()
      p.factory = self
      p.factory.instance = p
      return p

