#!/usr/bin/env python
# -*- coding: UTF-8 -*-
#
#    friend.py
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

import dbus
from PySide import QtCore, QtNetwork, QtGui

import pybonjour
from lib_sms import createPDUmessage
from lib import logger
from config import config

port = 5299


class Friend(QtCore.QThread):
    def __init__(self, fullname, number, auth_user, parent=None):
        QtCore.QThread.__init__(self, parent)
        self.fullname = fullname
        self.number = number
        self.port = port
        self.auth_user = auth_user
        self.node = "%s@n900" % ''.join(c for c in self.fullname if c.isalnum()).lower()
        self.favorite = False

        self.parent = parent
        self.client = None  # Bonjour socket client
        self.is_ready = False
        self.id = 0

    def set_data(self, value, attr):
        """ For view
        """
        if attr == "favorite":
            value, bool = value.toInt()
            if bool:
                if value == QtCore.Qt.Checked:
                    setattr(self, "favorite", QtCore.Qt.Checked)
                else:
                    setattr(self, "favorite", QtCore.Qt.Unchecked)

                return True
        return False

    def _register_callback(self, sdRef, flags, errorCode,
                           name, regtype, domain):
        # Set variable when self is registered
        sleep(1)
        self.is_ready = True
        logger.debug("Bonjour contact registered: %s" % self.fullname)

    def run(self):
        # Register on bonjour chat
        self.id = random.randint(100000000000, 999999999999)
        txt = {}
        txt['1st'] = self.fullname
        txt['last'] = ""
        txt['status'] = 'avail'
        txt['port.p2pj'] = self.port
        txt['nick'] = self.fullname
#        txt['node'] = self.node
        txt['jid'] = self.node
        txt['email'] = self.node
        txt['version'] = 1
        txt['txtvers'] = 1
        logger.debug("txt register: %s" % str(txt))

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

    def send_sms(self, message):
        if config.use_smssend == 0: 
            logger.debug("Sending sms using 'dbus'")
            bus = dbus.SystemBus()
            smsobject = bus.get_object('com.nokia.phone.SMS',
                                       '/com/nokia/phone/SMS/ba212ae1')
            smsiface = dbus.Interface(smsobject, 'com.nokia.csd.SMS.Outgoing')
            message = message.encode('utf-8')
            logger.debug("to: %s " % self.number)
            logger.debug("send sms: %s " % message)

            pdus = createPDUmessage(self.number, message)

            for pdu in pdus:
                arr = dbus.Array(pdu)

                msg = dbus.Array([arr])
                while True:
                    try:
                        logger.debug("Sending sms: %s" % msg)
                        smsiface.Send(msg, '')
                        break
                    except dbus.exceptions.DBusException, e:
                        logger.debug("Sending sms failed, error: %s" % str(e))
                        logger.debug("Retrying")
                        pass
                logger.debug("Sms send: %s" % msg)
        else:
            logger.debug("Sending sms using 'smssend'")
            message = message.replace('"', '\\"')
            s = subprocess.Popen("/usr/bin/smssend "
                             "-s "
                             "-n "
                             "%s "
                             "-m "
                             '"%s" ' % (self.number, message),
                             shell=True, stdout=subprocess.PIPE)
            res = s.stdout.readlines()
            if any([i for i in res if i.find('OK') != -1]):
                logger.debug("Sms send: %s" % message)
            else:
                self.send_sms(message)
                logger.debug("Sending sms failed")
                logger.debug("Retrying")

    def sms_to_bonjour(self, msg):
        logger.debug("Forward sms to bonjour")
        msg = msg.replace("<", "&lt;")
        msg = msg.replace(">", "&gt;")
        # Waiting self is bonjour registered
        while self.is_ready == False:
            logger.debug("Waiting bonjour contact "
                         "registered: %s" % self.fullname)
            sleep(1)

        # Connect to bonjour server
        host = self.auth_user.values()[0]['host']
        port = self.auth_user.values()[0]['port']
        so = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        logger.debug("Connecting to %s:%s" % (host, port))
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
        dic = {"to": username,
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
        xml = (u"""<message from="%(from)s" to="%(to)s" type="chat" """
               u"""id="%(id)s"><body>%(msg)s</body></message>""" % dic)
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
        logger.debug("End foward sms to bonjour")
        return True
