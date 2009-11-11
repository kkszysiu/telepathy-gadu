# telepathy-butterfly - an MSN connection manager for Telepathy
#
# Copyright (C) 2007 Ali Sabil <ali.sabil@gmail.com>
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
import weakref

import telepathy
#import papyon

__all__ = ['GaduHandleFactory']

logger = logging.getLogger('Gadu.Handle')


def GaduHandleFactory(connection, type, *args):
    mapping = {'self': GaduSelfHandle,
               'contact': GaduContactHandle,
               'list': GaduListHandle,
               'group': GaduGroupHandle}
    handle = mapping[type](connection, *args)
    connection._handles[handle.get_type(), handle.get_id()] = handle
    return handle


class GaduHandleMeta(type):
    def __call__(cls, connection, *args):
        obj, newly_created = cls.__new__(cls, connection, *args)
        if newly_created:
            obj.__init__(connection, connection.get_handle_id(), *args)
            logger.info("New Handle %s" % unicode(obj))
        return obj 


class GaduHandle(telepathy.server.Handle):
    __metaclass__ = GaduHandleMeta

    instances = weakref.WeakValueDictionary()
    def __new__(cls, connection, *args):
        key = (cls, connection._account[0], args)
        if key not in cls.instances.keys():
            instance = object.__new__(cls, connection, *args)
            cls.instances[key] = instance # TRICKY: instances is a weakdict
            return instance, True
        return cls.instances[key], False

    def __init__(self, connection, id, handle_type, name):
        telepathy.server.Handle.__init__(self, id, handle_type, name)
        self._conn = weakref.proxy(connection)

    def __unicode__(self):
        type_mapping = {telepathy.HANDLE_TYPE_CONTACT : 'Contact',
                telepathy.HANDLE_TYPE_ROOM : 'Room',
                telepathy.HANDLE_TYPE_LIST : 'List',
                telepathy.HANDLE_TYPE_GROUP : 'Group'}
        type_str = type_mapping.get(self.type, '')
        return "<Gadu%sHandle id=%u name='%s'>" % \
            (type_str, self.id, self.name)

    id = property(telepathy.server.Handle.get_id)
    type = property(telepathy.server.Handle.get_type)
    name = property(telepathy.server.Handle.get_name)


class GaduSelfHandle(GaduHandle):
    instance = None

    def __init__(self, connection, id):
        handle_type = telepathy.HANDLE_TYPE_CONTACT
        handle_name = connection._account[0] + "#" + str("1")
        self._connection = connection
        GaduHandle.__init__(self, connection, id, handle_type, handle_name)

    @property
    def profile(self):
        #TODO: thats not required, it should be removed someday :)
        return False


class GaduContactHandle(GaduHandle):
    #TODO: GG using just UIN to indenrify user so we need just contact_uin instead of contact_account and contact_network)
    def __init__(self, connection, id, contact_account, contact_network):
        handle_type = telepathy.HANDLE_TYPE_CONTACT
        handle_name = str(contact_account)
        self.account = str(contact_account)
        self.network = contact_network
        self.pending_groups = set()
        self.pending_alias = None
        self._connection = connection
        GaduHandle.__init__(self, connection, id, handle_type, handle_name)

    @property
    def contact(self):
        print "GaduContactHandle %s" % (self.account)
        result = self._connection.gadu_client.get_contact(int(self.account))
        return result


class GaduListHandle(GaduHandle):
    def __init__(self, connection, id, list_name):
        handle_type = telepathy.HANDLE_TYPE_LIST
        handle_name = list_name
        GaduHandle.__init__(self, connection, id, handle_type, handle_name)


class GaduGroupHandle(GaduHandle):
    def __init__(self, connection, id, group_name):
        handle_type = telepathy.HANDLE_TYPE_GROUP
        handle_name = group_name
        GaduHandle.__init__(self, connection, id, handle_type, handle_name)

    @property
    def group(self):
        for group in self._conn.msn_client.address_book.groups:
            # Microsoft seems to like case insensitive stuff
            if group.name.decode("utf-8").lower() == self.name.lower():
                return group
        return None

