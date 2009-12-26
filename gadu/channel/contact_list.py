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

import logging
import weakref

import telepathy
#import papyon
#import papyon.event

import xml.etree.ElementTree as ET

from gadu.util.decorator import async
from gadu.handle import GaduHandleFactory

from gadu.lqsoft.pygadu.twisted_protocol import GaduClient
from gadu.lqsoft.pygadu.models import GaduProfile, GaduContact

__all__ = ['GaduContactListChannelFactory']

logger = logging.getLogger('Gadu.ContactListChannel')

class HandleMutex(object):
    def __init__(self):
        self._handles = set()
        self._keys = {}
        self._callbacks = {}

    def is_locked(self, handle):
        return (handle in self._handles)

    def is_owned(self, key, handle):
        return (handle in self._handles and self._keys[handle] == key)

    def lock(self, key, handle):
        if self.is_locked(handle):
            return False
        self._handles.add(handle)
        self._keys[handle] = key
        return True

    def unlock(self, key, handle):
        if not self.is_owned(key, handle):
            return
        self._handles.remove(handle)
        del self._keys[handle]
        callbacks = self._callbacks.get(handle, [])[:]
        self._callbacks[handle] = []
        for callback in callbacks:
            callback[0](*callback[1:])

    def add_callback(self, key, handle, callback):
        if self.is_owned(key, handle):
            return
        if not self.is_locked(handle):
            callback[0](*callback[1:])
        else:
            self._callbacks.setdefault(handle, []).append(callback)

class Lockable(object):
    def __init__(self, mutex, key, cb_name):
        self._mutex = mutex
        self._key = key
        self._cb_name = cb_name

    def __call__(self, func):
        def method(object, handle, *args, **kwargs):
            def finished_cb(*user_data):
                self._mutex.unlock(self._key, handle)

            def unlocked_cb():
                self._mutex.lock(self._key, handle)
                kwargs[self._cb_name] = finished_cb
                if func(object, handle, *args, **kwargs):
                    finished_cb()

            self._mutex.add_callback(self._key, handle, (unlocked_cb,))

        return method

mutex = HandleMutex()


def GaduContactListChannelFactory(connection, manager, handle, props):
    handle = connection.handle(
        props[telepathy.CHANNEL_INTERFACE + '.TargetHandleType'],
        props[telepathy.CHANNEL_INTERFACE + '.TargetHandle'])

    if handle.get_name() == 'subscribe':
        channel_class = GaduSubscribeListChannel
    #hacky & tricky
#    elif handle.get_name() == 'publish':
#        channel_class = GaduSubscribeListChannel

#    elif handle.get_name() == 'publish':
#        channel_class = ButterflyPublishListChannel
#    elif handle.get_name() == 'hide':
#        channel_class = ButterflyHideListChannel
#    elif handle.get_name() == 'allow':
#        channel_class = ButterflyAllowListChannel
#    elif handle.get_name() == 'deny':
#        channel_class = ButterflyDenyListChannel
    else:
        raise TypeError("Unknown list type : " + handle.get_name())
    return channel_class(connection, manager, props)


class GaduListChannel(
        telepathy.server.ChannelTypeContactList,
        telepathy.server.ChannelInterfaceGroup):
    "Abstract Contact List channels"

    def __init__(self, connection, manager, props):
        self._conn_ref = weakref.ref(connection)
        telepathy.server.ChannelTypeContactList.__init__(self, connection, manager, props)
        telepathy.server.ChannelInterfaceGroup.__init__(self)
        self._populate(connection)

    def GetLocalPendingMembersWithInfo(self):
        return []

    # papyon.event.AddressBookEventInterface
    def on_addressbook_contact_added(self, contact):
        added = set()
        local_pending = set()
        remote_pending = set()

        ad, lp, rp = self._filter_contact(contact)
        if ad or lp or rp:
            handle = ButterflyHandleFactory(self._conn_ref(), 'contact',
                contact.account, contact.network_id)
            if ad: added.add(handle)
            if lp: local_pending.add(handle)
            if rp: remote_pending.add(handle)
            msg = contact.attributes.get('invite_message', '')
            self.MembersChanged(msg, added, (), local_pending, remote_pending, 0,
                    telepathy.CHANNEL_GROUP_CHANGE_REASON_NONE)

    # papyon.event.AddressBookEventInterface
    def on_addressbook_contact_deleted(self, contact):
        handle = ButterflyHandleFactory(self._conn_ref(), 'contact',
                contact.account, contact.network_id)
        ad, lp, rp = self._filter_contact(contact)
        if self._contains_handle(handle) and not ad:
            self.MembersChanged('', (), [handle], (), (), 0,
                    telepathy.CHANNEL_GROUP_CHANGE_REASON_NONE)

    # papyon.event.AddressBookEventInterface
    def on_addressbook_contact_blocked(self, contact):
        pass

    # papyon.event.AddressBookEventInterface
    def on_addressbook_contact_unblocked(self, contact):
        pass

    @async
    def _populate(self, connection):
        added = set()
        local_pending = set()
        remote_pending = set()

        for contact in connection.gadu_client.contacts:
            #logger.info("New contact %s, name: %s added." % (contact.uin, contact.ShowName))
            ad, lp, rp = self._filter_contact(contact)
            if ad or lp or rp:
                handle = GaduHandleFactory(self._conn_ref(), 'contact',
                        contact.uin, None)
                if ad: added.add(handle)
                if lp: local_pending.add(handle)
                if rp: remote_pending.add(handle)
        self.MembersChanged('', added, (), local_pending, remote_pending, 0,
                telepathy.CHANNEL_GROUP_CHANGE_REASON_NONE)

    def _filter_contact(self, contact):
        return (False, False, False)

    def _contains_handle(self, handle):
        members, local_pending, remote_pending = self.GetAllMembers()
        return (handle in members) or (handle in local_pending) or \
                (handle in remote_pending)


