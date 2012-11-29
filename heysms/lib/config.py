#!/usr/bin/env python
# -*- coding: UTF-8 -*-
#
#    config.py
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


import os
import subprocess
import time

from PySide import QtCore, QtGui

from lib import banner_notification
from lib import logger


languages = {u"English": "en",
             u"Français": "fr",
            }

class Config(QtCore.QSettings):
    def __init__(self, parent=None):
        QtCore.QSettings.__init__(self,
                         '/home/' + os.getenv( 'USER' ) + '/.heysms',
                         "0", parent)
        self.parent = parent
        self.last_authorized_bonjour_contact = self.value("last_authorized_bonjour_contact", '')
        if isinstance(self.last_authorized_bonjour_contact, tuple):
            self.last_authorized_bonjour_contact, _ = self.last_authorized_bonjour_contact

        # Compatibility mode
        self.use_smssend = self.value("use_smssend", QtCore.Qt.Unchecked)
        ## Useless ... I think ...
        if isinstance(self.use_smssend, tuple):
            self.use_smssend, _ = self.use_smssend

        # toggle_profile
        self.manage_profile = self.value("manage_profile", QtCore.Qt.Unchecked)
        ## Useless ... I think ...
        if isinstance(self.manage_profile, tuple):
            self.manage_profile, _ = self.manage_profile

        # startup_friends
        raw_friends = self.value("startup_friends", [])
        self.startup_friends = [str(i.toString()) for i in raw_friends]

        # start network usb
        self.useusb = self.value("use_usb", QtCore.Qt.Unchecked)
        ## Useless ... I think ...
        if isinstance(self.useusb, tuple):
            self.useusb, _ = self.useusb

        # start controler
        self.usecontroler = self.value("use_controller", QtCore.Qt.Unchecked)
        ## Useless ... I think ...
        if isinstance(self.usecontroler, tuple):
            self.usecontroler, _ = self.usecontroler

        # language
        # TODO AUTODETECTION for default
        default_lang = os.environ['LANG'].split("_")[0]
        if not default_lang in languages.values():
            default_lang = "en"
        self.language = self.value("language", default_lang)
        logger.debug("Language: %s" % self.language)

    def update_last_authorized_user(self, contact):
        self.last_authorized_bonjour_contact = contact
        self.setValue("last_authorized_bonjour_contact", QtCore.QVariant(contact))
        self.sync()

    def read_last_authorized_bonjour_contact(self):
        raw_contact = self.value("last_authorized_bonjour_contact")
        return str(raw_contact)

    def del_startup_contacts(self, friend):
        self.startup_friends.remove(friend.number)
        self.setValue("startup_friends", QtCore.QVariant(self.startup_friends))
        self.sync()

    def add_startup_contacts(self, friend):
        self.startup_friends.append(friend.number)
        self.startup_friends = list(set(self.startup_friends))
        self.setValue("startup_friends", QtCore.QVariant(self.startup_friends))
        self.sync()

    def toggle_smssend(self, state):
        self.use_smssend = state
        self.setValue("use_smssend", QtCore.QVariant(state))
        self.sync()

    def toggle_controller(self, state):
        self.setValue("use_controller", QtCore.QVariant(state))
        self.sync()

    def toggle_profile(self, state=None):
        if state is None:
            state = self.manage_profile

        if state == QtCore.Qt.Checked:
            r = os.system('/usr/bin/dbus-send '
                      '--type=method_call '
                      '--dest=com.nokia.profiled '
                      '/com/nokia/profiled '
                      'com.nokia.profiled.set_profile '
                      'string:"silent"')
            self.manage_profile = QtCore.Qt.Checked
        else:
            r = os.system('/usr/bin/dbus-send '
                      '--type=method_call '
                      '--dest=com.nokia.profiled '
                      '/com/nokia/profiled '
                      'com.nokia.profiled.set_profile '
                      'string:"general"')
            self.manage_profile = QtCore.Qt.Unchecked

        self.setValue("manage_profile",
                      QtCore.QVariant(self.manage_profile))
        self.sync()

    def init_profile(self):
        s = subprocess.Popen("/usr/bin/dbus-send "
                             "--type=method_call "
                             "--print-reply "
                             "--dest=com.nokia.profiled "
                             "/com/nokia/profiled "
                             "com.nokia.profiled.get_profile",
                             shell=True, stdout=subprocess.PIPE)
        try:
            p = s.stdout.readlines()[-1].strip()
            self.orig_profile = p.split('"')[1]
        except:
            self.orig_profile = "general"
        if self.manage_profile == QtCore.Qt.Checked:    
            self.toggle_profile()

    def toggle_useusb(self, state):
        # Save parameter
        self.setValue("use_usb", QtCore.QVariant(state))
        self.sync()

        # Start usb
        if state == QtCore.Qt.Checked:
            self.start_useusb()

        else:
            self.restore_useusb()

    def start_useusb(self):
        # Check current module
        s = subprocess.Popen("cat "
                             "/proc/driver/musb_hdrc "
                             "| "
                             "grep "
                             '"Gadget driver:" ',
                             shell=True, stdout=subprocess.PIPE)
        ret = s.stdout.readlines()
        if len(ret) > 0:
            if ret[0].find('g_file_storage') != -1:
                # Disable g_file_storage module
                s = subprocess.Popen("echo "
                         "' "
                         "/sbin/rmmod "
                         "g_file_storage "
                         "' "
                         "| "
                         "sudo "
                         "gainroot ",
                         shell=True, stdout=subprocess.PIPE)

            time.sleep(1)
            if ret[0].find('g_ether') != -1 and ret[0].find('(none)') != -1:
                banner_notification(self.tr("Please don't set USB mode"))
                return

        # Check if usb0 is used
        if ret[0].find('g_ether') != -1: 
            s = subprocess.Popen("/sbin/ifconfig "
                                 "usb0",
                                 shell=True, stdout=subprocess.PIPE)
            ret = s.stdout.readlines()
            if any([l for l in ret if l.find('addr:') != -1]):
                # usb already used
                banner_notification(self.tr("USB network is currently used ..."))
                return
        time.sleep(1)
        # mount ethernet module
        s = subprocess.Popen("echo "
                             "' "
                             "/sbin/modprobe "
                             "g_ether "
                             "' "
                             "| "
                             "sudo "
                             "gainroot ",
                             shell=True, stdout=subprocess.PIPE)
        # Waiting for mount moule
        time.sleep(1)
        # Set IP
        network = "192.168.55."
        s = subprocess.Popen("echo "
                             "' "
                             "/sbin/ifconfig "
                             "usb0 "
                             + network + "1 "
                             "netmask "
                             "255.255.255.0 "
                             "up "
                             "' "
                             "| "
                             "sudo "
                             "gainroot ",
                             shell=True, stdout=subprocess.PIPE)
        time.sleep(1)            
        # launch dhcp server (dnsmasq)
        self.dns_sp = subprocess.Popen("echo "
                             "' "
                             "/usr/sbin/dnsmasq "
                             "--no-daemon "
                             "-i "
                             "usb0 "
                             "-a "
                             + network + "1 "
                             "-I "
                             "lo "
                             "-z "
                             "--dhcp-range=" + network + "10," + network + "200,6h "
                             "--dhcp-authoritative "
                             "' "
                             "| "
                             "sudo "
                             "gainroot ",
                             shell=True, stdout=subprocess.PIPE)

    def restore_useusb(self):
        s = subprocess.Popen("pgrep "
                             "-lf "
                             "dnsmasq "
                             "| "
                             "grep "
                             '"i usb0" '
                             "| "
                             "cut "
                             "-d "
                             '" " '
                             "-f "
                             "1",
                             shell=True, stdout=subprocess.PIPE)

        for pid in s.stdout.readlines():
            s = subprocess.Popen("echo "
                                 "'"
                                 "kill "
                                 + pid +
                                 "' "
                                 "| "
                                 "sudo "
                                 "gainroot ",
                                 shell=True, stdout=subprocess.PIPE)
        time.sleep(0.5)
        s = subprocess.Popen("echo "
                             "' "
                             "/sbin/ifconfig "
                             "usb0 "
                             "down "
                             "' "
                             "| "
                             "sudo "
                             "gainroot ",
                             shell=True, stdout=subprocess.PIPE)
        s = subprocess.Popen("echo "
                             "' "
                             "/sbin/rmmod "
                             "g_ether "
                             "' "
                             "| "
                             "sudo "
                             "gainroot ",
                             shell=True, stdout=subprocess.PIPE)
        time.sleep(1)
        s = subprocess.Popen("echo "
                             "' "
                             "/sbin/modprobe "
                             "g_file_storage "
                             "' "
                             "| "
                             "sudo "
                             "gainroot ",
                             shell=True, stdout=subprocess.PIPE)

    def restore_profile(self):
        if self.manage_profile == QtCore.Qt.Checked:
            r = os.system('/usr/bin/dbus-send '
                      '--type=method_call '
                      '--dest=com.nokia.profiled '
                      '/com/nokia/profiled '
                      'com.nokia.profiled.set_profile '
                      'string:"%s"' % self.orig_profile)

    def set_language(self, lang=None, starting=False):
        if lang:
            self.language = lang

        self.setValue("language", self.language)
        self.sync()
        translator = self.parent.translator
        if translator:
            translator.load("heysms_" + self.language, "/opt/HeySms/i18n/", "_", ".qm")
            self.parent.app.installTranslator(translator)

        if not starting:
            self.parent.central_widget.retranslate()
            self.parent.menubar.retranslate()
            self.parent.main_window.conf_dialog.retranslate()
            logger.debug("Translate successfully to: %s" % self.language)


