import sys
import os
import time
import weakref
import logging

import xml.etree.ElementTree as ET

from gadu.lqsoft.pygadu.twisted_protocol import GaduClient
from gadu.lqsoft.pygadu.models import GaduProfile, GaduContact, GaduContactGroup

from twisted.internet import reactor, protocol
from twisted.python import log

import dbus
import telepathy

from gadu.presence import GaduPresence
from gadu.aliasing import GaduAliasing
#from butterfly.avatars import ButterflyAvatars
from gadu.handle import GaduHandleFactory
from gadu.capabilities import GaduCapabilities
from gadu.contacts import GaduContacts
from gadu.channel_manager import GaduChannelManager
from gadu.util.decorator import async

__all__ = ['GaduConnection']

logger = logging.getLogger('Gadu.Connection')


class GaduConfig(object):
    def __init__(self, uin):
        self.uin = uin
        self.path = None
        self.contacts_count = 0

    def check_dirs(self):
        path = os.path.join(os.path.join(os.environ['HOME'], '.telepathy-gadu'), str(self.uin))
        try:
            os.makedirs(path)
        except:
            pass
        if os.path.isfile(os.path.join(path, 'profile.xml')):
            pass
        else:
            config_file = open(os.path.join(path, 'profile.xml'), 'wb+')
            config_file.write("""<ContactBook>
                <Groups />
                <Contacts />
            </ContactBook>""");
            config_file.close()
        self.path = os.path.join(path, 'profile.xml')
        return os.path.join(path, 'profile.xml')

    def get_contacts(self):
        file = open(self.path, "r")
        config_xml = ET.parse(file).getroot()

        self.roster = {'groups':[], 'contacts':[]}

        for elem in config_xml.find('Groups').getchildren():
            self.roster['groups'].append(elem)

        for elem in config_xml.find('Contacts').getchildren():
            self.roster['contacts'].append(elem)

        self.contacts_count = len(config_xml.find('Contacts').getchildren())

        return self.roster

    def make_contacts_file(self, groups, contacts):
        contactbook_xml = ET.Element("ContactBook")

        groups_xml = ET.SubElement(contactbook_xml, "Groups")
        contacts_xml = ET.SubElement(contactbook_xml, "Contacts")

        for group in groups:
            #Id, Name, IsExpanded, IsRemovable
            group_xml = ET.SubElement(groups_xml, "Group")
            ET.SubElement(group_xml, "Id").text = group.Id
            ET.SubElement(group_xml, "Name").text = group.Name
            ET.SubElement(group_xml, "IsExpanded").text = str(group.IsExpanded)
            ET.SubElement(group_xml, "IsRemovable").text = str(group.IsRemovable)

        for contact in contacts:
            #Guid, GGNumber, ShowName. MobilePhone. HomePhone, Email, WWWAddress, FirstName, LastName, Gender, Birth, City, Province, Groups, CurrentAvatar, Avatars
            contact_xml = ET.SubElement(contacts_xml, "Contact")
            ET.SubElement(contact_xml, "Guid").text = contact.Guid
            ET.SubElement(contact_xml, "GGNumber").text = contact.GGNumber
            ET.SubElement(contact_xml, "ShowName").text = contact.ShowName
            contact_groups_xml = ET.SubElement(contact_xml, "Groups")
            contact_groups = ET.fromstring(contact.Groups)
            if contact.Groups:
                for group in contact_groups.getchildren():
                    ET.SubElement(contact_groups_xml, "GroupId").text = group.text

        #ET.dump(contactbook_xml)
        xml_file = ET.tostring(contactbook_xml)

        #and save that
        config_file = open(self.path, 'wb+')
        config_file.write(xml_file);
        config_file.close()

    def get_contacts_count(self):
        return self.contacts_count

#class GaduClientFactory(protocol.ClientFactory, protocol.ReconnectingClientFactory):
class GaduClientFactory(protocol.ClientFactory):
    def __init__(self, config):
        self.config = config

    def buildProtocol(self, addr):
        # connect using current selected profile
        #self.resetDelay()
        return GaduClient(self.config)

    def startedConnecting(self, connector):
        logger.info('Started to connect.')

    def clientConnectionLost(self, connector, reason):
        logger.info('Lost connection.  Reason: %s' % (reason))
        #protocol.ReconnectingClientFactory.clientConnectionLost(self, connector, reason)
        #connector.connect()
        reactor.stop()

    def clientConnectionFailed(self, connector, reason):
        logger.info('Connection failed. Reason: %s' % (reason))
        #protocol.ReconnectingClientFactory.clientConnectionFailed(self, connector, reason)
        reactor.stop()