class GaduSubscribeListChannel(GaduListChannel):
    """Subscribe List channel.

    This channel contains the list of contact to whom the current used is
    'subscribed', basically this list contains the contact for whom you are
    supposed to receive presence notification."""

    def __init__(self, connection, manager, props):
        GaduListChannel.__init__(self, connection, manager, props)
        #papyon.event.ContactEventInterface.__init__(self, connection.msn_client)
        self.GroupFlagsChanged(telepathy.CHANNEL_GROUP_FLAG_CAN_ADD |
                telepathy.CHANNEL_GROUP_FLAG_CAN_REMOVE, 0)

    def AddMembers(self, contacts, message):
        logger.info("Subscribe - AddMembers called")
        for h in contacts:
            handle = self._conn.handle(telepathy.constants.HANDLE_TYPE_CONTACT, h)
            contact_xml = ET.Element("Contact")
            ET.SubElement(contact_xml, "Guid").text = str(handle.name)
            ET.SubElement(contact_xml, "GGNumber").text = str(handle.name)
            ET.SubElement(contact_xml, "ShowName").text = str(handle.name)
            ET.SubElement(contact_xml, "Groups")
            c = GaduContact.from_xml(contact_xml)
            self._conn_ref().gadu_client.addContact( c )
            #config.addNewContact( c )
            self._conn_ref().gadu_client.notifyAboutContact( c )
            logger.info("Adding contact: %s" % (handle.name))
            self.MembersChanged('', [handle], (), (), (), 0,
                    telepathy.CHANNEL_GROUP_CHANGE_REASON_INVITED)

            logger.info("Contact added.")

#        logger.info("Subscribe - Add Members called.")
#        handle = self._conn.handle(telepathy.HANDLE_TYPE_CONTACT, handle_id)
#        if handle.contact is not None and \
#           handle.contact.is_member(papyon.Membership.FORWARD):
#            return True
#
#        account = handle.account
#        network = handle.network
#        groups = list(handle.pending_groups)

    def RemoveMembers(self, contacts, message):
        for h in contacts:
            self._remove(h)

    def _filter_contact(self, contact):
        return (True, False, False)
        #return (contact.is_member(papyon.Membership.FORWARD) and not
        #        contact.is_member(papyon.Membership.PENDING), False, False)

    #@Lockable(mutex, 'add_subscribe', 'finished_cb')
