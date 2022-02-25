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

import pprint
import sys
import traceback

from PyQt5 import Qt
from PyQt5.QtWidgets import QMessageBox
from qgis.gui import QgisInterface

from biotopmanager.common.transaction import BiotopTransactions
from biotopmanager.common.layer_manager import LayerManager
from biotopmanager.common.exception_handling import UnabelToLock, UnabelToUnLock
from biotopmanager.common.configuration import Configuration
from biotopmanager.common.locking import BiotopeLocking
from biotopmanager.common.user_credentials import PostgresUser
from biotopmanager.delete_dialog import DeleteDialog


def showExceptionError(e: Exception):
    e_type, e_value, e_traceback = sys.exc_info()
    message = [e.__class__, e_type, e_value, traceback.format_tb(e_traceback)]
    message = pprint.pformat(message)
    header = "Folgender Fehler ist während der Bearbeitung aufgetreten:\n\n"
    QMessageBox.critical(None, "Fehler", header + str(message))


def start_biotop_editing(iface: QgisInterface):
    """Start editing in the edit layer and  trigger the add feature tool
    """
    lm = LayerManager()

    try:
        iface.setActiveLayer(lm.edit_layer)
        lm.edit_layer.startEditing()
        iface.mapCanvas().refreshAllLayers()
        iface.actionAddFeature().trigger()
    except UnabelToLock as e:
        QMessageBox.critical(iface.mainWindow(), "Fehler", str(e))
    except Exception as e:
        showExceptionError(e=e)


def transfer_from_biotop_to_edit(iface: QgisInterface):
    """Transfer selected biotope into the edit layer
    """
    bt = BiotopTransactions()
    lm = LayerManager()

    source_layer = lm.biotope_layer
    if source_layer:
        selected_feature_ids = source_layer.selectedFeatureIds()
        if not selected_feature_ids:
            QMessageBox.information(iface.mainWindow(), "Nichts zu tun", "Es wurden keine Biotope selektiert.")
            return
    else:
        QMessageBox.critical(iface.mainWindow(), "Fehler", "Der Biotoplayer wurde nicht gefunden.")
        return

    try:
        bt.transfer_from_biotop_to_edit()
        iface.setActiveLayer(lm.edit_layer)
        lm.edit_layer.startEditing()
        iface.mapCanvas().refreshAllLayers()
    except UnabelToLock as e:
        QMessageBox.critical(iface.mainWindow(), "Fehler", str(e))
    except Exception as e:
        showExceptionError(e=e)


def transfer_from_edit_to_biotop(iface: QgisInterface):
    """Transfer all biotope from the edit layer to the biotope layer
    """
    bt = BiotopTransactions()
    lm = LayerManager()
    locking = BiotopeLocking()
    pguser = PostgresUser()

    try:
        result = bt.transfer_from_edit_to_biotop(dry_run=True)
        if not result["insert"] and not result["update"] and not result["ignored"]:
            QMessageBox.information(iface.mainWindow(), "Nichts zu tun",
                                    "Es gibt keine modifizierten oder neue Biotope.")
            if locking.unlock_user(user_id=pguser.user_id) is not True:
                raise UnabelToUnLock("Biotope können nicht entsperrt werden.")
            iface.mapCanvas().refreshAllLayers()
            return

        msgBox = QMessageBox()
        msgBox.setWindowTitle("Biotope zurückführen")

        count_new = 0
        count_modified = 0
        count_ignored = 0

        detailedText = ""
        detailedText += "Folgende Biotope werden neu eingefügt:\n  "
        for id in result["insert"]:
            detailedText += f"{id}, "
            count_new += 1

        detailedText += "\n\nFolgende Biotope werden modifiziert:\n  "
        for id in result["update"]:
            detailedText += f"{id}, "
            count_modified += 1

        detailedText += "\n\nFolgende Biotope wurden nicht verändert und werden nicht zurückgeführt:\n"
        for id in result["ignored"]:
            detailedText += f"{id}, "
            count_ignored += 1

        infoText = ""
        if count_new == 1:
            infoText += f"Soll <b>ein neues Biotop</b> in den Datenbestand übernommen werden?<br><br>"
        if count_new > 1:
            infoText += f"Sollen <b>{count_new} neue Biotope</b> in den Datenbestand übernommen werden?<br><br>"

        if count_modified == 1:
            infoText += f"Soll <b>ein modifziertes Biotop</b> im Datenbestand geändert werden?<br><br>"
        if count_modified > 1:
            infoText += f"Sollen <b>{count_modified} modifzierte Biotope</b> im Datenbestand geändert werden?<br><br>"

        if count_ignored == 1:
            infoText += f"<b>Ein Biotope</b> wurde nicht verändert und wird nicht zurückgeführt."
        if count_ignored > 1:
            infoText += f"<b>{count_ignored} Biotope</b> wurden nicht verändert und werden nicht zurückgeführt."

        msgBox.setText(infoText)
        msgBox.setDetailedText(detailedText)
        msgBox.setStandardButtons(QMessageBox.Ok | QMessageBox.Cancel)
        msgBox.setDefaultButton(QMessageBox.Cancel)
        choice = msgBox.exec_()

        if choice == QMessageBox.Cancel:
            return

        result = bt.transfer_from_edit_to_biotop(dry_run=False)
        iface.setActiveLayer(lm.biotope_layer)
        iface.mapCanvas().refreshAllLayers()
        QMessageBox.information(iface.mainWindow(), "Information", "Vorgang erfolgreich abgeschlossen")
    except UnabelToUnLock as e:
        QMessageBox.critical(iface.mainWindow(), "Fehler", str(e))
    except Exception as e:
        showExceptionError(e=e)


