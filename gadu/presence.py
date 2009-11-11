# telepathy-butterfly - an MSN connection manager for Telepathy
#
# Copyright (C) 2006-2007 Ali Sabil <ali.sabil@gmail.com>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA

# Implementation of the SimplePresence specification at :
# http://telepathy.freedesktop.org/spec.html#org.freedesktop.Telepathy.Connection.Interface.SimplePresence

import logging
import time

import dbus
import telepathy
import telepathy.constants
import telepathy.errors
#import papyon

from gadu.handle import GaduHandleFactory
from gadu.util.decorator import async

__all__ = ['GaduPresence']

logger = logging.getLogger('Gadu.Presence')


class GaduPresenceMapping(object):
    ONLINE = 'available'
    FFC  = 'free_for_chat'
    BUSY = 'busy'
    IDLE = 'dnd'
    INVISIBLE = 'hidden'
    OFFLINE = 'offline'

    to_gg = {
            ONLINE:     'AVAILBLE',
            BUSY:       'BUSY',
            IDLE:       'DND',
            INVISIBLE:  'HIDDEN',
            OFFLINE:    'NOT_AVAILBLE'
            }

    to_telepathy = {
            'AVAILBLE':                 ONLINE,
            'FFC':                      FFC,
            'BUSY':                     BUSY,
            'DND':                      IDLE,
            'HIDDEN':                   INVISIBLE,
            'NOT_AVAILBLE':             OFFLINE
            }

    from_gg_to_tp = {
#        'NOT_AVAILBLE':         0x0001,
#        'NOT_AVAILBLE_DESC':    0x0015,
#        'FFC':                  0x0017,
#        'FFC_DESC':             0x0018,
#        'AVAILBLE':             0x0002,
#        'AVAILBLE_DESC':        0x0004,
#        'BUSY':                 0x0003,
#        'BUSY_DESC':            0x0005,
#        'DND':                  0x0021,
#        'DND_DESC':             0x0022,
#        'HIDDEN':               0x0014,
#        'HIDDEN_DESC':          0x0016,
#        'DND':                  0x0021,
#        'BLOCKED':              0x0006,
#        'MASK_FRIEND':          0x8000,
#        'MASK_GFX':             0x0100,
#        'MASK_STATUS':          0x4000,
            0:                          OFFLINE,
            0x0001:                     OFFLINE,
            0x4015:                     OFFLINE,
            0x0017:                     ONLINE,
            0x4018:                     ONLINE,
            0x0002:                     ONLINE,
            0x4004:                     ONLINE,
            0x0003:                     BUSY,
            0x4005:                     BUSY,
            0x0021:                     IDLE,
            0x4022:                     IDLE,
            0x0014:                     INVISIBLE,
            0x4016:                     INVISIBLE
    }

    to_presence_type = {
            ONLINE:     telepathy.constants.CONNECTION_PRESENCE_TYPE_AVAILABLE,
            FFC:     telepathy.constants.CONNECTION_PRESENCE_TYPE_AVAILABLE,
            BUSY:       telepathy.constants.CONNECTION_PRESENCE_TYPE_BUSY,
            IDLE:       telepathy.constants.CONNECTION_PRESENCE_TYPE_EXTENDED_AWAY,
            INVISIBLE:  telepathy.constants.CONNECTION_PRESENCE_TYPE_HIDDEN,
            OFFLINE:    telepathy.constants.CONNECTION_PRESENCE_TYPE_OFFLINE
            }

class GaduPresence(telepathy.server.ConnectionInterfacePresence,
        telepathy.server.ConnectionInterfaceSimplePresence):

    def __init__(self):
        telepathy.server.ConnectionInterfacePresence.__init__(self)
        telepathy.server.ConnectionInterfaceSimplePresence.__init__(self)