#    def _add(self, handle_id, message, finished_cb):
#        logger.info("Subscribe - Add Members called.")
#        handle = self._conn.handle(telepathy.HANDLE_TYPE_CONTACT, handle_id)
#        if handle.contact is not None and \
#           handle.contact.is_member(papyon.Membership.FORWARD):
#            return True
#
#        account = handle.account
#        network = handle.network
#        groups = list(handle.pending_groups)
#        handle.pending_groups = set()
#        ab = self._conn.msn_client.address_book
#        ab.add_messenger_contact(account,
#                network_id=network,
#                auto_allow=False,
#                invite_message=message.encode('utf-8'),
#                groups=groups,
#                done_cb=(finished_cb,),
#                failed_cb=(finished_cb,))

    @Lockable(mutex, 'rem_subscribe', 'finished_cb')
    def _remove(self, handle_id, finished_cb):
        handle = self._conn.handle(telepathy.HANDLE_TYPE_CONTACT, handle_id)
        contact = handle.contact
        if contact is None or not contact.is_member(papyon.Membership.FORWARD):
            return True
        ab = self._conn.msn_client.address_book
        ab.delete_contact(contact, done_cb=(finished_cb,),
                failed_cb=(finished_cb,))

    # papyon.event.ContactEventInterface
    def on_contact_memberships_changed(self, contact):
        handle = ButterflyHandleFactory(self._conn_ref(), 'contact',
                contact.account, contact.network_id)
        if contact.is_member(papyon.Membership.FORWARD):
            self.MembersChanged('', [handle], (), (), (), 0,
                    telepathy.CHANNEL_GROUP_CHANGE_REASON_INVITED)
            if len(handle.pending_groups) > 0:
                ab = self._conn.msn_client.address_book
                for group in handle.pending_groups:
                    ab.add_contact_to_group(group, contact)
                handle.pending_groups = set()

#
#class ButterflyPublishListChannel(ButterflyListChannel,
#        papyon.event.ContactEventInterface):
#
#    def __init__(self, connection, manager, props):
#        ButterflyListChannel.__init__(self, connection, manager, props)
#        papyon.event.ContactEventInterface.__init__(self, connection.msn_client)
#        self.GroupFlagsChanged(0, 0)
#
#    def AddMembers(self, contacts, message):
#        for handle_id in contacts:
#            self._add(handle_id, message)
#
#    def RemoveMembers(self, contacts, message):
#        for handle_id in contacts:
#            self._remove(handle_id)
#
#    def GetLocalPendingMembersWithInfo(self):
#        result = []
#        for contact in self._conn.msn_client.address_book.contacts:
#            if not contact.is_member(papyon.Membership.PENDING):
#                continue
#            handle = ButterflyHandleFactory(self._conn_ref(), 'contact',
#                    contact.account, contact.network_id)
#            result.append((handle, handle,
#                    telepathy.CHANNEL_GROUP_CHANGE_REASON_INVITED,
#                    contact.attributes.get('invite_message', '')))
#        return result
#
#    def _filter_contact(self, contact):
#        return (contact.is_member(papyon.Membership.ALLOW),
#                contact.is_member(papyon.Membership.PENDING),
#                False)
#
#    @Lockable(mutex, 'add_publish', 'finished_cb')
#    def _add(self, handle_id, message, finished_cb):
#        handle = self._conn.handle(telepathy.HANDLE_TYPE_CONTACT, handle_id)
#        contact = handle.contact
#        if contact is not None and contact.is_member(papyon.Membership.ALLOW):
#            return True
#
#        account = handle.account
#        network = handle.network
#        ab = self._conn.msn_client.address_book
#        if contact is not None and contact.is_member(papyon.Membership.PENDING):
#            ab.accept_contact_invitation(contact, False,
#                    done_cb=(finished_cb,), failed_cb=(finished_cb,))
#        else:
#            ab.allow_contact(account, network,
#                    done_cb=(finished_cb,), failed_cb=(finished_cb,))
#
#    @Lockable(mutex, 'rem_publish', 'finished_cb')
#    def _remove(self, handle_id, finished_cb):
#        handle = self._conn.handle(telepathy.HANDLE_TYPE_CONTACT, handle_id)
#        contact = handle.contact
#        ab = self._conn.msn_client.address_book
#        if contact.is_member(papyon.Membership.PENDING):
#            ab.decline_contact_invitation(contact, False, done_cb=finished_cb,
#                    failed_cb=finished_cb)
#        elif contact.is_member(papyon.Membership.ALLOW):
#            ab.disallow_contact(contact, done_cb=(finished_cb,),
#                    failed_cb=(finished_cb,))
#        else:
#            return True
#
#    # papyon.event.ContactEventInterface
#    def on_contact_memberships_changed(self, contact):
#        handle = ButterflyHandleFactory(self._conn_ref(), 'contact',
#                contact.account, contact.network_id)
#        if self._contains_handle(handle):
#            if contact.is_member(papyon.Membership.PENDING):
#                # Nothing worth our attention
#                return
#
#            if contact.is_member(papyon.Membership.ALLOW):
#                # Contact accepted
#                self.MembersChanged('', [handle], (), (), (), 0,
#                        telepathy.CHANNEL_GROUP_CHANGE_REASON_INVITED)
#            else:
#                # Contact rejected
#                self.MembersChanged('', (), [handle], (), (), 0,
#                        telepathy.CHANNEL_GROUP_CHANGE_REASON_NONE)
