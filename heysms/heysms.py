#!/usr/bin/env python
# -*- coding: UTF-8 -*-
#
#    heysms.py
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


import sys
import re
import os
from datetime import datetime
import bsddb
from time import sleep
from optparse import OptionParser

from PySide import QtCore, QtGui
try:
    import osso
except:
    pass

from lib.lib import banner_notification, list_presence_users
from lib.server import Bonjour_server
from lib.sms_listener import Sms_listener
from lib.call_listener import Call_listener
from lib.scheduler import Scheduler
from lib.lib import logger
from lib.friend import Friend
from lib.config import config, Config_dialog
from lib.friend_list import Friend_list_widget


class MenuBar(QtGui.QMenuBar):
    def __init__(self, parent=None, ):
        QtGui.QMenuBar.__init__(self, parent)
        self.setObjectName("Menu")
        self.preference = self.addAction(self.tr("&Preferences"))
        self.add_friend = self.addAction(self.tr("Add &friend"))
        self.about = self.addAction(self.tr("&About"))
        ## Quit
        self.quit = self.addAction(self.tr("&Quit"))

    def retranslate(self):
        self.preference.setText(self.tr("&Preferences"))
        self.add_friend.setText(self.tr("Add &friend"))
        self.about.setText(self.tr("&About"))
        self.quit.setText(self.tr("&Quit"))


class Central_widget(QtGui.QWidget):
    def __init__(self, parent):
        QtGui.QWidget.__init__(self)
        self.parent = parent

        # Load gui items
        self.bonjour_users_label = QtGui.QLabel(self.tr('Select your Bonjour '
                                                'contact id :'))
        self.bonjour_users_label.setFixedHeight(50)
        self.bonjour_users = QtGui.QComboBox()
        icon = QtGui.QIcon('/usr/share/icons/hicolor/48x48/hildon'
                           '/general_refresh.png')
        self.reload_bonjour_users_button = QtGui.QPushButton()
        self.reload_bonjour_users_button.setIcon(icon)
        self.reload_bonjour_users_button.setFixedWidth(80)
        self.empty = QtGui.QLabel('')
        self.friend_list_label = QtGui.QLabel(self.tr('Friend list :'))
        self.friends_list = Friend_list_widget(self)
        mainLayout = QtGui.QGridLayout()
        mainLayout.addWidget(self.bonjour_users_label, 0, 0, 1, 2)
        mainLayout.addWidget(self.bonjour_users, 1, 0)
        mainLayout.addWidget(self.reload_bonjour_users_button, 1, 1)
        
        mainLayout.addWidget(self.empty, 4, 0, 1, 2)
        mainLayout.addWidget(self.friend_list_label, 5, 0, 1, 2)
        mainLayout.addWidget(self.friends_list, 6, 0, 1, 2)

        mainLayout.setRowStretch(0, 0)
        self.setLayout(mainLayout)

    def retranslate(self):
        self.bonjour_users_label.setText(self.tr('Select your Bonjour '
                                                'contact id :'))
        self.friend_list_label.setText(self.tr('Friend list :'))

    def reload_contacts(self):
#        self.parent.main_window.setAttribute(
#                                    QtCore.Qt.WA_Maemo5ShowProgressIndicator,
#                                    True)
        # Read last bonjour_contact used
        last_authorized_bonjour_contact = config.read_last_authorized_bonjour_contact()

        self.parent.main_window.repaint()
        banner_notification(self.tr("Looking for Bonjour contacts ..."))
        self.parent.bonjour_users = list_presence_users()
        self.bonjour_users.clear()
        if len(self.parent.bonjour_users) == 0:
            banner_notification(self.tr("No Bonjour contacts found !"))
        else:
            node_friend_list = [f.node for f in 
                                self.parent.scheduler.friend_list]
            for bonjour_user, info in self.parent.bonjour_users.items():
                # if the contact was create by heysms
                # we don't want to see it in the list
                bonjour_user = bonjour_user.decode('utf-8')
                if bonjour_user in node_friend_list:
                    continue
                self.bonjour_users.addItem(bonjour_user)
            # Search in list last bonjour_contact used
            index = self.bonjour_users.findText(last_authorized_bonjour_contact)
            if index != -1:
                # Select last bonjour_contact used
                logger.debug("Last Bonjour contact found: %s, we select it" % last_authorized_bonjour_contact)
                self.bonjour_users.setCurrentIndex(index)

            banner_notification(self.tr("Bonjour contacts loaded !"))

