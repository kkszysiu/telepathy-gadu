# telepathy-butterfly - an MSN connection manager for Telepathy
#
# Copyright (C) 2009 Collabora Ltd.
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
import dbus

import telepathy
import papyon
import papyon.event

from butterfly.util.decorator import async
from butterfly.handle import ButterflyHandleFactory
from butterfly.media import ButterflySessionHandler

from telepathy.interfaces import CHANNEL_INTERFACE, CHANNEL_INTERFACE_GROUP

__all__ = ['ButterflyMediaChannel']

logger = logging.getLogger('Butterfly.MediaChannel')


class ButterflyMediaChannel(
        telepathy.server.ChannelTypeStreamedMedia,
        telepathy.server.ChannelInterfaceCallState,
        telepathy.server.ChannelInterfaceGroup,
        telepathy.server.ChannelInterfaceMediaSignalling,
        papyon.event.CallEventInterface,
        papyon.event.ContactEventInterface,
        papyon.event.MediaSessionEventInterface):

    def __init__(self, conn, manager, call, handle, props):
        telepathy.server.ChannelTypeStreamedMedia.__init__(self, conn, manager, props)
        telepathy.server.ChannelInterfaceCallState.__init__(self)
        telepathy.server.ChannelInterfaceGroup.__init__(self)
        telepathy.server.ChannelInterfaceMediaSignalling.__init__(self)
        papyon.event.CallEventInterface.__init__(self, call)
        papyon.event.ContactEventInterface.__init__(self, conn.msn_client)
        papyon.event.MediaSessionEventInterface.__init__(self, call.media_session)

        self._call = call
        self._handle = handle

        self._implement_property_get(CHANNEL_INTERFACE, {
                'InitiatorHandle': lambda: dbus.UInt32(self._initiator.id),
                'InitiatorID': lambda: self._initiator.name
                })

        self._implement_property_get(CHANNEL_INTERFACE_GROUP,
            {'LocalPendingMembers': lambda: self.GetLocalPendingMembersWithInfo() })

        self._add_immutables({
                'InitiatorHandle': CHANNEL_INTERFACE,
                'InitiatorID': CHANNEL_INTERFACE,
                })

        if CHANNEL_INTERFACE + '.InitiatorHandle' in props:
            self._initiator = conn.handle(telepathy.HANDLE_TYPE_CONTACT,
                props[CHANNEL_INTERFACE + '.InitiatorHandle'])
        elif CHANNEL_INTERFACE + '.InitiatorID' in props:
            self._initiator = ButterflyHandleFactory(conn, 'contact',
                id=props[CHANNEL_INTERFACE + '.InitiatorHandle'])
        else:
            logger.warning('InitiatorID or InitiatorHandle not set on new channel')
            self._initiator = None

        self._session_handler = ButterflySessionHandler(self._conn, self, call.media_session)

        flags = (telepathy.CHANNEL_GROUP_FLAG_CAN_REMOVE |
                 telepathy.CHANNEL_GROUP_FLAG_MESSAGE_REMOVE |
                 telepathy.CHANNEL_GROUP_FLAG_MESSAGE_REJECT)
        self.GroupFlagsChanged(flags, 0)
        self.__add_initial_participants()

    def Close(self):
        logger.info("Channel closed by client")
        self._call.end()

    def GetSessionHandlers(self):
        return [(self._session_handler, self._session_handler.subtype)]

    def ListStreams(self):
        logger.info("List streams")
        streams = dbus.Array([], signature="a(uuuuuu)")
        for handler in self._session_handler.ListStreams():
            streams.append((handler.id, self._handle, handler.type,
                handler.state, handler.direction, handler.pending_send))
        return streams

    def RequestStreams(self, handle, types):
        logger.info("Request streams %r %r %r" % (handle, self._handle, types))
        if self._handle.get_id() == 0:
            self._handle = self._conn.handle(telepathy.HANDLE_TYPE_CONTACT, handle)

        streams = dbus.Array([], signature="a(uuuuuu)")
        for type in types:
            handler = self._session_handler.CreateStream(type, 3)
            handler.connect("state-changed", self.on_stream_state_changed)
            handler.connect("error", self.on_stream_error)
            streams.append((handler.id, self._handle, handler.type,
                handler.state, handler.direction, handler.pending_send))
        self._call.invite()
        return streams

    def RequestStreamDirection(self, id, direction):
        logger.info("Request stream direction %r %r" % (id, direction))
        # FIXME: Need to implement changing the stream direction
        #self._session_handler.GetStream(id).direction = direction

    def RemoveStreams(self, streams):
        logger.info("Remove streams %r" % streams)
        for id in streams:
            self._session_handler.RemoveStream(id)
        if not self._session_handler.HasStreams():
            self.Close()

    def GetSelfHandle(self):
        return self._conn.GetSelfHandle()

    def GetLocalPendingMembersWithInfo(self):
        info = dbus.Array([], signature="(uuus)")
        for member in self._local_pending:
            info.append((member, self._handle, 0, ''))
        return info

    def AddMembers(self, handles, message):
        logger.info("Add members %r: %s" % (handles, message))
        for handle in handles:
            print handle, self.GetSelfHandle()
            if handle == int(self.GetSelfHandle()):
                if self.GetSelfHandle() in self._local_pending:
                    self._call.accept()

    def RemoveMembers(self, handles, message):
        logger.info("Remove members %r: %s" % (handles, message))

    def RemoveMembersWithReason(self, handles, message, reason):
        logger.info("Remove members %r: %s (%i)" % (handles, message, reason))

    #papyon.event.call.CallEventInterface
    def on_call_accepted(self):
        self.on_call_answered(telepathy.MEDIA_STREAM_DIRECTION_BIDIRECTIONAL, 0)

    #papyon.event.call.CallEventInterface
    def on_call_rejected(self, response):
        self.on_call_answered(telepathy.MEDIA_STREAM_DIRECTION_NONE, 0)

    def on_call_answered(self, direction, pending_send):
        for handler in self._session_handler.ListStreams():
            handler.set_direction(direction, pending_send)
            self.StreamDirectionChanged(handler.id, direction, pending_send)

    #papyon.event.call.CallEventInterface
    def on_call_ended(self):
        logger.info("Call has ended")
        telepathy.server.ChannelTypeStreamedMedia.Close(self)
        self.remove_from_connection()
        self._session_handler.remove_from_connection()

    #papyon.event.media.MediaSessionEventInterface
    def on_stream_created(self, stream):
        if stream.created_locally:
            return # Stream handler is already existing

        logger.info("Media Stream created upon peer request")
        handler = self._session_handler.HandleStream(stream)
        handler.connect("state-changed", self.on_stream_state_changed)
        handler.connect("error", self.on_stream_error)

    #papyon.event.media.MediaSessionEventInterface
    def on_stream_added(self, stream):
        handler = self._session_handler.NewStream(stream)
        logger.info("Media Stream %i added" % handler.id)
        self.StreamAdded(handler.id, self._handle, handler.type)
        self.StreamDirectionChanged(handler.id, handler.direction,
                handler.pending_send)

    #papyon.event.media.MediaSessionEventInterface
    def on_stream_removed(self, stream):
        handler = self._session_handler.FindStream(stream)
        logger.info("Media Stream %i removed" % handler.id)
        self._session_handler.RemoveStream(handler.id)
        del handler

    #papyon.event.media.ContactEventInterface
    def on_contact_presence_changed(self, contact):
        if contact == self._call.peer and \
           contact.presence == papyon.Presence.OFFLINE:
            logger.info("%s is now offline, closing channel" % contact)
            self.Close()

    #StreamHandler event
    def on_stream_error(self, handler, error, message):
        self.StreamError(handler.id, error, message)
        self._call.media_session.remove_stream(handler.stream)

    #StreamHandler event
    def on_stream_state_changed(self, handler, state):
        self.StreamStateChanged(handler.id, state)

    def __add_initial_participants(self):
        added = []
        local_pending = []
        remote_pending = []

        if self._call.incoming:
            local_pending.append(self._conn.GetSelfHandle())
            added.append(self._handle)
        else:
            remote_pending.append(self._handle)
            added.append(self._conn.GetSelfHandle())

        self.MembersChanged('', added, [], local_pending, remote_pending,
                0, telepathy.CHANNEL_GROUP_CHANGE_REASON_NONE)
        self._call.ring()