class GaduConnection(telepathy.server.Connection,
        telepathy.server.ConnectionInterfaceRequests,
        GaduPresence,
        GaduAliasing,
#        ButterflyAvatars,
        GaduCapabilities,
        GaduContacts
        ):


    _mandatory_parameters = {
            'account' : 's',
            'password' : 's'
            }
    _optional_parameters = {
            'server' : 's',
            'port' : 'q'
            }
    _parameter_defaults = {
            'server' : '91.197.13.67',
            'port' : 8074
            }

    def __init__(self, manager, parameters):
        self.check_parameters(parameters)

        try:
            account = unicode(parameters['account'])
            server = (parameters['server'], parameters['port'])

            self._manager = weakref.proxy(manager)
            self._account = (parameters['account'], parameters['password'])
            self._server = (parameters['server'], parameters['port'])

            self.profile = GaduProfile(uin= int(parameters['account']) )
            self.profile.uin = int(parameters['account'])
            self.profile.password = str(parameters['password'])
            self.profile.status = 0x014
            self.profile.onLoginSuccess = self.on_loginSuccess
            self.profile.onLoginFailure = self.on_loginFailed
            self.profile.onContactStatusChange = self.on_updateContact
            self.profile.onMessageReceived = self.on_messageReceived

            #lets try to make file with contacts etc ^^
            self.configfile = GaduConfig(int(parameters['account']))
            self.configfile.check_dirs()
            #lets get contacts from contacts config file
            contacts_list = self.configfile.get_contacts()

            for contact_from_list in contacts_list['contacts']:
                c = GaduContact.from_xml(contact_from_list)
                try:
                    c.uin
                    self.profile.addContact( c )
                except:
                    pass
                
            for group_from_list in contacts_list['groups']:
                g = GaduContactGroup.from_xml(group_from_list)
                if g.Name:
                    self.profile.addGroup(g)
            
            logger.info("We have %s contacts in file." % (self.configfile.get_contacts_count()))
                

            self.factory = GaduClientFactory(self.profile)
            self._channel_manager = GaduChannelManager(self)
            self._recv_id = 0

            # Call parent initializers
            telepathy.server.Connection.__init__(self, 'gadugadu', account, 'gadu')
            telepathy.server.ConnectionInterfaceRequests.__init__(self)
            GaduPresence.__init__(self)
            GaduAliasing.__init__(self)
#            ButterflyAvatars.__init__(self)
            GaduCapabilities.__init__(self)
            GaduContacts.__init__(self)


            self.set_self_handle(GaduHandleFactory(self, 'self'))

            self.__disconnect_reason = telepathy.CONNECTION_STATUS_REASON_NONE_SPECIFIED
            #small hack. We started to connnect with status invisible and just later we change status to client-like
            self._initial_presence = 0x014
            self._initial_personal_message = None

            logger.info("Connection to the account %s created" % account)
        except Exception, e:
            import traceback
            logger.exception("Failed to create Connection")
            raise

    @property
    def manager(self):
        return self._manager

    @property
    def gadu_client(self):
        return self.profile

    def handle(self, handle_type, handle_id):
        self.check_handle(handle_type, handle_id)
        return self._handles[handle_type, handle_id]

    def get_contact_alias(self, handle_id):
        return self._get_alias(handle_id)

    def get_handle_id_by_name(self, handle_type, name):
        """Returns a handle ID for the given type and name

        Arguments:
        handle_type -- Telepathy Handle_Type for all the handles
        name -- username for the contact

        Returns:
        handle_id -- ID for the given username
        """

        handle_id = 0
        for handle in self._handles.values():
            if handle.get_name() == name:
                handle_id = handle.get_id()
                break

        return handle_id

    def Connect(self):
        if self._status == telepathy.CONNECTION_STATUS_DISCONNECTED:
            logger.info("Connecting")
            self.StatusChanged(telepathy.CONNECTION_STATUS_CONNECTING,
                    telepathy.CONNECTION_STATUS_REASON_REQUESTED)
            self.__disconnect_reason = telepathy.CONNECTION_STATUS_REASON_NONE_SPECIFIED
            #reactor.connectTCP('91.197.13.83', 8074, self.factory)
            reactor.connectTCP(self._server[0], self._server[1], self.factory)

    def Disconnect(self):
        logger.info("Disconnecting")
        self.StatusChanged(telepathy.CONNECTION_STATUS_DISCONNECTED,
                telepathy.CONNECTION_STATUS_REASON_REQUESTED)
        reactor.stop()

    def RequestHandles(self, handle_type, names, sender):
        logger.info("Method RequestHandles called, handle type: %s, names: %s" % (str(handle_type), str(names)))
        self.check_connected()
        self.check_handle_type(handle_type)

        handles = []
        for name in names:
            if handle_type == telepathy.HANDLE_TYPE_CONTACT:
                contact_name = name

                handle = GaduHandleFactory(self, 'contact',
                        contact_name, None)