#        papyon.event.ContactEventInterface.__init__(self, self.msn_client)
#        papyon.event.ProfileEventInterface.__init__(self, self.msn_client)

        dbus_interface = 'org.freedesktop.Telepathy.Connection.Interface.SimplePresence'

        self._implement_property_get(dbus_interface, {'Statuses' : self.get_statuses})


    def GetStatuses(self):
        # the arguments are in common to all on-line presences
        arguments = {'message' : 's'}

        # you get one of these for each status
        # {name:(type, self, exclusive, {argument:types}}
        return {
            GaduPresenceMapping.ONLINE:(
                telepathy.CONNECTION_PRESENCE_TYPE_AVAILABLE,
                True, True, arguments),
            GaduPresenceMapping.BUSY:(
                telepathy.CONNECTION_PRESENCE_TYPE_BUSY,
                True, True, arguments),
            GaduPresenceMapping.IDLE:(
                telepathy.CONNECTION_PRESENCE_TYPE_EXTENDED_AWAY,
                True, True, arguments),
            GaduPresenceMapping.INVISIBLE:(
                telepathy.CONNECTION_PRESENCE_TYPE_HIDDEN,
                True, True, {}),
            GaduPresenceMapping.OFFLINE:(
                telepathy.CONNECTION_PRESENCE_TYPE_OFFLINE,
                True, True, {})
        }

    def RequestPresence(self, contacts):
        presences = self.get_presences(contacts)
        self.PresenceUpdate(presences)

    def GetPresence(self, contacts):
        return self.get_presences(contacts)

    def SetStatus(self, statuses):
        status, arguments = statuses.items()[0]
        if status == GaduPresenceMapping.OFFLINE:
            self.Disconnect()

        print "SetStatus emitted"

        presence = GaduPresenceMapping.to_gg[status]
        message = arguments.get('message', u'')

        logger.info("Setting Presence to '%s'" % presence)
        logger.info("Setting Personal message to '%s'" % message)

        message.encode("utf-8")

        if self._status != telepathy.CONNECTION_STATUS_CONNECTED:
            self._initial_presence = presence
            self._initial_personal_message = message
        else:
            self.msn_client.profile.personal_message = message
            self.msn_client.profile.presence = presence

    def get_presences(self, contacts):
        presences = {}
        for handle_id in contacts:
            handle = self.handle(telepathy.HANDLE_TYPE_CONTACT, handle_id)
#            try:
#                contact = handle.contact
#            except AttributeError:
#                contact = handle.profile
#
#            if contact is not None:
#                presence = ButterflyPresenceMapping.to_telepathy[contact.presence]
#                personal_message = unicode(contact.personal_message, "utf-8")
#            else:
#                presence = GaduPresenceMapping.OFFLINE
#                personal_message = u""
            try:
                contact = handle.profile
                presence = GaduPresenceMapping.OFFLINE
                personal_message = u""
            except AttributeError:
                #I dont know what to do here. Do I really need this? :P
                contact = handle.contact
                print "get_simple_presences, contact uin: %s, status: %s, desc: %s" % (contact.uin, contact.status, contact.description)
                if contact is not None:
                    presence = GaduPresenceMapping.to_telepathy[contact.status]
                    personal_message = unicode(contact.description, "utf-8")
                else:
                    presence = GaduPresenceMapping.OFFLINE
                    personal_message = u""

            arguments = {}
            if personal_message:
                arguments = {'message' : personal_message}

            presences[handle] = (0, {presence : arguments}) # TODO: Timestamp
        return presences


    # SimplePresence

    def GetPresences(self, contacts):
        return self.get_simple_presences(contacts)

    def SetPresence(self, status, message):
        if status == GaduPresenceMapping.OFFLINE:
            self.Disconnect()

        print "SetStatus status: %s" % (status)

        try:
            presence = GaduPresenceMapping.to_gg[status]
        except KeyError:
            raise telepathy.errors.InvalidArgument

        logger.info("Setting Presence to '%s'" % presence)
        logger.info("Setting Personal message to '%s'" % message)

        message = message.encode("utf-8")

        if self._status != telepathy.CONNECTION_STATUS_CONNECTED:
            self._initial_presence = presence
            self._initial_personal_message = message
        else:
            self.profile.setMyState(presence, message)
            
    def get_simple_presences(self, contacts):
        presences = {}
        for handle_id in contacts:
            handle = self.handle(telepathy.HANDLE_TYPE_CONTACT, handle_id)
            try:
                contact = handle.profile
                presence = GaduPresenceMapping.OFFLINE
                personal_message = u""
            except AttributeError:
                #I dont know what to do here. Do I really need this? :P
                contact = handle.contact
                #print "get_simple_presences, contact uin: %s, status: %x, desc: %s" % (contact.uin, contact.status, contact.description)
                if contact is not None:
                    #print "Contact status: %s" % (contact.status)
                    presence = GaduPresenceMapping.from_gg_to_tp[contact.status]
                    personal_message = unicode(contact.description, "utf-8")
                else:
                    presence = GaduPresenceMapping.OFFLINE
                    personal_message = u""

