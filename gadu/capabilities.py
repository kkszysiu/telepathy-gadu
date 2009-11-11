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
import dbus

import telepathy
#import papyon
#import papyon.event

from gadu.handle import GaduHandleFactory

__all__ = ['GaduCapabilities']

logger = logging.getLogger('Gadu.Capabilities')

class GaduCapabilities(telepathy.server.ConnectionInterfaceCapabilities):

    def __init__(self):
        telepathy.server.ConnectionInterfaceCapabilities.__init__(self)
#        papyon.event.ContactEventInterface.__init__(self, self.msn_client)
        dbus_interface = telepathy.CONNECTION_INTERFACE_CAPABILITIES

    def AdvertiseCapabilities(self, add, remove):
#        for caps, specs in add:
#            if caps == telepathy.CHANNEL_TYPE_STREAMED_MEDIA:
#                if specs & telepathy.CHANNEL_MEDIA_CAPABILITY_VIDEO:
#                    self._self_handle.profile.client_id.has_webcam = True
#                    self._self_handle.profile.client_id.supports_rtc_video = True
#        for caps in remove:
#            if caps == telepathy.CHANNEL_TYPE_STREAMED_MEDIA:
#                self._self_handle.profile.client_id.has_webcam = False

        return telepathy.server.ConnectionInterfaceCapabilities.\
            AdvertiseCapabilities(self, add, remove)

#    # papyon.event.ContactEventInterface
#    def on_contact_client_capabilities_changed(self, contact):
#        self._update_capabilities(contact)
#
#    def _update_capabilities(self, contact):
#        handle = ButterflyHandleFactory(self, 'contact',
#                contact.account, contact.network_id)
#        ctype = telepathy.CHANNEL_TYPE_STREAMED_MEDIA
#
#        new_gen, new_spec = self._get_capabilities(contact)
#        if handle in self._caps:
#            old_gen, old_spec = self._caps[handle][ctype]
#        else:
#            old_gen = 0
#            old_spec = 0
#
#        if old_gen == new_gen and old_spec == new_spec:
#            return
#
#        diff = (int(handle), ctype, old_gen, new_gen, old_spec, new_spec)
#        self.CapabilitiesChanged([diff])
#
#    def _get_capabilities(self, contact):
#        gen_caps = 0
#        spec_caps = 0
#
#        caps = contact.client_capabilities
#        if caps.supports_sip_invite:
#            gen_caps |= telepathy.CONNECTION_CAPABILITY_FLAG_CREATE
#            gen_caps |= telepathy.CONNECTION_CAPABILITY_FLAG_INVITE
#            spec_caps |= telepathy.CHANNEL_MEDIA_CAPABILITY_AUDIO
#            spec_caps |= telepathy.CHANNEL_MEDIA_CAPABILITY_NAT_TRAVERSAL_STUN
#
#            if caps.has_webcam:
#                spec_caps |= telepathy.CHANNEL_MEDIA_CAPABILITY_VIDEO
#
#        return gen_caps, spec_caps
