# telepathy-sunshine is the GaduGadu connection manager for Telepathy
#
# Copyright (C) 2006-2007 Ali Sabil <ali.sabil@gmail.com>
# Copyright (C) 2007 Johann Prieur <johann.prieur@gmail.com>
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

import logging, hashlib

import telepathy

import xml.etree.ElementTree as ET

from sunshine.lqsoft.pygadu.models import GaduProfile, GaduContact, GaduContactGroup

from sunshine.util.decorator import async
from sunshine.handle import SunshineHandleFactory
from sunshine.channel.contact_list import SunshineListChannel

__all__ = ['SunshineGroupChannel']

logger = logging.getLogger('Sunshine.GroupChannel')


class SunshineGroupChannel(SunshineListChannel):

    def __init__(self, connection, manager, props):
        self.__pending_add = []
        self.__pending_remove = []
        self.conn = connection
        self.groups = {}
        SunshineListChannel.__init__(self, connection, manager, props)
        self.GroupFlagsChanged(telepathy.CHANNEL_GROUP_FLAG_CAN_ADD | 
                telepathy.CHANNEL_GROUP_FLAG_CAN_REMOVE, 0)
        @async
        def create_group():
            if self._handle.group is None:
                name = self._handle.name
                for group in self.conn.profile.groups:
                    if group.Name != name:
                        h = hashlib.md5()
                        h.update(name)

                        group_xml = ET.Element("Group")
                        ET.SubElement(group_xml, "Id").text = h.hexdigest()
                        ET.SubElement(group_xml, "Name").text = name
                        ET.SubElement(group_xml, "IsExpanded").text = str('True')
                        ET.SubElement(group_xml, "IsRemovable").text = str('True')

                        g = GaduContactGroup.from_xml(group_xml)
                        self.conn.profile.addGroup(g)
                        
            for group in self.conn.profile.groups:
                self.groups[group.Id] = group.Name

            for contact in self.conn.profile.contacts:
                contact_groups = ET.fromstring(contact.Groups)
                if contact.Groups:
                    for group in contact_groups.getchildren():
                        if self.groups.has_key(group.text):
                            if self.groups[group.text] == self._handle.group.Name:
                                self.add_contact_to_group(self._handle.group, contact, None)
        create_group()


    def AddMembers(self, contacts, message):
        for contact_handle_id in contacts:
            contact_handle = self._conn.handle(telepathy.HANDLE_TYPE_CONTACT,
                        contact_handle_id)
            logger.info("Adding contact %s to group %s" %
                    (unicode(contact_handle), unicode(self._handle)))

            contact = contact_handle.contact
            group = self._handle.group

            self.add_contact_to_group(group, contact, contact_handle)


    def RemoveMembers(self, contacts, message):
        for contact_handle_id in contacts:
            contact_handle = self._conn.handle(telepathy.HANDLE_TYPE_CONTACT,
                        contact_handle_id)
            logger.info("Removing contact %s from pending group %s" %
                    (unicode(contact_handle), unicode(self._handle)))

            contact = contact_handle.contact
            group = self._handle.group

            self.delete_contact_from_group(group, contact, contact_handle)

    def Close(self):
        logger.debug("Deleting group %s" % self._handle.name)
        del self.conn.profile.groups[self._handle.name]
#        ab = self._conn.msn_client.address_book
#        group = self._handle.group
#        ab.delete_group(group)

#    def _filter_contact(self, contact):
#        if contact.is_member(papyon.Membership.FORWARD):
#            for group in contact.groups:
#                if group.name.decode("utf-8") == self._handle.name:
#                    return (True, False, False)
#        return (False, False, False)
#
#    def on_addressbook_group_added(self, group):
#        if group.name.decode("utf-8") == self._handle.name:
#            self.AddMembers(self.__pending_add, None)
#            self.__pending_add = []
#            self.RemoveMembers(self.__pending_remove, None)
#            self.__pending_remove = []
#
#    def on_addressbook_group_deleted(self, group):
#        if group.name.decode("utf-8") == self._handle.name:
#            self.Closed()
#            self._conn.remove_channel(self)
#
#    def on_addressbook_group_contact_added(self, group, contact):
#        group_name = group.name.decode("utf-8")
#        if group_name == self._handle.name:
#            handle = ButterflyHandleFactory(self._conn_ref(), 'contact',
#                    contact.account, contact.network_id)
#
#            added = set()
#            added.add(handle)
#
#            self.MembersChanged('', added, (), (), (), 0,
#                    telepathy.CHANNEL_GROUP_CHANGE_REASON_NONE)
#
#            logger.debug("Contact %s added to group %s" %
#                    (handle.name, group_name))
#
#    def on_addressbook_group_contact_deleted(self, group, contact):
#        group_name = group.name.decode("utf-8")
#        if group_name == self._handle.name:
#            handle = ButterflyHandleFactory(self._conn_ref(), 'contact',
#                    contact.account, contact.network_id)
#
#            removed = set()
#            removed.add(handle)
#
#            self.MembersChanged('', (), removed, (), (), 0,
#                    telepathy.CHANNEL_GROUP_CHANGE_REASON_NONE)
#
#            logger.debug("Contact %s removed from group %s" %
#                    (handle.name, group_name))
#

    @async
    def add_contact_to_group(self, group, contact, contact_handle):
        group_name = group.Name
        if group_name == self._handle.name:
            if hasattr(contact, 'uin'):
                contact_uin = contact.uin
            else:
                contact_uin = contact_handle.name

            handle = SunshineHandleFactory(self.conn, 'contact',
                    contact_uin, None)
            added = set()
            added.add(handle)

            if group.Name and group.Id:
                is_group = False

                contact_groups_xml = ET.Element("Groups")
                if hasattr(contact, 'Groups'):
                    contact_groups = ET.fromstring(contact.Groups)
                    for c_group in contact_groups.getchildren():
                        if c_group.text == group.Id:
                            is_group = True
                        ET.SubElement(contact_groups_xml, "GroupId").text = c_group.text
                if is_group != True:
                    ET.SubElement(contact_groups_xml, "GroupId").text = group.Id
                c_groups = ET.tostring(contact_groups_xml)

                if hasattr(contact, 'updateGroups'):
                    contact.updateGroups(c_groups)
                else:
                    self.conn.pending_contacts_to_group[contact_uin] = c_groups

            self.MembersChanged('', added, (), (), (), 0,
                    telepathy.CHANNEL_GROUP_CHANGE_REASON_NONE)

            logger.debug("Contact %s added to group %s" %
                    (handle.name, group_name))

    @async
    def delete_contact_from_group(self, group, contact, contact_handle):
        group_name = group.Name
        if group_name == self._handle.name:
            handle = SunshineHandleFactory(self.conn, 'contact',
                    contact.uin, None)
            removed = set()
            removed.add(handle)

            contact_groups_xml = ET.Element("Groups")
            contact_groups = ET.fromstring(contact.Groups)
            if contact.Groups:
                for c_group in contact_groups.getchildren():
                    if c_group.text != group.Id:
                        ET.SubElement(contact_groups_xml, "GroupId").text = c_group.text
            c_groups = ET.tostring(contact_groups_xml)

            contact.updateGroups(c_groups)

            self.MembersChanged('', (), removed, (), (), 0,
                    telepathy.CHANNEL_GROUP_CHANGE_REASON_NONE)

            logger.debug("Contact %s removed from group %s" %
                    (handle.name, group_name))