class Config_dialog(QtGui.QDialog):
    def __init__(self, parent=None):
        QtGui.QDialog.__init__(self, parent)
        self.parent = parent
        self.config = config
        self.silent_label = QtGui.QLabel(self.tr('Switch in Silent mode when HeySms starts'))
        self.silent_checkbox = QtGui.QCheckBox(self)
#        self.silent_checkbox.setCheckState(config.manage_profile)
        self.silent_checkbox.setFixedWidth(70)
        self.use_smssend_label = QtGui.QLabel(self.tr('Use Smssend to send Sms'))
        self.smssend_checkbox = QtGui.QCheckBox(self)
#        self.smssend_checkbox.setCheckState(config.use_smssend)
        self.smssend_checkbox.setFixedWidth(70)
        self.useusb_label = QtGui.QLabel(self.tr('Activate USB networking'))
        self.useusb_checkbox = QtGui.QCheckBox(self)
#        self.useusb_checkbox.setCheckState(config.useusb)
        self.useusb_checkbox.setFixedWidth(70)
        self.usecontroller_label = QtGui.QLabel(self.tr('Active Controller contact'))
        self.usecontroller_checkbox = QtGui.QCheckBox(self)
#        self.usecontroller_checkbox.setCheckState(config.usecontroler)
        self.usecontroller_checkbox.setFixedWidth(70)
        self.language_label = QtGui.QLabel(self.tr('Language'))
        self.language_combobox = QtGui.QComboBox(self)
        for name, lang in languages.items():
            self.language_combobox.addItem(name, lang)
        index = self.language_combobox.findData(config.language)
        self.language_combobox.setCurrentIndex(index)
        mainLayout = QtGui.QGridLayout()
        mainLayout.addWidget(self.silent_label, 0, 0)
        mainLayout.addWidget(self.silent_checkbox, 0, 1)
        mainLayout.addWidget(self.use_smssend_label, 1, 0)
        mainLayout.addWidget(self.smssend_checkbox, 1, 1)
        mainLayout.addWidget(self.useusb_label, 2, 0)
        mainLayout.addWidget(self.useusb_checkbox, 2, 1)
        mainLayout.addWidget(self.usecontroller_label, 3, 0)
        mainLayout.addWidget(self.usecontroller_checkbox, 3, 1)
        mainLayout.addWidget(self.language_label, 4, 0)
        mainLayout.addWidget(self.language_combobox, 4, 1)
        mainLayout.setRowStretch(0, 0)
        self.setLayout(mainLayout)
        self.setWindowTitle(self.tr('Preferences'))

        QtCore.QObject.connect(self.silent_checkbox,
                               QtCore.SIGNAL("stateChanged(int)"),
                               self.toggle_profile)
        QtCore.QObject.connect(self.smssend_checkbox,
                               QtCore.SIGNAL("stateChanged(int)"),
                               self.toggle_smssend)
        QtCore.QObject.connect(self.useusb_checkbox,
                               QtCore.SIGNAL("stateChanged(int)"),
                               self.toggle_useusb)
        QtCore.QObject.connect(self.usecontroller_checkbox,
                               QtCore.SIGNAL("stateChanged(int)"),
                               self.toggle_controller)
        QtCore.QObject.connect(self.language_combobox,
                               QtCore.SIGNAL("currentIndexChanged (int)"),
                               self.set_language)

    def retranslate(self):
        self.silent_label.setText(self.tr('Switch in Silent mode when HeySms starts'))
        self.use_smssend_label.setText(self.tr('Use Smssend to send Sms'))
        self.useusb_label.setText(self.tr('Activate USB networking'))
        self.usecontroller_label.setText(self.tr('Active Controller contact'))
        self.language_label.setText(self.tr('Language'))
        self.setWindowTitle(self.tr('Preferences'))

    def toggle_useusb(self, state):
        config.toggle_useusb(state)

    def toggle_profile(self, state):
        config.toggle_profile(state)

    def toggle_controller(self, state):
        config.toggle_controller(state)
        if state == QtCore.Qt.Checked:
            # Start controller
            self.config.parent.scheduler.start_controller()
            self.config.parent.scheduler.controller.function_help()
        else:
            # Stop controller
            self.config.parent.scheduler.stop_controller()

    def toggle_smssend(self, state):
        s = subprocess.Popen("/usr/bin/which "
                             "smssend ",
                             shell=True, stdout=subprocess.PIPE)
        res = s.stdout.readlines()
        smssend_installed = False 
        if len(res) == 1:
            smssend_installed = True 

        if not smssend_installed:
            banner_notification(self.tr("You need to install smssend"))
            QtCore.QObject.disconnect(self.smssend_checkbox,
                               QtCore.SIGNAL("stateChanged(int)"),
                               self.toggle_smssend)
            self.smssend_checkbox.setCheckState(QtCore.Qt.Unchecked)
            QtCore.QObject.connect(self.smssend_checkbox,
                               QtCore.SIGNAL("stateChanged(int)"),
                               self.toggle_smssend)
            return

        state = self.smssend_checkbox.checkState()
        config.toggle_smssend(state)
    
    def set_language(self, index_lang):
        lang = self.language_combobox.itemData(index_lang).toString()
        config.set_language(lang)

config = Config()
