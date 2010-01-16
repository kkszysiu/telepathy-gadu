# telepathy-sunshine is the GaduGadu connection manager for Telepathy
#
# Copyright (C) 2009 Olivier Le Thanh Duong <olivier@lethanh.be>
# Copyright (C) 2010 Krzysztof Klinikowski <kkszysiu@gmail.com>
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


import logging
import time

import telepathy
import telepathy.errors
import dbus

__all__ = ['SunshineContacts']

logger = logging.getLogger('Sunshine.Contacts')

class SunshineContacts(telepathy.server.ConnectionInterfaceContacts):

    attributes = {
        telepathy.CONNECTION : 'contact-id',
        telepathy.CONNECTION_INTERFACE_SIMPLE_PRESENCE : 'presence',
        telepathy.CONNECTION_INTERFACE_ALIASING : 'alias',
        telepathy.CONNECTION_INTERFACE_AVATARS : 'token',
        telepathy.CONNECTION_INTERFACE_CAPABILITIES : 'caps'
        }

    def __init__(self):
        telepathy.server.ConnectionInterfaceContacts.__init__(self)

        dbus_interface = telepathy.CONNECTION_INTERFACE_CONTACTS

        self._implement_property_get(dbus_interface, \
                {'ContactAttributeInterfaces' : self.get_contact_attribute_interfaces})

    # Overwrite the dbus attribute to get the sender argument
    @dbus.service.method(telepathy.CONNECTION_INTERFACE_CONTACTS, in_signature='auasb',
                            out_signature='a{ua{sv}}', sender_keyword='sender')
    def GetContactAttributes(self, handles, interfaces, hold, sender):
        #InspectHandle already checks we're connected, the handles and handle type.
        for interface in interfaces:
            if interface not in self.attributes:
                raise telepathy.errors.InvalidArgument(
                    'Interface %s is not supported by GetContactAttributes' % (interface))

        handle_type = telepathy.HANDLE_TYPE_CONTACT
        ret = {}
        for handle in handles:
            ret[handle] = {}

        functions = {
            telepathy.CONNECTION :
                lambda x: zip(x, self.InspectHandles(handle_type, x)),
            telepathy.CONNECTION_INTERFACE_SIMPLE_PRESENCE :
                lambda x: self.GetPresences(x).items(),
            telepathy.CONNECTION_INTERFACE_ALIASING :
                lambda x: self.GetAliases(x).items(),
            telepathy.CONNECTION_INTERFACE_AVATARS :
                lambda x: self.GetKnownAvatarTokens(x).items(),
            telepathy.CONNECTION_INTERFACE_CAPABILITIES :
                lambda x: self.GetCapabilities(x).items()
            }

        #Hold handles if needed
        if hold:
            self.HoldHandles(handle_type, handles, sender)

        # Attributes from the interface org.freedesktop.Telepathy.Connection
        # are always returned, and need not be requested explicitly.
        interfaces = set(interfaces + [telepathy.CONNECTION])
        for interface in interfaces:
            interface_attribute = interface + '/' + self.attributes[interface]
            results = functions[interface](handles)
            for handle, value in results:
                ret[int(handle)][interface_attribute] = value
        return ret

    def get_contact_attribute_interfaces(self):
        return self.attributes.keys()