#                try:
#                    #just check is contact_name is integer
#                    stripped = str(int(contact_name))
#                except:
#                    if self.profile.isContactExist(contact_name) == False:
#                        contact_pseudo_xmled = ET.fromstring("""<Contact><Guid>%s</Guid><GGNumber>%s</GGNumber><ShowName>%s</ShowName></Contact>""" % (str(contact_name), str(contact_name), str(contact_name)))
#                        c = GaduContact.from_xml(contact_pseudo_xmled)
#                        #self.profile.addContact( c )
#                        self.profile.addNewContact( c )
#                        self.profile.notifyAboutContact( c )
                #if len(name) > 1:
                #    network_id = int(name[1])
                #else:
                #    network_id = papyon.NetworkID.MSN
                #contacts = self.msn_client.address_book.contacts.\
                #        search_by_account(contact_name).\
                #        search_by_network_id(network_id)
                #
                #if len(contacts) > 0:
                #    contact = contacts[0]
                #    handle = GaduHandleFactory(self, 'contact',
                #            contact.account, contact.network_id)
                #else:
                #    handle = GaduHandleFactory(self, 'contact',
                #            contact_name, network_id)
                #print contact_name
                #contact = self.profile.get_contact(int(contact_name))
                #print str(contact)



                

#                    print "contact name: %s" % (contact_name)
#                    handle = GaduHandleFactory(self, 'contact',
#                                str(contact_name), None)
#
#
                
            elif handle_type == telepathy.HANDLE_TYPE_LIST:
                handle = GaduHandleFactory(self, 'list', name)
            elif handle_type == telepathy.HANDLE_TYPE_GROUP:
                handle = GaduHandleFactory(self, 'group', name)
            else:
                raise telepathy.NotAvailable('Handle type unsupported %d' % handle_type)
            handles.append(handle.id)
            self.add_client_handle(handle, sender)
        return handles

    def _generate_props(self, channel_type, handle, suppress_handler, initiator_handle=None):
        props = {
            telepathy.CHANNEL_INTERFACE + '.ChannelType': channel_type,
            telepathy.CHANNEL_INTERFACE + '.TargetHandle': 0 if handle is None else handle.get_id(),
            telepathy.CHANNEL_INTERFACE + '.TargetHandleType': telepathy.HANDLE_TYPE_NONE if handle is None else handle.get_type(),
            telepathy.CHANNEL_INTERFACE + '.Requested': suppress_handler
            }

        if initiator_handle is not None:
            props[telepathy.CHANNEL_INTERFACE + '.InitiatorHandle'] = initiator_handle.id

        return props

    @dbus.service.method(telepathy.CONNECTION, in_signature='suub',
        out_signature='o', async_callbacks=('_success', '_error'))
    def RequestChannel(self, type, handle_type, handle_id, suppress_handler,
            _success, _error):
        self.check_connected()
        channel_manager = self._channel_manager

        if handle_id == 0:
            handle = None
        else:
            handle = self.handle(handle_type, handle_id)
        props = self._generate_props(type, handle, suppress_handler)
        self._validate_handle(props)

        channel = channel_manager.channel_for_props(props, signal=False)

        _success(channel._object_path)
        self.signal_new_channels([channel])


    def get_handle_id_by_name(self, handle_type, name):
        """Returns a handle ID for the given type and name

        Arguments:
        handle_type -- Telepathy Handle_Type for all the handles
        name -- username for the contact

        Returns:
        handle_id -- ID for the given username
        """
        handle_id = 0
        for handle in self._handles.values():
            if handle.get_name() == name:
                handle_id = handle.get_id()
                break

        return handle_id

    def updateContactsFile(self):
        """Method that updates contact file when it changes and in loop every 5 seconds."""
        self.configfile.make_contacts_file(self.profile.groups, self.profile.contacts)
        reactor.callLater(5, self.updateContactsFile)

    @async
    def makeTelepathyContactsChannel(self):
        logger.debug("Method makeTelepathyContactsChannel called.")
        handle = GaduHandleFactory(self, 'list', 'subscribe')
        props = self._generate_props(telepathy.CHANNEL_TYPE_CONTACT_LIST,
            handle, False)
        self._channel_manager.channel_for_props(props, signal=True)

