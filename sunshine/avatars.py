# telepathy-sunshine is the GaduGadu connection manager for Telepathy
#
# Copyright (C) 2006-2007 Ali Sabil <ali.sabil@gmail.com>
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
import imghdr
import hashlib
import dbus

import telepathy

from twisted.web.client import getPage

from xml.dom import minidom

from sunshine.handle import SunshineHandleFactory
from sunshine.util.decorator import async

__all__ = ['SunshineAvatars']

logger = logging.getLogger('Sunshine.Avatars')


class SunshineAvatars(telepathy.server.ConnectionInterfaceAvatars):

    def __init__(self):
        print 'SunshineAvatars called.'
        self._avatar_known = False
        telepathy.server.ConnectionInterfaceAvatars.__init__(self)

    def GetAvatarRequirements(self):
        mime_types = ("image/png","image/jpeg","image/gif")
        return (mime_types, 96, 96, 192, 192, 500 * 1024)

    def GetKnownAvatarTokens(self, contacts):
        result = {}
        for handle_id in contacts:
            handle = self.handle(telepathy.HANDLE_TYPE_CONTACT, handle_id)
            if handle == self.GetSelfHandle():
                #tutaj kiedys trzeba napisac kod odp za naszego avatara
                contact = None
                av_token = handle.name
                #pass
            else:
                contact = handle.contact

            if contact is not None:
                av_token = str(contact.uin)
            else:
                av_token = None

            if av_token is not None:
                result[handle] = av_token
            elif self._avatar_known:
                result[handle] = ""
        return result

    def RequestAvatars(self, contacts):
        for handle_id in contacts:
            handle = self.handle(telepathy.HANDLE_TYPE_CONTACT, handle_id)
            if handle == self.GetSelfHandle():
                #msn_object = self.msn_client.profile.msn_object
                #self._msn_object_retrieved(msn_object, handle)
                pass
            else:
                contact = handle.contact
                if contact is not None:
                    url = 'http://api.gadu-gadu.pl/avatars/%s/0.xml' % (str(contact.uin))
                    d = getPage(url, timeout=10)
                    d.addCallback(self.on_fetch_avatars_file_ok, url, handle_id)
                    d.addErrback(self.on_fetch_avatars_file_failed, url, handle_id)
                        
    def SetAvatar(self, avatar, mime_type):
        pass
#        self._avatar_known = True
#        if not isinstance(avatar, str):
#            avatar = "".join([chr(b) for b in avatar])
#        msn_object = papyon.p2p.MSNObject(self.msn_client.profile,
#                         len(avatar),
#                         papyon.p2p.MSNObjectType.DISPLAY_PICTURE,
#                         hashlib.sha1(avatar).hexdigest() + '.tmp',
#                         "",
#                         data=StringIO.StringIO(avatar))
#        self.msn_client.profile.msn_object = msn_object
#        avatar_token = msn_object._data_sha.encode("hex")
#        logger.info("Setting self avatar to %s" % avatar_token)
#        return avatar_token

    def ClearAvatar(self):
        pass
#        self.msn_client.profile.msn_object = None
#        self._avatar_known = True

    def on_fetch_avatars_file_ok(self, result, url, handle_id):
        try:
            if result:
                logger.info("Avatar file retrieved from %s" % (url))
                e = minidom.parseString(result)
                data = e.getElementsByTagName('bigAvatar')[0].firstChild.data

                d = getPage(str(data), timeout=20)
                d.addCallback(self.on_fetch_avatars_ok, data, handle_id)
                d.addErrback(self.on_fetch_avatars_failed, data, handle_id)
        except:
            logger.info("Avatar file can't be retrieved from %s" % (url))

    def on_fetch_avatars_file_failed(self, error, url, handle_id):
        logger.info("Avatar file can't be retrieved from %s, error: %s" % (url, error.getErrorMessage()))

    def on_fetch_avatars_ok(self, result, url, handle_id):
        try:
            handle = self.handle(telepathy.constants.HANDLE_TYPE_CONTACT, handle_id)
            logger.info("Avatar retrieved for %s from %s" % (handle.name, url))
            type = imghdr.what('', result)
            if type is None: type = 'jpeg'
            avatar = dbus.ByteArray(result)
            h = hashlib.new('md5')
            h.update(url)
            token = h.hexdigest()
            self.AvatarRetrieved(handle, token, avatar, 'image/' + type)
        except:
            logger.debug("Avatar retrieved but something went wrong.")

    def on_fetch_avatars_failed(self, error, url, handle_id):
        logger.debug("Avatar not retrieved, error: %s" % (error.getErrorMessage()))
#
#    # papyon.event.ContactEventInterface
#    def on_contact_msn_object_changed(self, contact):
#        if contact.msn_object is not None:
#            avatar_token = contact.msn_object._data_sha.encode("hex")
#        else:
#            avatar_token = ""
#        handle = ButterflyHandleFactory(self, 'contact',
#                contact.account, contact.network_id)
#        self.AvatarUpdated(handle, avatar_token)
#
#    # papyon.event.ProfileEventInterface
#    def on_profile_msn_object_changed(self):
#        msn_object = self.msn_client.profile.msn_object
#        if msn_object is not None:
#            avatar_token = msn_object._data_sha.encode("hex")
#            logger.info("Self avatar changed to %s" % avatar_token)
#            handle = ButterflyHandleFactory(self, 'self')
#            self.AvatarUpdated(handle, avatar_token)
#
#    @async
#    def _msn_object_retrieved(self, msn_object, handle):
#        if msn_object is not None and msn_object._data is not None:
#            logger.info("Avatar retrieved %s" % msn_object._data_sha.encode("hex"))
#            msn_object._data.seek(0, 0)
#            avatar = msn_object._data.read()
#            msn_object._data.seek(0, 0)
#            type = imghdr.what('', avatar)
#            if type is None: type = 'jpeg'
#            avatar = dbus.ByteArray(avatar)
#            token = msn_object._data_sha.encode("hex")
#            self.AvatarRetrieved(handle, token, avatar, 'image/' + type)
#        else:
#            logger.info("Avatar retrieved but NULL")
