# -*- coding: utf-8
__author__="lreqc"
__date__ ="$2009-07-14 07:33:27$"

from gadu.lqsoft.pygadu.network_base import StructNotice
import xml.etree.ElementTree as ET
import hashlib, zlib

class GaduProfile(object):

    def __init__(self, uin):
        self.uin = uin
        self.__status = None
        self.__hashelem = None
        self.__contacts = {}
        self.__groups = {}
        self.__connection = None
        
    def __set_password(self, value):
        self.__hashelem = hashlib.new('sha1')
        self.__hashelem.update(value)

    def __get_hashelem(self):
        return self.__hashelem.copy()

    def __set_status(self, value):
        self.__status = value

    def __get_status(self):
        return self.__status

    password = property(__get_hashelem, __set_password)
    status = property(__get_status, __set_status)

    def _updateContact(self, notify):
        # notify is of class GGStruct_Status80
        try:
            contact = self.__contacts[notify.uin]
        except KeyError:
            contact = GaduContact.simple_make(self, notify.uin, "Unknown User")

        contact.status =  notify.status
        contact.description = notify.description
        self.onContactStatusChange(contact)

    def _creditials(self, result, *args, **kwargs):
        """Called by protocol, to get creditials, result will be passed to login
            procedure. It should be a 2-tuple with (uin, hash_elem)"""
        return self.onCreditialsNeeded()

    def _loginSuccess(self, conn, *args, **kwargs):
        self.__connection = conn
        self.onLoginSuccess()
        return self

    # high-level interface
    @property
    def connected(self):
        """Is the profile currently used in an active connection"""
        return self.__connection is not None

    def addContact(self, contact):
        if self.__contacts.has_key(contact.uin):
            raise ValueError("Contact with UIN %d already exists." % contact.uin)
        
        self.__contacts[contact.uin] = contact
        if self.connected:
            self.setNotifyState(contact.uin, contact.notify_flags)

    def addGroup(self, group):
        if self.__groups.has_key(group.Id):
            raise ValueError("Group %d already exists." % group.Id)
        self.__groups[group.Id] = group

    # stuff that user can use
    def setNotifyState(self, uin, new_state):
        pass

    def sendTextMessage(self, text):
        pass

    def setMyState(self, new_state, new_description=''):
        if not self.connected:
            raise RuntimeError("You need to be connected, to import contact list from the server.")

        self.__connection.changeStatus(new_state, new_description)

    def sendTo(self, uin, message):
        if not self.connected:
            raise RuntimeError("You need to be connected, to send messages.")
        self.__connection.sendHTMLMessage(uin, message + '\0')

    def importContacts(self, callback):
        """Issue an import request. This is non-blocking and returns no data."""
        if not self.connected:
            raise RuntimeError("You need to be connected, to import contact list from the server.")

        def parse_xml(data):
            book = ET.fromstring(zlib.decompress(data))
            self._flushContacts()
            
            for elem in book.find('Groups').getchildren():                
                self.addGroup( GaduContactGroup.from_xml(elem) )

            for elem in book.find('Contacts').getchildren():
                contact = GaduContact.from_xml(elem)
                self.addContact( contact )
                self.__connection.addNewContact(contact)

            callback()

        self.__connection.sendImportRequest(parse_xml)

    def _flushContacts(self):
        self.__contacts = {}
        self.__groups = {}

    def exportContacts(self):
        pass

    def disconnect(self):
        self.__connection.transport.loseConnection()

    # stuff that should be implemented by user
    def onCreditialsNeeded(self, *args, **kwargs):
        return (self.uin, self.__hashelem, self.__status)

    def onLoginSuccess(self):
        """Called when login is completed."""
        pass

    def onLoginFailure(self, reason):
        """Called after an unsuccessful login."""
        pass

    def onContactStatusChange(self, contact):
        """Called when a status of a contact has changed."""
        pass

    def onMessageReceived(self, message):
        """Called when a message had been received"""
        pass

    def isContactExist(self, uin):
        return self.__contacts.has_key(uin)

    def get_contact(self, uin):
        if self.__contacts.has_key(uin):
            return self.__contacts[uin]
        else:
            return None

    @property
    def contacts(self):
        return self.__contacts.itervalues()

