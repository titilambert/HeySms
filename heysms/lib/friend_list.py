#!/usr/bin/env python
# -*- coding: UTF-8 -*-
#
#    fried_list.py
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
import os
from datetime import datetime
from time import sleep
from optparse import OptionParser

from PySide import QtCore, QtGui
from friend import Friend
from lib import logger
from config import config


class Delete_button(QtGui.QPushButton):
    def __init__(self, friend, parent=None):
        QtGui.QPushButton.__init__(self, parent)
        self.friend = friend
        self.parent = parent
        delete_icon = QtGui.QIcon('/usr/share/icons/hicolor/48x48/hildon'
                                  '/general_close.png')
        self.setIcon(delete_icon)
        self.setFixedWidth(80)
 
        QtCore.QObject.connect(self,
                               QtCore.SIGNAL("pressed ()"),
                               self.delete)
    def delete(self):
        logger.debug("Delete friend: %s" % self.friend.fullname)
        self.parent.delete_friend(self.friend)


class Favorite_button(QtGui.QPushButton):
    def __init__(self, friend, parent=None):
        QtGui.QPushButton.__init__(self, parent)
        self.friend = friend
        self.parent = parent

        if friend.favorite == True:
            favorite_icon = QtGui.QIcon('/usr/share/icons/hicolor/32x32/apps'
                                        '/favorite.png')
            #favorite_icon = QtGui.QIcon('/home/user/heysms/heysms/images/favorite.png')
        else:
        
            favorite_icon = QtGui.QIcon('/usr/share/icons/hicolor/32x32/apps'
                                        '/non-favorite.png')
            #favorite_icon = QtGui.QIcon('/home/user/heysms/heysms/images/non-favorite.png')
        self.setIcon(favorite_icon)
        self.setFixedWidth(80)

        QtCore.QObject.connect(self,
                               QtCore.SIGNAL("pressed ()"),
                               self.toggle_favorite)

    def toggle_favorite(self):
        if self.friend.favorite == False:
            favorite_icon = QtGui.QIcon('/usr/share/icons/hicolor/32x32/apps'
                                        '/favorite.png')
            self.friend.favorite = True
            config.add_startup_contacts(self.friend)
        else:
            favorite_icon = QtGui.QIcon('/usr/share/icons/hicolor/32x32/apps'
                                        '/non-favorite.png')
            self.friend.favorite = False
            config.del_startup_contacts(self.friend)

        logger.debug("Toggle favorite friend: %s to %s" % (self.friend.fullname,
                                                           self.friend.favorite))
        self.setIcon(favorite_icon)


class Friend_list_widget(QtGui.QTableWidget):
    def __init__(self, parent=None):
        QtGui.QTableWidget.__init__(self, parent)
        self.parent = parent
        self.setColumnCount(3)
        self.friend_list = []

        self.horizontalHeader().hide()
        self.verticalHeader().hide()
        self.setShowGrid(False)
        self.horizontalHeader().setResizeMode(0, QtGui.QHeaderView.Stretch)
        self.horizontalHeader().setResizeMode(1, QtGui.QHeaderView.Fixed)
        self.horizontalHeader().setResizeMode(2, QtGui.QHeaderView.Fixed)
        self.horizontalHeader().resizeSection (1, 100)
        self.horizontalHeader().resizeSection (2, 80)
        self.setSelectionMode(QtGui.QAbstractItemView.NoSelection)
        self.setGridStyle(QtCore.Qt.NoPen)

        QtCore.QObject.connect(self,
                               QtCore.SIGNAL("add_friend"),
                               self.add_friend)

    def add_friend(self, friend):
        row = self.rowCount()
        self.insertRow(row)
        name = QtGui.QTableWidgetItem(friend.fullname)
        self.setItem(row, 0, name)

        self.favorite_button = Favorite_button(friend, self)
        self.setCellWidget(row, 1, self.favorite_button)

        delete_button = Delete_button(friend, self)
        self.setCellWidget(row, 2, delete_button)

        self.setRowHeight(row, 80)
        self.friend_list.append(friend)

    def delete_friend(self, friend):
        friend.close()
        row = self.friend_list.index(friend)
        self.removeRow(row)
        self.parent.parent.scheduler.friend_list.remove(friend)
        self.friend_list.remove(friend)
