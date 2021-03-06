# -*- coding: utf-8 -*-
"""
/***************************************************************************
 BiotopManager
                                 A QGIS plugin
 Dieses Plugin verwaltet Biotope
 Generated by Plugin Builder: http://g-sherman.github.io/Qgis-Plugin-Builder/
                              -------------------
        begin                : 2018-06-27
        git sha              : $Format:%H$
        copyright            : (C) 2018 by GBD GmbH
        email                : gebbert@gbd-consult.de
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""
from qgis.core import Qgis, QgsMessageLog
import sys


def qgis_log(message: str, level: int = Qgis.Info) -> None:
    """This function log messages to the QGIS terminal

    Args:
        message: the message
        level: Qgis.Info, Qgis.Warning, Qgis.Critical
    """
    if sys.stderr:
        sys.stderr.write(message + "\n")
    QgsMessageLog.logMessage(message=message, level=level, tag="biotopmanager")
