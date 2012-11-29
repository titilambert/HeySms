#!/usr/bin/env python
# -*- coding: UTF-8 -*-
#
#    controller.py
#
#    This file is part of HeySms
#
#    Copyright (C) 2012 Thibault Cohen
#
#    This program is free software; you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation; either version 2 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program; if not, write to the Free Software
#    Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
#


import select
import random
import socket
from time import sleep
import subprocess
import os

import dbus
from PySide import QtCore, QtNetwork, QtGui

import pybonjour
from friend import Friend
from lib import logger, search_contacts
from config import config


port = 5299


class Controller(QtCore.QThread):
    def __init__(self,auth_user, parent=None):
        QtCore.QThread.__init__(self, None)
        self.fullname = 'N900_Controller'
        self.port = port
        self.number = 'N900'
        self.auth_user = auth_user
        self.node = "%s@n900" % ''.join(c for c in self.fullname if c.isalnum()).lower()
        self.favorite = False

        self.parent = parent
        self.client = None  # Bonjour socket client
        self.is_ready = False
        self.id = 0

        self.add_contact_dict = None
        self.active_contact_dict = None
        # set self.active_contact_dict
        self.update_active_list()

    def _register_callback(self, sdRef, flags, errorCode,
                           name, regtype, domain):
        # Set variable when self is registered
        sleep(1)
        self.is_ready = True
        logger.debug("Controller contact registered: %s" % self.fullname)

    def run(self):
        # Register on bonjour chat
        self.id = random.randint(100000000000, 999999999999)
        txt = {}
        txt['1st'] = self.fullname
        txt['last'] = ""
        txt['status'] = 'avail'
        txt['port.p2pj'] = self.port
        txt['nick'] = self.fullname
        txt['jid'] = self.node
        txt['email'] = self.node
        txt['version'] = 1
        txt['txtvers'] = 1

        txt = pybonjour.TXTRecord(txt, strict=True)

        self.sdRef = pybonjour.DNSServiceRegister(name=self.node,
                                regtype='_presence._tcp',
                                port=self.port,
                                txtRecord=txt,
                                callBack=self._register_callback
                                )
        # Bonjour chat handcheck
        self.must_run = True
        while self.must_run:
            ready = select.select([self.sdRef], [], [], 1)
            if self.sdRef in ready[0]:
                pybonjour.DNSServiceProcessResult(self.sdRef)


    def close(self):
        self.must_run = False
        while self.isRunning():
            sleep(0.5)
        logger.debug("Friend closed: %s" % self.fullname)
        self.sdRef.close()


    def sms_to_bonjour(self, msg):
        logger.debug("Forward controller reply to bonjour")
        msg = msg.replace("<", "&lt;")
        msg = msg.replace(">", "&gt;")
        if isinstance(msg, QtCore.QString):
            msg = unicode(msg)
        # Waiting self is bonjour registered
        while self.is_ready == False:
            logger.debug("Waiting bonjour contact "
                         "registered: %s" % self.fullname)
            sleep(1)

        # Connect to bonjour server
        host = self.auth_user.values()[0]['host']
        port = self.auth_user.values()[0]['port']
        so = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            so.connect((host, port))
        except TypeError,e :
            logger.debug("Connection error: %s" % str(e))
            return False
        # Dont need this !?
        so.setblocking(1)
        so.settimeout(2)

        # Prepare variables
        username = self.auth_user.keys()[0]

        dic = {"to": username.decode("utf-8"),
               "from": self.node,
               "msg": msg,
               "id": self.id}
        # Hand check
        # Send data
        xml = (u"""<?xml version='1.0' encoding='UTF-8'?><stream:stream """
               u"""xmlns='jabber:client' """
               u"""xmlns:stream='http://etherx.jabber.org/streams' """
               u"""to="%(to)s" from="%(from)s" version="1.0">""" % dic)
        logger.debug("Send Handcheck")
        so.send(xml.encode('utf-8'))

        # Read data
        try:
            data = so.recv(1024)
            #print data
        except socket.timeout:
            #print "socket.timeout"
            pass

        # Send data
        so.send("""<stream:features/>""")

        # Read data
        try:
            data = so.recv(1024)
            #print data
        except socket.timeout:
            #print "socket.timeout"
            pass

        # Send data
        xml = ("""<message xmlns="jabber:client" from="%(from)s" to="%(to)s" type="chat" """
               """id="%(id)s"><body>%(msg)s</body></message>""" % dic)
        logger.debug("Send message")
        so.send(xml.encode('utf-8'))
        try:
            data = so.recv(1024)
            #print data
        except socket.timeout:
            #print "socket.timeout"
            pass
        # Close connection
        so.close()
        logger.debug("End foward controller reply to bonjour")
        return True

    def send_sms(self, message):
        # Launch function
        logger.debug("Controller communication detected")
        params = None
        try:
            function_name, params = message.split(" ", 1)
        except ValueError, e:
            function_name = message
        except:
            return True

        try:
            getattr(self, 'function_' + function_name)(params)
        except AttributeError, e:
            self.sms_to_bonjour(self.tr("Command `%s' not found. Type `help' to see available commands" % function_name))
        except Exception, e:
            self.sms_to_bonjour(self.tr("Error in function `function_%s': %s" % (function_name, str(e))))
        return True

    def function_help(self, *args, **kargs):
        """ Return controller help
        """
        logger.debug("Controller: `help' function called")
        message = self.tr( 
                  """\nHeySms Help\n"""
                  """===========\n\n"""
                  """Show this help\t: help\n"""
                  """Add contact\t: add $CONTACT_ID$. Use `search' command before\n"""
                  """Del contact\t: del $CONTACT_ID$. Use `show' command before\n"""
                  """Search contact\t: search $CONTACT_NAME$\n"""
                  """Show contacts\t: show\n"""
                  """Echo your msg\t: echo $MESSAGE$\n"""
                  )

        self.sms_to_bonjour(message)

    def function_echo(self, message):
        """ Return your message. Usefull for tests
        """
        logger.debug("Controller: `echo' function called")
        self.sms_to_bonjour(message)

    def function_add(self, id):
        """ Active a contact in HeySms
        """
        if self.add_contact_dict is None:
            self.sms_to_bonjour(self.tr("Please use `search' command before"))
        else:
            try:
                id = int(id)
            except:
                self.sms_to_bonjour(self.tr("Bad ID: %s" % id))
                return
            if not id in self.add_contact_dict:
                self.sms_to_bonjour(self.tr("ID not found: %s" % id))
                return
            else:
                name, number = self.add_contact_dict[id]
                names = [friend.fullname for friend in self.active_contact_dict.values()]
                if name in names:
                    self.sms_to_bonjour(self.tr("\r\nContact `%s' already activated\r\n" % name))
                    return
                new_friend = Friend(name, number, self.auth_user)
                # Add to friend list in table model
                self.parent.central_widget.friends_list.emit(QtCore.SIGNAL("add_friend"), new_friend)
                # append to scheduler friend list
                self.parent.scheduler.friend_list.append(new_friend)
                new_friend.start()
                self.sms_to_bonjour(self.tr("\r\nContact `%s' activated\r\n" % name))
                self.function_show()

    def function_del(self, id):
        """ Deactive a contact in HeySms
        """
        if self.active_contact_dict is None:
            self.sms_to_bonjour(self.tr("Please use `show' command before"))
        else:
            try:
                id = int(id)
            except:
                self.sms_to_bonjour(self.tr("Bad ID: %s" % id))
                return
            if not id in self.active_contact_dict:
                self.sms_to_bonjour(self.tr("ID not found: %s" % id))
                return
            else:
                friend = self.active_contact_dict[id]
                name = friend.fullname
                self.parent.central_widget.friends_list.delete_friend(friend)
                self.sms_to_bonjour(self.tr("\r\nContact `%s' deleted\r\n" % name))
                self.function_show()
        
    def function_search(self, params):
        """ Search a contact in order to add it
        """
        logger.debug("Controller: `search' function called")
        res = search_contacts(str(params))
        self.add_contact_dict = dict([(index + 1, 
                                       (contact[0].decode('utf-8'),
                                        contact[1]))
                                      for index, contact in enumerate(res)])
        message = self.tr("\r\n\t\tSearch result\r\n  IDs\t    Names\t\t\t\tNumbers\r\n")
        message = message + "\r\n".join(["  %s\t-   %s" % (index, " :\t".join(contact)) for index, contact in self.add_contact_dict.items()])
        self.sms_to_bonjour(message)

    def function_show(self, *args, **kargs):
        """ Show active contacts
        """
        message = self.tr("\r\n\t\tActive contacts\r\n IDs\t  Favorite\t\tNames\t\t\t\tNumbers\r\n")
        self.update_active_list()
        message = message + "\r\n".join(["  %s\t-  %s\t-   %s" % (index, friend.favorite, " :\t".join((friend.fullname, friend.number))) for index, friend in self.active_contact_dict.items()])
        self.sms_to_bonjour(message)

    def update_active_list(self):
        """ Update active list
        """
        tmp_list = [friend for friend in self.parent.scheduler.friend_list if friend.number != 'N900' ]
        self.active_contact_dict = dict([(index + 1,  friend) for index, friend in enumerate(tmp_list)])
