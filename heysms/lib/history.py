#!/usr/bin/env python
# -*- coding: UTF-8 -*-
#
#    history.py
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


import datetime

from PySide import QtSql

db = QtSql.QSqlDatabase("QSQLITE")
db.setDatabaseName("/home/user/.rtcom-eventlogger/el-v1.db")


def insert_sms_in_history(sms):
    global db

    # Pre
    num = sms['num']
    if not sms['message']:
        return
    msg = sms['message'].encode('utf-8').decode('utf-8')
    group_uid = str(num[-7:])
    now = int(datetime.datetime.now().strftime("%s"))

    db.open()
    query = QtSql.QSqlQuery(db)
    query.prepare("""INSERT INTO Events (service_id, event_type_id,
                     storage_time, start_time, end_time, is_read,
                     outgoing, flags, bytes_sent, bytes_received,
                     local_uid, local_name, remote_uid, channel,
                     free_text, group_uid)
                     VALUES (:service_id, :event_type_id,
                     :storage_time, :start_time, :end_time, :is_read,
                     :outgoing, :flags, :bytes_sent, :bytes_received,
                     :local_uid, :local_name, :remote_uid, :channel,
                    :free_text, :group_uid)"""
                    )

    query.bindValue(":service_id", 3)
    query.bindValue(":event_type_id", 11)
    query.bindValue(":storage_time", now)
    query.bindValue(":start_time", now)
    query.bindValue(":end_time", 0)
    query.bindValue(":is_read", 1)
    query.bindValue(":outgoing", 1)
    query.bindValue(":flags", 0)
    query.bindValue(":bytes_sent", 0)
    query.bindValue(":bytes_received", 0)
    query.bindValue(":local_uid", "ring/tel/ring")
    query.bindValue(":local_name", "<SelfHandle>")
    query.bindValue(":remote_uid", num)
    query.bindValue(":channel", "")
    query.bindValue(":free_text", msg)
    query.bindValue(":group_uid", group_uid)
    status = query.exec_()

    db.close()
