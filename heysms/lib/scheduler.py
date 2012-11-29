#!/usr/bin/env python
# -*- coding: UTF-8 -*-
#
#    scheduler.py
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


import Queue
from time import sleep

from PySide import QtCore

from friend import Friend
from lib import search_contact_by_number, banner_notification
from lib import logger
from history import insert_sms_in_history
from config import config
from controller import Controller

recv_sms_q = Queue.Queue()
send_sms_q = Queue.Queue()
sms_history_q = Queue.Queue()
incoming_call_q = Queue.Queue()


class Scheduler(QtCore.QThread):
    def __init__(self, parent):
        QtCore.QThread.__init__(self)
        self.friend_list = []
        self.parent = parent
        self.must_run = False
        self.waiting_authorized_contact = False

    def run(self):
        while self.parent.bonjour_auth_user == '':
            logger.debug("Waiting selection of an authorized bonjour contact")
            self.waiting_authorized_contact = True
            sleep(1)
        self.waiting_authorized_contact = False

        bonjour_auth_username = unicode(self.parent.bonjour_auth_user).encode("utf-8")
        self.auth_user = {bonjour_auth_username:
                            self.parent.bonjour_users[bonjour_auth_username]}

        self.add_starting_friends()

        if config.usecontroler == QtCore.Qt.Checked:
            # Startup controller
            self.start_controller()

        self.must_run = True
        while self.must_run:
            sleep(0.1)
            if not recv_sms_q.empty():
                new_sms = recv_sms_q.get()
                status = self.sms_received(new_sms['phone_number'],
                              new_sms['message'])
                if status:
                    recv_sms_q.task_done()
            if not send_sms_q.empty():
                new_sms = send_sms_q.get()
                self.send_sms(new_sms['to'],
                              new_sms['message'])
                send_sms_q.task_done()
            if not sms_history_q.empty():
                sms = sms_history_q.get()
                insert_sms_in_history(sms)
                sms_history_q.task_done()

    def stop_controller(self):
        self.controller.close()

    def start_controller(self):
        self.controller = Controller(self.auth_user, self.parent)
        self.controller.start()
        self.friend_list.append(self.controller)

    def add_starting_friends(self):
        friend_numbers = config.startup_friends
        for number in friend_numbers:
            logger.debug("This is a starting friend: %s" % number)
            fullname = search_contact_by_number(number)
            # Save it !
            while self.parent.bonjour_auth_user == '':
                logger.debug("Waiting selection of an authorized bonjour contact")
                sleep(1)
            bonjour_auth_username = unicode(self.parent.bonjour_auth_user).encode("utf-8")
            auth_user = {bonjour_auth_username:
                            self.parent.bonjour_users[bonjour_auth_username]}
            new_friend = Friend(fullname, number, auth_user)
            new_friend.favorite = True
            # Add to friend list in table model
            self.parent.central_widget.friends_list.emit(QtCore.SIGNAL("add_friend"), new_friend)
            # append to friend list
            self.friend_list.append(new_friend)
            # Register it on bonjour
            new_friend.start()

    def set_auth(self, bonjour_auth_user):
        bonjour_auth_username = unicode(self.parent.bonjour_auth_user).encode("utf-8")
        if bonjour_auth_username:
            auth_user = {bonjour_auth_username:
                     self.parent.bonjour_users[bonjour_auth_username]}
            logger.debug("Bonjour contact which receive message: %s" % auth_user)
            for f in self.friend_list:
                f.auth_user = auth_user
        else:
            banner_notification(self.tr("Avahi error, please restart HeySms"))

    def send_sms(self, to, msg):
        logger.debug("Send sms to: %s" % to)
        logger.debug("Sms content: %s" % msg)
        node_list = [friend.node for friend in self.friend_list]
        try:
            i = node_list.index(to)
        except ValueError:
            # Impossible ?
            logger.debug("User not find in list: %s" % to)
            return
        friend = self.friend_list[i]
        controller = friend.send_sms(msg)
        if not controller:
            sms_history_q.put({'message': msg, 'num': friend.number})

    def sms_received(self, sender, msg):
        logger.debug("New sms from: %s" % sender)
        self.number_list = [friend.number for friend in self.friend_list]
        if not sender in self.number_list:
            # Create a new friend
            logger.debug("This is a new friend: %s" % sender)
            fullname = search_contact_by_number(str(sender))
            number = str(sender)
            # Save it !
            bonjour_auth_username = str(self.parent.bonjour_auth_user)
            auth_user = {bonjour_auth_username:
                            self.parent.bonjour_users[bonjour_auth_username]}
            new_friend = Friend(fullname, number, auth_user)
            # Add to friend list in table model
            self.parent.central_widget.friends_list.emit(QtCore.SIGNAL("add_friend"), new_friend)
            # append to friend list
            self.friend_list.append(new_friend)
            # Register it on bonjour
            new_friend.start()
            friend = new_friend
        else:
            i = self.number_list.index(sender)
            friend = self.friend_list[i]
            logger.debug("This is an old friend: %s" % sender)
        # SMS to bonjour
        logger.debug("Forward sms to bonjour")
        try:
            ret = friend.sms_to_bonjour(msg)
            logger.debug("sms_to_bonjour return: %s" % str(ret))
            return ret
        except Exception, e:
            logger.debug("sms_to_bonjour error: %s" % str(e))
            return False