class Def(object):
    def __init__(self, type, default_value, required=False, exportable=True, init=lambda x: x):
        self.type = type
        self.default = default_value
        self.required = required
        self.exportable = exportable
        self._init = init

    def init(self, value):
        return self.type( self._init(value) )
        
def mkdef(*args):
    return Def(*args)


class FlatXMLObject(object):

    def __init__(self, **kwargs):
        for (k, v) in self.SCHEMA.iteritems():
            if v.required and not kwargs.has_key(k):
                raise ValueError("You must supply a %s field." % k)

            setattr(self, k, kwargs.get(k, v.default))
            if not isinstance(getattr(self, k), v.type):
                raise ValueError("Field %s has to be of class %s." % (k, v.type.__name__))

    @classmethod
    def from_xml(cls, element):
        dict = {}

        for (k, v) in cls.SCHEMA.iteritems():
            elem = element.find("./"+k)
            if not v.exportable:
                continue
                
            if v.required and elem is None:
                raise ValueError("Invalid element - need child element %s to unpack." % k)

            dict[k] = v.type(elem.text if elem is not None and elem.text else v.default)           

        return cls(**dict)          

class GaduContactGroup(FlatXMLObject):
    SCHEMA = {
        "Id":           mkdef(str, '', True),
        "Name":         mkdef(str, '', True),
        "IsExpanded":   mkdef(bool, True),
        "IsRemovable":  mkdef(bool, True),
    }
    

class GaduContact(FlatXMLObject):
    """Single contact as seen in catalog (person we are watching) - conforming to GG8.0"""
    SCHEMA = {
        'Guid':             mkdef(str, '', True),
        'GGNumber':         mkdef(str, '', True),
        'ShowName':         mkdef(str, '', True),
        'MobilePhone':      mkdef(str, ''),
        'HomePhone':        mkdef(str, ''),
        'Email':            mkdef(str, 'someone@somewhere.moc'),
        'WWWAddress':       mkdef(str, ''),
        'FirstName':        mkdef(str, ''),
        'LastName':         mkdef(str, ''),
        'Gender':           mkdef(int, 0),
        'Birth':            mkdef(str, ''),
        'City':             mkdef(str, ''),
        'Province':         mkdef(str, ''),
        # 'Groups':           mkdef(list, ['0'], init lambda v: [ int(x) for x in v.split() ]),
        'CurrentAvatar':    mkdef(int, 0),
        # 'Avatars':          mkdef(list, []),
        'UserActivatedInMG':mkdef(bool, False),
        'FlagBuddy':        mkdef(bool, False),
        'FlagNormal':       mkdef(bool, False),
        'FlagFriend':       mkdef(bool, False),
        'FlagIgnored':      mkdef(bool, False),
        # state variables
        'description':      mkdef(str, '', False, False),
        'status':           mkdef(int, 0, False, False),
    }

    @classmethod
    def simple_make(cls, profile, uin, name):
        return cls(profile, Guid=str(uin), GGNumber=str(uin), ShowName=name)

    def __str__(self):
        return "[%s,%d: %s]" % (self.GGNumber, self.status, self.description)

    @property
    def uin(self):
        return int(self.GGNumber)

    @property
    def notify_flags(self):
        return int(self.FlagBuddy and StructNotice.TYPE.BUDDY) \
            & int(self.FlagFriend and StructNotice.TYPE.FRIEND) \
            & int(self.FlagIgnored and StructNotice.TYPE.IGNORE)

    def updateStatus(self, status, desc=None):
        self.status = status
        if desc: self.description = desc

    def updateName(self, name):
        self.ShowName = name

#     @classmethod
#     def from_request_string(cls, rqs):
#         dict = {}
#         for (fmt, value) in zip(cls.RQ_STRING_FORMAT, rqs.split(';')):
#             dict[fmt[0]] = fmt[1](value)
#         return cls(**dict)
# 
#     def request_string(self):
#         return ";".join( [ str(self.__getattribute__(fmt[0])) for fmt in self.RQ_STRING_FORMAT] )
