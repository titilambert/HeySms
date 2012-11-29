#!/usr/bin/env python
# -*- coding: UTF-8 -*-
#
#    call_listener.py
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


import time

import dbus
from dbus.mainloop.glib import DBusGMainLoop
from PySide import QtCore

from scheduler import recv_sms_q
from lib import logger, search_contact_by_number


class Call_listener(QtCore.QThread):
    def __init__(self, parent):
        QtCore.QThread.__init__(self)
        self.parent = parent

    def callback(self, obj_path, callernumber):
        callernumber = str(callernumber)
        fullname = search_contact_by_number(callernumber)
        try:
            # If number not found in contacts list
            fullname = int(fullname)
        except ValueError, e:
            pass
        logger.debug("New incoming call from: %s" % fullname)
        message = self.tr("New incoming call from: %s" % fullname)
        recv_sms_q.put({'phone_number': 'N900',
                        'message': message})

    def run(self):
        DBusGMainLoop(set_as_default=True)
        bus = dbus.SystemBus()
        bus.add_signal_receiver(self.callback,
                                path='/com/nokia/csd/call',
                                dbus_interface='com.nokia.csd.Call',
                                signal_name='Coming')
        import gobject
        from dbus import glib
        gobject.threads_init()
        glib.threads_init()