#        self.parent.main_window.setAttribute(
#                                    QtCore.Qt.WA_Maemo5ShowProgressIndicator,
#                                    False)


class Ui_MainWindow(QtCore.QObject):
    def __init__(self, app, translator):
        QtCore.QObject.__init__(self)
        self.app = app
        self.friend_list = []
        self.bonjour_auth_user = ''
        self.bonjour_users = {}
        self.translator = translator

    def setupUi(self, main_window):
        self.main_window = main_window
        self.main_window.setObjectName("MainWindow")
        self.main_window.resize(800, 400)
        icon = QtGui.QIcon('/usr/share/icons/hicolor/128x128/apps'
                           '/heysms.png')
        self.main_window.setWindowIcon(icon)

        self.central_widget = Central_widget(self)
        self.main_window.setCentralWidget(self.central_widget)
        self.main_window.conf_dialog = Config_dialog(self.main_window)
        # Load saved config
        config.init_profile()
        if config.useusb == QtCore.Qt.Checked:
            config.start_useusb()

        ### Menu
        self.menubar = MenuBar(self.main_window)
        self.main_window.setMenuBar(self.menubar)

        QtCore.QMetaObject.connectSlotsByName(self.main_window)

        # Signals
        QtCore.QObject.connect(self.central_widget.reload_bonjour_users_button,
                               QtCore.SIGNAL("pressed ()"),
                               self.central_widget.reload_contacts)
        QtCore.QObject.connect(self.central_widget.bonjour_users,
                               QtCore.SIGNAL("currentIndexChanged "
                                             "(const QString&)"),
                               self.change_bonjour_user)

        QtCore.QObject.connect(self.menubar.preference,
                               QtCore.SIGNAL("triggered()"),
                               self.main_window.conf_dialog.exec_)

        QtCore.QObject.connect(self.menubar.add_friend,
                               QtCore.SIGNAL("triggered()"),
                               self.add_friend)

        QtCore.QObject.connect(self.menubar.about,
                               QtCore.SIGNAL("triggered()"),
                               self.show_about)
        ## Quit
        QtCore.QObject.connect(self.menubar.quit,
                               QtCore.SIGNAL("triggered()"),
                               self.app.quit)

    def toggle_server(self):
        if not hasattr(self, 'bs'):
            self.bonjour_auth_user = self.central_widget.bonjour_users\
                                         .currentText()
            self.bs = Bonjour_server(self.bonjour_auth_user)
        if not self.bs.is_running():
            self.bs.listen()

    def change_bonjour_user(self, new_bonjour_user):
        if not hasattr(self, 'bs'):
            self.toggle_server()
        else:
            self.bs.set_auth(new_bonjour_user)
            self.bonjour_auth_user = new_bonjour_user
            self.scheduler.set_auth(new_bonjour_user)
            config.update_last_authorized_user(new_bonjour_user)

    def add_friend(self):
        friends_dialog = QtGui.QInputDialog(self.main_window)
        friends_dialog.setComboBoxEditable(0)
        friends_dialog.setOkButtonText(self.tr("Done"))
        db = bsddb.hashopen('/home/user/.osso-abook/db/addressbook.db', 'r')
        friend_list = {}
        old_friend_list = [f.fullname for f in self.scheduler.friend_list]
        q_friend_dict = {}
        for contact in db.values():