#            if contact is not None:
#
#                presence = ButterflyPresenceMapping.to_telepathy[contact.presence]
#                personal_message = unicode(contact.personal_message, "utf-8")
#            else:
#                presence = ButterflyPresenceMapping.OFFLINE
#                personal_message = u""

            presence_type = GaduPresenceMapping.to_presence_type[presence]

            presences[handle] = (presence_type, presence, personal_message)
        return presences

    def get_statuses(self):
        # you get one of these for each status
        # {name:(Type, May_Set_On_Self, Can_Have_Message}
        return dbus.Dictionary({
            GaduPresenceMapping.ONLINE:(
                telepathy.CONNECTION_PRESENCE_TYPE_AVAILABLE,
                True, True),
            GaduPresenceMapping.BUSY:(
                telepathy.CONNECTION_PRESENCE_TYPE_BUSY,
                True, True),
            GaduPresenceMapping.IDLE:(
                telepathy.CONNECTION_PRESENCE_TYPE_EXTENDED_AWAY,
                True, True),
            GaduPresenceMapping.INVISIBLE:(
                telepathy.CONNECTION_PRESENCE_TYPE_HIDDEN,
                True, True),
            GaduPresenceMapping.OFFLINE:(
                telepathy.CONNECTION_PRESENCE_TYPE_OFFLINE,
                True, True)
        }, signature='s(ubb)')

    # papyon.event.ContactEventInterface
    def on_contact_presence_changed(self, contact):
        handle = ButterflyHandleFactory(self, 'contact',
                contact.account, contact.network_id)
        logger.info("Contact %s presence changed to '%s'" % (unicode(handle),
            contact.presence))
        self._presence_changed(handle, contact.presence, contact.personal_message)

    # papyon.event.ContactEventInterface
    on_contact_personal_message_changed = on_contact_presence_changed

    # papyon.event.ProfileEventInterface
    def on_profile_presence_changed(self):
        profile = self.msn_client.profile
        self._presence_changed(ButterflyHandleFactory(self, 'self'),
                profile.presence, profile.personal_message)

    # papyon.event.ProfileEventInterface
    on_profile_personal_message_changed = on_profile_presence_changed

    @async
    def _presence_changed(self, handle, presence, personal_message):
        try:
            presence = GaduPresenceMapping.from_gg_to_tp[presence]
        except KeyError:
            presence = GaduPresenceMapping.from_gg_to_tp[presence]
        presence_type = GaduPresenceMapping.to_presence_type[presence]
        personal_message = unicode(str(personal_message.text), "utf-8")

        self.PresencesChanged({handle: (presence_type, presence, personal_message)})

        arguments = {}
        if personal_message:
            arguments = {'message' : personal_message}

        self.PresenceUpdate({handle: (int(time.time()), {presence:arguments})})
