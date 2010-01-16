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

import logging
import weakref
import time

import telepathy

from sunshine.util.decorator import async
from sunshine.handle import SunshineHandleFactory

__all__ = ['SunshineTextChannel']

logger = logging.getLogger('Sunshine.TextChannel')


class SunshineTextChannel(telepathy.server.ChannelTypeText):

    def __init__(self, conn, manager, conversation, props):
        _, surpress_handler, handle = manager._get_type_requested_handle(props)
        self._recv_id = 0
        self._conn_ref = weakref.ref(conn)
        self.conn = conn

        self.contact = handle.contact

        telepathy.server.ChannelTypeText.__init__(self, conn, manager, props)

    def Send(self, message_type, text):
        if message_type == telepathy.CHANNEL_TEXT_MESSAGE_TYPE_NORMAL:
            logger.info("Sending message : %s" % unicode(text))
            msg = text.encode('windows-1250')
            self.conn.gadu_client.sendTo(int(self.contact.uin), str(text), str(msg))
        else:
            raise telepathy.NotImplemented("Unhandled message type")
        self.Sent(int(time.time()), message_type, text)

    def Close(self):
        telepathy.server.ChannelTypeText.Close(self)
        self.remove_from_connection()

    # Redefine GetSelfHandle since we use our own handle
    #  as Butterfly doesn't have channel specific handles
    def GetSelfHandle(self):
        return self._conn.GetSelfHandle()

    # Rededefine AcknowledgePendingMessages to remove offline messages
    # from the oim box.
    def AcknowledgePendingMessages(self, ids):
        telepathy.server.ChannelTypeText.AcknowledgePendingMessages(self, ids)
#        messages = []
#        for id in ids:
#            if id in self._pending_offline_messages.keys():
#                messages.append(self._pending_offline_messages[id])
#                del self._pending_offline_messages[id]
#        self._oim_box_ref().delete_messages(messages)

    # Rededefine ListPendingMessages to remove offline messages
    # from the oim box.
    def ListPendingMessages(self, clear):
        return telepathy.server.ChannelTypeText.ListPendingMessages(self, clear)


#        if clear:
#            messages = self._pending_offline_messages.values()
#            self._oim_box_ref().delete_messages(messages)
#        return telepathy.server.ChannelTypeText.ListPendingMessages(self, clear)
#
#    # papyon.event.ConversationEventInterface
#    def on_conversation_user_joined(self, contact):
#        handle = ButterflyHandleFactory(self._conn_ref(), 'contact',
#                contact.account, contact.network_id)
#        logger.info("User %s joined" % unicode(handle))
#        if handle not in self._members:
#            self.MembersChanged('', [handle], [], [], [],
#                    handle, telepathy.CHANNEL_GROUP_CHANGE_REASON_INVITED)
#
#    # papyon.event.ConversationEventInterface
#    def on_conversation_user_left(self, contact):
#        handle = ButterflyHandleFactory(self._conn_ref(), 'contact',
#                contact.account, contact.network_id)
#        logger.info("User %s left" % unicode(handle))
#        # There was only us and we are leaving, is it necessary?
#        if len(self._members) == 1:
#            self.ChatStateChanged(handle, telepathy.CHANNEL_CHAT_STATE_GONE)
#        elif len(self._members) == 2:
#            # Add the last user who left as the offline contact so we may still send
#            # him offlines messages and destroy the conversation
#            self._conversation.leave()
#            self._conversation = None
#            self._offline_handle = handle
#            self._offline_contact = contact
#        else:
#            #If there is only us and a offline contact don't remove him from
#            #the members since we still send him messages
#            self.MembersChanged('', [], [handle], [], [],
#                    handle, telepathy.CHANNEL_GROUP_CHANGE_REASON_NONE)
#
#    # papyon.event.ConversationEventInterface
#    def on_conversation_user_typing(self, contact):
#        handle = ButterflyHandleFactory(self._conn_ref(), 'contact',
#                contact.account, contact.network_id)
#        logger.info("User %s is typing" % unicode(handle))
#        self.ChatStateChanged(handle, telepathy.CHANNEL_CHAT_STATE_COMPOSING)
#
#    # papyon.event.ConversationEventInterface
#    def on_conversation_message_received(self, sender, message):
#        id = self._recv_id
#        timestamp = int(time.time())
#        handle = ButterflyHandleFactory(self._conn_ref(), 'contact',
#                sender.account, sender.network_id)
#        type = telepathy.CHANNEL_TEXT_MESSAGE_TYPE_NORMAL
#        message = message.content
#        logger.info("User %s sent a message" % unicode(handle))
#        self.Received(id, timestamp, handle, type, 0, message)
#        self._recv_id += 1
#
#    # papyon.event.ConversationEventInterface
#    def on_conversation_nudge_received(self, sender):
#        id = self._recv_id
#        timestamp = int(time.time())
#        handle = ButterflyHandleFactory(self._conn_ref(), 'contact',
#                sender.account, sender.network_id)
#        type = telepathy.CHANNEL_TEXT_MESSAGE_TYPE_ACTION
#        text = unicode("sends you a nudge", "utf-8")
#        logger.info("User %s sent a nudge" % unicode(handle))
#        self.Received(id, timestamp, handle, type, 0, text)
#        self._recv_id += 1
#
#    # papyon.event.ContactEventInterface
#    def on_contact_presence_changed(self, contact):
#        handle = ButterflyHandleFactory(self._conn_ref(), 'contact',
#                contact.account, contact.network_id)
#        # Recreate a conversation if our contact join
#        if self._offline_contact == contact and contact.presence != papyon.Presence.OFFLINE:
#            logger.info('Contact %s connected, inviting him to the text channel' % unicode(contact))
#            client = self._conn_ref().msn_client
#            self._conversation = papyon.Conversation(client, [contact])
#            papyon.event.ConversationEventInterface.__init__(self, self._conversation)
#            self._offline_contact = None
#            self._offline_handle = None
#        #FIXME : I really hope there is no race condition between the time
#        # the contact accept the invitation and the time we send him a message
#        # Can a user refuse an invitation? what happens then?
#
#
#    # Public API
#    def offline_message_received(self, message):
#        # @message a papyon.OfflineIM.OfflineMessage
#        id = self._recv_id
#        sender = message.sender
#        timestamp = time.mktime(message.date.timetuple())
#        text = message.text
#
#        # Map the id to the offline message so we can remove it
#        # when acked by the client
#        self._pending_offline_messages[id] = message
#
#        handle = ButterflyHandleFactory(self._conn_ref(), 'contact',
#                sender.account, sender.network_id)
#        type = telepathy.CHANNEL_TEXT_MESSAGE_TYPE_NORMAL
#        logger.info("User %r sent a offline message" % handle)
#        self.Received(id, timestamp, handle, type, 0, text)
#
#        self._recv_id += 1
#
#    @async
#    def __add_initial_participants(self):
#        handles = []
#        handles.append(self._conn.GetSelfHandle())
#        if self._conversation:
#            for participant in self._conversation.participants:
#                handle = ButterflyHandleFactory(self._conn_ref(), 'contact',
#                        participant.account, participant.network_id)
#                handles.append(handle)
#        else:
#            handles.append(self._offline_handle)
#
#        self.MembersChanged('', handles, [], [], [],
#                0, telepathy.CHANNEL_GROUP_CHANGE_REASON_NONE)