#            logger.debug("Trying to find name and "
#                         "cell number in: %s" % contact.split('\n'))
            reg = re.compile('FN:(.*?)\\r', re.S|re.M)
            numbers = re.findall("TEL;TYPE=.*?CELL.*?:(.[0-9]*)\r\n", contact)
            m = re.search(reg, contact)
            if m is None:
                logger.debug("No name in contact")
                continue
            elif not numbers:
                logger.debug("No cell phone found")
                continue

            name = m.group(1).decode('utf-8')
            for num in numbers:
                logger.debug("Found : %s - %s" % (name, num))
                if name in old_friend_list:
                    logger.debug("Friend already in list: %s" % name)
                    continue

                i = 1
                while name in friend_list:
                    name = name + " (%s)" % str(i)
                    i = i + 1

                # Prepare lists
                friend_list[num] = name
                q_friend_dict["%s - %s" % (name, num)] = num

        q_friend_list = QtCore.QStringList(sorted(q_friend_dict.keys()))
        friends_dialog.setComboBoxItems(q_friend_list)
        friends_dialog.setWindowTitle(self.tr("Add a friend"))
        friends_dialog.setLabelText(self.tr("Select a friend"))
        ret = friends_dialog.exec_()

        if ret == 0:
            logger.debug("Dialog not confirmed")
            return

        raw_name = unicode(friends_dialog.textValue())
        number = q_friend_dict[raw_name]
        select_friend = friend_list[number]
        bonjour_auth_username = str(self.bonjour_auth_user)
        auth_user = {bonjour_auth_username:
                self.bonjour_users[bonjour_auth_username]}

        # Check if friend is already in friend list
        if select_friend in old_friend_list:
                logger.debug("Selected friend already in list: %s" % select_friend)
                return

        new_friend = Friend(select_friend, number, auth_user)
        # Add to friend list in table model
        self.central_widget.friends_list.emit(QtCore.SIGNAL("add_friend"), new_friend)
        # append to scheduler friend list
        self.scheduler.friend_list.append(new_friend)
        # Register it on bonjour
        new_friend.start()

    def show_about(self):
        icon = QtGui.QIcon('/usr/share/icons/hicolor/48x48/hildon'
                           '/general_refresh.png')
        vars = {}
        vars['version'] = "1.7.2"
        message = QtCore.QString(self.tr("""<center><h2>HeySms</h2></center>"""
                                 """<center>Version: %(version)s</center>"""
                                 """<br/>Visite web site: <a href="http://talk.maemo.org/showthread.php?t=84705">Here</a> """
                                 """<br/>Report bugs: <a href="https://github.com/titilambert/HeySms/issues?milestone=&page=1&state=open">Here</a> """
                                 """<br/>Thanks: """
                                 """<ul>"""
                                 """<li>My Doudoune</li>"""
                                 """<li>David Rodigari</li>"""
                                 """<li>Oskar Welzl</li>"""
                                 """<li>Stefan Siegl</li>"""
                                 """</ul>"""
                                 """ """ % vars))
        QtGui.QMessageBox.about(self.main_window, self.tr("About"), message)


def main():

    def exit():
        logger.debug("Stopping active friends")
        for f in ui.friend_list:
            f.close()
        logger.debug("Shutdown scheduler")
        ui.scheduler.must_run = False
        while ui.scheduler.isRunning():
            logger.debug("Waiting scheduler")
            if ui.scheduler.waiting_authorized_contact == True:
                break
            sleep(0.1)
        logger.debug("Restore profile")
        config.restore_profile()
        if config.useusb == QtCore.Qt.Checked:
            logger.debug("Restore USB")
            config.restore_useusb()

    opt_parser = OptionParser()
    opt_parser.add_option("-d", "--debug", dest="debug_mode",
                          action="store_true",
                          default='False', help="Debug mode")

    translator = QtCore.QTranslator()
    app = QtGui.QApplication(sys.argv)
#    app.setOrganizationName("HeySms")
#    app.setOrganizationDomain("HeySms")
    app.setApplicationName("HeySms")
    (options, args) = opt_parser.parse_args([str(i) for i in app.arguments()])
    logger.set_debug(options.debug_mode)
    
    ui = Ui_MainWindow(app, translator)
    config.parent = ui
    config.set_language(starting=True)
    main_window = QtGui.QMainWindow()
    ui.setupUi(main_window)

    ui.call_listener = Call_listener(ui)
    ui.call_listener.start()
    logger.debug("Call_listener started")
    ui.sms_listener = Sms_listener(ui)
    ui.sms_listener.start()
    logger.debug("Sms_listener started")
    ui.scheduler = Scheduler(ui)
    ui.scheduler.start()
    logger.debug("Scheduler started")

    main_window.setWindowTitle("HeySms")
#    main_window.setAttribute(QtCore.Qt.WA_Maemo5AutoOrientation, True)
    main_window.app = app
    main_window.show()
    main_window.repaint()
    ui.central_widget.repaint()
    ui.central_widget.reload_contacts()


    QtCore.QObject.connect(app,
                           QtCore.SIGNAL("aboutToQuit()"),
                           exit)

    sys.exit(app.exec_())
