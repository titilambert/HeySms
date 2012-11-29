#!/usr/bin/env python
# -*- coding: UTF-8 -*-
#
#    server.py
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


import socket
from time import sleep
import asyncore
import socket
from xml.sax.saxutils import unescape

from PySide import QtCore
from PySide import QtNetwork

from BeautifulSoup import BeautifulSoup
from scheduler import send_sms_q
from lib import logger


class Bonjour_server():
    def __init__(self, auth_user):
        self.host = '0.0.0.0'
        self.port = 5299
        self.auth_user = auth_user
        self.server = self.Server(self)

    def get_user(self, soup):
        """ Get target user ( friend cell phone number )
        """
        attrs = dict(soup.first().attrs)
        if 'to' in attrs.keys():
            if attrs['to'] != '':
                return attrs['to']
        return False

    def check_auth(self, soup):
        """ Check bonjour sender username
        """
        attrs = dict(soup.first().attrs)
        if 'from' in attrs.keys():
            if attrs['from'] == unicode(self.auth_user):
                return True
        return False

    def set_auth(self, username):
        """ Set bonjour user which receive and send sms
        """
        self.auth_user = username

    def listen(self):
        self.server.start()

    def is_running(self):
        return self.server.isListening()

    def stop(self):
        self.server.close()

    class Server(QtNetwork.QTcpServer):
        def __init__(self, parent):
            QtNetwork.QTcpServer.__init__(self)
            self.parent = parent
            self.auth_user = self.parent.auth_user
            self.host = QtNetwork.QHostAddress(self.parent.host)
            self.port = self.parent.port

        def start(self):
            i = 0
            ret = self.listen(self.host, self.port)
            while not ret:
                ret = self.listen(self.host, self.port + i)
                i = i + 1
                self.port = self.port + i
            logger.debug("Bonjour server listen on port %s" % self.port)
            QtCore.QObject.connect(self,
                                   QtCore.SIGNAL("newConnection()"),
                                   self.accept_new_connection)

        def accept_new_connection(self):
            sock = self.nextPendingConnection()
            self.connect(sock, QtCore.SIGNAL("readyRead()"), self.tcpsocket_ready_to_read)

        def tcpsocket_ready_to_read(self):
            sock = self.sender()   
            recvData = str(sock.readAll())
            ###### First msg ######
            logger.debug("New Bonjour message received")
            if recvData.find("<message") != -1:
                # for kopete which send only one request
                i = recvData.find("<message")
                recvData = recvData[i:]

            if recvData.startswith("<?xml version"):
                # Test if is authorized user
                soup = BeautifulSoup(recvData)
                if not self.parent.check_auth(soup):
                    logger.debug("Bonjour message received "
                                 "from unauthorized user")
                    sock.close()
                    return

                # Get target user ( friend cell phone number)
                user = self.parent.get_user(soup)
                if user == False:
                    # User not found
                    sock.close()
                    return

                logger.debug("Bonjour message received "
                             "from authorized user: %s" % user)
                # First reply
                sendData = (u"""<?xml version='1.0' encoding='UTF-8'?>"""
                     u"""<stream:stream xmlns='jabber:client' """
                     u"""xmlns:stream='http://etherx.jabber.org/streams'"""
                     u""" to="%s" from="%s" version="1.0">"""
                     % (self.auth_user, user))
                sock.write(sendData.encode('utf-8'))

                sock.waitForReadyRead()
                recvData = str(sock.readAll())

            ###### Second msg ######
            if recvData == "<stream:features/>":
                sendData = """<stream:features />"""
                sock.write(sendData)
                sock.waitForReadyRead()
                recvData = str(sock.readAll())

            if recvData.startswith("<message"):
                soup = BeautifulSoup(recvData)
                if not self.parent.check_auth(soup):
                    sock.close()
                    return
                # Get user whowill receive sms
                user = self.parent.get_user(soup)
                # Get Message
                root = soup.first()
                message = root.findChild('body').getString()
                message = unescape(message, {"&apos;": "'", "&quot;": '"'})

                logger.debug("New sms for %s queued" % user)
                logger.debug("New sms content %s" % message)
                # Put message in sms queue
                if message:
                    send_sms_q.put({'to': user,
                           'message': message
                           })
                else:
                    # NOTIFY ???
                    # messag empty ????
                    pass

            sock.close()
