#!/usr/bin/env python
# -*- coding: utf-8

__author__="lreqc"
__date__ ="$2009-07-14 01:54:14$"

import gtk
import xml.etree.ElementTree as ET

from twisted.internet import gtk2reactor
gtk2reactor.install()

from lqsoft.pygadu.twisted_protocol import GaduClient
from lqsoft.pygadu.models import GaduProfile, GaduContact

from twisted.internet import reactor, protocol
from twisted.python import log

import sys

class GaduClientFactory(protocol.ClientFactory):
    def __init__(self, config):
        self.config = config

    def buildProtocol(self, addr):
        # connect using current selected profile
        return GaduClient(self.config.profile)

    def startedConnecting(self, connector):
        print 'Started to connect.'

    def clientConnectionLost(self, connector, reason):
        print 'Lost connection.  Reason:', reason
    #    protocol.ReconnectingClientFactory.clientConnectionLost(self, connector, reason)
    #    connector.connect()

    def clientConnectionFailed(self, connector, reason):
        print 'Connection failed. Reason:', reason
    #    protocol.ReconnectingClientFactory.clientConnectionFailed(self, connector, reason)
        reactor.stop()

class MainApp(object):

    def __init__(self, config):
        self.config = config
        self.factory = GaduClientFactory(config)       

        self.gtk_builder = gtk.Builder();
        self.gtk_builder.add_from_file("simple_client.glade")

        self.mainWindow = self.gtk_builder.get_object("RoosterWindow")
        self.mainWindow.connect("destroy", self.onExit)

        self.contactTree = self.gtk_builder.get_object("ContactTree")

        unconnected = self.gtk_builder.connect_signals({
            'on_menu_connect_activate': self.connectUser,
            'on_menu_quit_activate': self.onExit,
            'on_menu_import_contacts_activate': self.importContacts,
           # 'on_menu_about_activate': self.onAbout,
        })
        print unconnected
        
        # status bar
        #self.statusBar = self.widgetTree.get_widget("main_statusbar")
        
        # extract some widgets
        #self.loginDialog = self.widgetTree.get_widget("LoginDialog")
        #self.loginDialog_uin = self.widgetTree.get_widget("uin_entry")
        #self.loginDialog_pass = self.widgetTree.get_widget("password_entry")
 
        #self.sendButton = self.widgetTree.get_widget("send_button")
        #self.messageEntry = self.widgetTree.get_widget("message_entry")

        #tv = self.widgetTree.get_widget("message_view")
        #self.msgBuf = gtk.TextBuffer()
        #tv.set_buffer(self.msgBuf)
        
        self.mainWindow.show()        

    def onMessageSent(self, widget, data=None):
        self.msgBuf.insert_at_cursor('Hello!\n')

    def onExit(self, widget, data=None):
        reactor.stop()
        return True

    def connectUser(self, widget, *args):
        """This is called when user selects "connect" from the main menu"""
        # connect some callbacks to the model
        profile = self.config.profile
        profile.onLoginSuccess = self.loginSuccess
        profile.onLoginFailure = self.loginFailed
        profile.onContactStatusChange = self.updateContact
        profile.onMessageReceived = self.messageReceived

        statusBar = self.gtk_builder.get_object("status_bar")

        self.__status_ctx_id = statusBar.get_context_id("Login status")
        statusBar.push(self.__status_ctx_id, "Authenticating...")
        
        reactor.connectTCP('91.197.13.83', 8074, self.factory)

        #self.loginDialog.show()

    def importContacts(self, widget, *args):
        txt = """<b>Gżegżółka</b>"""
        # self.config.profile.importContacts(self.refreshContactList)
        self.config.profile.sendTo(1849224, txt)

    def refreshContactList(self):
        self.contactTree.clear()

        all_g = self.contactTree.append(None, row=("ALL", 0, False) )

        for contact in self.config.profile.contacts:
            self.contactTree.append(all_g,\
                row=(contact.ShowName, contact.status, True) )

    def loginDialogResponse(self, widget, response_id, *args):
        self.loginDialog.destroy()

        if response_id == 2:
            self.profile.uin = int(self.loginDialog_uin.get_text())
            self.profile.password = self.loginDialog_pass.get_text()

            statusBar = self.gtk_builder.get_object("status_bar")

            statusBar.pop(self.__status_ctx_id)
            statusBar.push(self.__status_ctx_id, "Connecting...")

            reactor.connectTCP('91.197.13.83', 8074, self.factory)
        else:
            return False

    def loginSuccess(self):
        statusBar = self.gtk_builder.get_object("status_bar")
        statusBar.pop(self.__status_ctx_id)
        statusBar.push(self.__status_ctx_id, "Login done.")

    def loginFailed(self):
        statusBar = self.gtk_builder.get_object("status_bar")
        
        statusBar.pop(self.__status_ctx_id)
        statusBar.push(self.__status_ctx_id, "Login done.")

    def updateContact(self, contact):
        print contact

    def messageReceived(self, msg):
        print "Msg %d %d [%r] [%r]" % (msg.content.offset_plain, msg.content.offset_attrs, msg.content.plain_message, msg.content.html_message)

class Config(object):

    def __init__(self, config_file):
        config_xml = ET.parse(config_file)

        self.profiles = {}

        for profile_xml in config_xml.findall('gadu-profile'):
            profile = GaduProfile(uin= int(profile_xml.find('uin').text) )
            profile.password = profile_xml.find('password').text

            for elem in profile_xml.find('Groups').getchildren():
                profile.addContactGroup( GaduContactGroup.from_xml(elem) )

            for elem in profile_xml.find('Contacts').getchildren():
                profile.addContact( GaduContact.from_xml(elem) )

            self.profiles[profile.uin] = profile

        self._default_profile = int(config_xml.find('default-profile').text)


    @property
    def profile(self):
        return self.profiles[self._default_profile]

if __name__ == '__main__':
    import os
    import os.path

    def init_defaults():
        with open(config_path, 'wb+') as config_file:
            config_file.write("""<?xml version='1.0'?>
            <sgc-config>
                <default-profile>0</default-profile>
                <gadu-profile>
                    <uin>0<!-- put your GG number here --></uin>
                    <password>no_pass<!-- put your password here --></password>
                    <Groups />
                    <Contacts />
                </gadu-profile>
            </sgc-config>""");


    # get the config data
    try:
        homedir = os.environ['APPDATA']
    except KeyError:
        homedir = os.environ['HOME']

    config_path = os.path.join(homedir, 'sgc_config.xml')

    if not os.path.isfile(config_path):
        init_defaults()

    config = Config(config_path)
    
    # initialize logging
    log.startLogging(sys.stdout)

    # run
    app = MainApp( config )
    reactor.run()