#        handle = ButterflyHandleFactory(self, 'list', 'publish')
#        props = self._generate_props(telepathy.CHANNEL_TYPE_CONTACT_LIST,
#            handle, False)
#        self._channel_manager.channel_for_props(props, signal=True)

    @async
    def makeTelepathyGroupChannels(self):
        logger.debug("Method makeTelepathyGroupChannels called.")
        for group in self.profile.groups:
            handle = GaduHandleFactory(self, 'group',
                    group.Name)
            props = self._generate_props(
                telepathy.CHANNEL_TYPE_CONTACT_LIST, handle, False)
            self._channel_manager.channel_for_props(props, signal=True)

    @async
    def on_contactsImported(self):
        #TODO: that contacts should be written into XML file with contacts. I need to write it :)
        logger.info("No contacts in the XML contacts file yet. Contacts imported.")

        self.configfile.make_contacts_file(self.profile.groups, self.profile.contacts)
        reactor.callLater(5, self.updateContactsFile)

        self.makeTelepathyContactsChannel()
        self.makeTelepathyGroupChannels()
        
        self._status = telepathy.CONNECTION_STATUS_CONNECTED
        self.StatusChanged(telepathy.CONNECTION_STATUS_CONNECTED,
                telepathy.CONNECTION_STATUS_REASON_REQUESTED)

    @async
    def on_loginSuccess(self):
        logger.info("Connected")

        #if its a first run or we dont have any contacts in contacts file yet then try to import contacts from server
        if self.configfile.get_contacts_count() == 0:
            self.profile.importContacts(self.on_contactsImported)
        else:
            self.configfile.make_contacts_file(self.profile.groups, self.profile.contacts)
            reactor.callLater(5, self.updateContactsFile)

            self.makeTelepathyContactsChannel()
            self.makeTelepathyGroupChannels()

            self._status = telepathy.CONNECTION_STATUS_CONNECTED
            self.StatusChanged(telepathy.CONNECTION_STATUS_CONNECTED,
                    telepathy.CONNECTION_STATUS_REASON_REQUESTED)

    @async
    def on_loginFailed(self):
        logger.info("Method on_loginFailed called.")
        self._status = telepathy.CONNECTION_STATUS_DISCONNECTED
        self.StatusChanged(telepathy.CONNECTION_STATUS_DISCONNECTED,
                telepathy.CONNECTION_STATUS_REASON_AUTHENTICATION_FAILED)
        reactor.stop()

    @async
    def on_updateContact(self, contact):
        handle_id = self.get_handle_id_by_name(telepathy.constants.HANDLE_TYPE_CONTACT, str(contact.uin))
        handle = self.handle(telepathy.constants.HANDLE_TYPE_CONTACT, handle_id)
        logger.info("Method on_updateContact called, status changed for UIN: %s, id: %s, status: %s, description: %s" % (contact.uin, handle.id, contact.status, contact.description))
        self._presence_changed(handle, contact.status, contact.get_desc())

    @async
    def on_messageReceived(self, msg):
        handle_id = self.get_handle_id_by_name(telepathy.constants.HANDLE_TYPE_CONTACT,
                                  str(msg.sender))
        if handle_id != 0:
            handle = self.handle(telepathy.constants.HANDLE_TYPE_CONTACT, handle_id)
        else:
            handle = GaduHandleFactory(self, 'contact',
                    str(msg.sender), None)
                
        timestamp = int(time.time())
        type = telepathy.CHANNEL_TEXT_MESSAGE_TYPE_NORMAL
        logger.info("User %s sent a message" % handle.name)

        logger.info("Msg from %r %d %d [%r] [%r]" % (msg.sender, msg.content.offset_plain, msg.content.offset_attrs, msg.content.plain_message, msg.content.html_message))

        props = self._generate_props(telepathy.CHANNEL_TYPE_TEXT,
                handle, False)
        channel = self._channel_manager.channel_for_props(props,
                signal=True, conversation=None)
        message = "%s" % unicode(str(msg.content.plain_message).replace('\x00', '').decode('windows-1250').encode('utf-8'))
        channel.Received(self._recv_id, timestamp, handle, type, 0, message)
        self._recv_id += 1


    # papyon.event.ClientEventInterface
    def on_client_state_changed(self, state):
        if state == papyon.event.ClientState.CONNECTING:
            self.StatusChanged(telepathy.CONNECTION_STATUS_CONNECTING,
                    telepathy.CONNECTION_STATUS_REASON_REQUESTED)
        elif state == papyon.event.ClientState.SYNCHRONIZED:
            handle = ButterflyHandleFactory(self, 'list', 'subscribe')