def cancel_edit(iface: QgisInterface):
    """Transfer all biotope from the edit layer to the biotope layer
    """
    bt = BiotopTransactions()
    lm = LayerManager()
    locking = BiotopeLocking()
    pguser = PostgresUser()

    try:
        result = bt.cancel_edit(dry_run=True)
        if not result["insert"] and not result["update"] and not result["ignored"]:
            QMessageBox.information(iface.mainWindow(), "Nichts zu tun", "Es gibt keine modifizierten "
                                                                         "oder neue Biotope.")
            if locking.unlock_user(user_id=pguser.user_id) is not True:
                raise UnabelToUnLock("Biotope können nicht entsperrt werden.")
            iface.mapCanvas().refreshAllLayers()
            return

        msgBox = QMessageBox()
        msgBox.setWindowTitle("Editieren abbrechen")

        count_new = 0
        count_modified = 0
        count_ignored = 0

        detailedText = ""
        detailedText += "Folgende Biotope wurden neu eingefügt, werden aber aus dem Editierlayer gelöscht:\n\n"
        for id in result["insert"]:
            detailedText += f"{id}, "
            count_new += 1

        detailedText += "\n\nFolgende Biotope wurden modifiziert, werden aber aus dem Editierlayer gelöscht:\n\n"
        for id in result["update"]:
            detailedText += f"{id}, "
            count_modified += 1

        detailedText += "\n\nFolgende Biotope wurden nicht verändert und werden aus dem Editierlayer gelöscht:\n\n"
        for id in result["ignored"]:
            detailedText += f"{id}, "
            count_ignored += 1

        infoText = ""
        if count_new == 1:
            infoText += f"Soll <b>ein neues Biotop</b> aus dem Editierlayer gelöscht werden?<br><br>"
        if count_new > 1:
            infoText += f"Sollen <b>{count_new} neue Biotope</b> aus dem Editierlayer gelöscht werden?<br><br>"

        if count_modified == 1:
            infoText += f"Soll <b>ein modifziertes Biotop</b> aus dem Editierlayer gelöscht werden?<br><br>"
        if count_modified > 1:
            infoText += f"Sollen <b>{count_modified} modifzierte Biotope</b> aus dem Editierlayer " \
                f"gelöscht werden?<br><br>"

        if count_ignored == 1:
            infoText += f"<b>Ein Biotope</b> wurde nicht verändert und wird aus dem Editierlayer gelöscht."
        if count_ignored > 1:
            infoText += f"<b>{count_ignored} Biotope</b> wurden nicht verändert und werden aus dem Editierlayer gelöscht."

        msgBox.setText(infoText)
        msgBox.setDetailedText(detailedText)
        msgBox.setStandardButtons(QMessageBox.Ok | QMessageBox.Cancel)
        msgBox.setDefaultButton(QMessageBox.Cancel)
        choice = msgBox.exec_()

        if choice == QMessageBox.Cancel:
            return

        result = bt.cancel_edit(dry_run=False)
        iface.setActiveLayer(lm.biotope_layer)
        iface.mapCanvas().refreshAllLayers()
        QMessageBox.information(iface.mainWindow(), "Information", "Vorgang erfolgreich abgeschlossen")
    except UnabelToUnLock as e:
        QMessageBox.critical(iface.mainWindow(), "Fehler", str(e))
    except Exception as e:
        showExceptionError(e=e)


def delete_biotope(iface: QgisInterface):
    """Delete all selected biotope from the biotope layer
    """
    bt = BiotopTransactions()
    lm = LayerManager()
    conf = Configuration()

    source_layer = lm.biotope_layer
    selected_feature_ids = source_layer.selectedFeatureIds()

    if not selected_feature_ids:
        QMessageBox.information(iface.mainWindow(), "Nichts zu tun", "Es wurden keine Biotope "
                                                                     "zu Archivierung selektiert.")
        return

    delete_dlg = DeleteDialog()
    delete_dlg.exec_()

    if delete_dlg.is_accepted is False:
        return

    msgBox = QMessageBox()
    msgBox.setWindowTitle("Biotope archivieren")

    content = ""
    content += "<h3>Sollen folgende Biotope archiviert werden?</h3>"

    if selected_feature_ids:
        for _id in selected_feature_ids:
            feature = source_layer.getFeature(_id)
            identifier = feature[conf.biotope_identifier]
            content += f"<b>{identifier}</b><br>"

    msgBox.setText(content)
    msgBox.setStandardButtons(QMessageBox.Ok | QMessageBox.Cancel)
    msgBox.setDefaultButton(QMessageBox.Cancel)
    choice = msgBox.exec_()
    if choice == QMessageBox.Cancel:
        return

    try:
        bt.delete_selected_biotope(delete_who=delete_dlg.loeschung_wer.currentText(),
                                   delete_datum=delete_dlg.loeschung_wann.dateTime().toString(Qt.Qt.ISODate),
                                   delete_message=delete_dlg.loeschung_bemerkung.toPlainText())
        iface.setActiveLayer(lm.biotope_layer)
        iface.mapCanvas().refreshAllLayers()
        QMessageBox.information(iface.mainWindow(), "Information", "Alle selektierten Biotope wurden archiviert.")
    except UnabelToUnLock as e:
        QMessageBox.critical(iface.mainWindow(), "Fehler", str(e))
    except Exception as e:
        showExceptionError(e=e)