#            props = self._generate_props(telepathy.CHANNEL_TYPE_CONTACT_LIST,
#                handle, False)
#            self._channel_manager.channel_for_props(props, signal=True)
#
#            handle = ButterflyHandleFactory(self, 'list', 'publish')
#            props = self._generate_props(telepathy.CHANNEL_TYPE_CONTACT_LIST,
#                handle, False)
#            self._channel_manager.channel_for_props(props, signal=True)

            #handle = ButterflyHandleFactory(self, 'list', 'hide')
            #props = self._generate_props(telepathy.CHANNEL_TYPE_CONTACT_LIST,
            #    handle, False)
            #self._channel_manager.channel_for_props(props, signal=True)

            #handle = ButterflyHandleFactory(self, 'list', 'allow')
            #props = self._generate_propstelepathy.CHANNEL_TYPE_CONTACT_LIST,
            #    handle, False)
            #self._channel_manager.channel_for_props(props, signal=True)

            #handle = ButterflyHandleFactory(self, 'list', 'deny')
            #props = self._generate_props(telepathy.CHANNEL_TYPE_CONTACT_LIST,
            #    handle, False)
            #self._channel_manager.channel_for_props(props, signal=True)

            for group in self.msn_client.address_book.groups:
                handle = ButterflyHandleFactory(self, 'group',
                        group.name.decode("utf-8"))
                props = self._generate_props(
                    telepathy.CHANNEL_TYPE_CONTACT_LIST, handle, False)
                self._channel_manager.channel_for_props(props, signal=True)
        elif state == papyon.event.ClientState.OPEN:
            self.StatusChanged(telepathy.CONNECTION_STATUS_CONNECTED,
                    telepathy.CONNECTION_STATUS_REASON_REQUESTED)
            presence = self._initial_presence
            message = self._initial_personal_message
            if presence is not None:
                self._client.profile.presence = presence
            if message is not None:
                self._client.profile.personal_message = message
            self._client.profile.end_point_name = "PAPYON"

            if (presence is not None) or (message is not None):
                self._presence_changed(ButterflyHandleFactory(self, 'self'),
                        self._client.profile.presence,
                        self._client.profile.personal_message)
        elif state == papyon.event.ClientState.CLOSED:
            self.StatusChanged(telepathy.CONNECTION_STATUS_DISCONNECTED,
                    self.__disconnect_reason)
            #FIXME
            self._channel_manager.close()
            self._advertise_disconnected()

    # papyon.event.ClientEventInterface
    def on_client_error(self, type, error):
        if type == papyon.event.ClientErrorType.NETWORK:
            self.__disconnect_reason = telepathy.CONNECTION_STATUS_REASON_NETWORK_ERROR
        elif type == papyon.event.ClientErrorType.AUTHENTICATION:
            self.__disconnect_reason = telepathy.CONNECTION_STATUS_REASON_AUTHENTICATION_FAILED
        elif type == papyon.event.ClientErrorType.PROTOCOL and \
             error == papyon.event.ProtocolError.OTHER_CLIENT:
            self.__disconnect_reason = telepathy.CONNECTION_STATUS_REASON_NAME_IN_USE
        else:
            self.__disconnect_reason = telepathy.CONNECTION_STATUS_REASON_NONE_SPECIFIED

    # papyon.event.InviteEventInterface
    def on_invite_conversation(self, conversation):
        logger.debug("Conversation invite")
        #FIXME: get rid of this crap and implement group support
        participants = conversation.participants
        for p in participants:
            participant = p
            break
        handle = ButterflyHandleFactory(self, 'contact',
                participant.account, participant.network_id)

        props = self._generate_props(telepathy.CHANNEL_TYPE_TEXT,
            handle, False, initiator_handle=handle)
        channel = self._channel_manager.channel_for_props(props,
            signal=True, conversation=conversation)

    # papyon.event.InviteEventInterface
    def on_invite_conference(self, call):
        logger.debug("Call invite")
        handle = ButterflyHandleFactory(self, 'contact', call.peer.account,
                call.peer.network_id)

        props = self._generate_props(telepathy.CHANNEL_TYPE_STREAMED_MEDIA,
                handle, False, initiator_handle=handle)

        channel = self._channel_manager.channel_for_props(props,
                signal=True, call=call)

    def _advertise_disconnected(self):
        self._manager.disconnected(self)
