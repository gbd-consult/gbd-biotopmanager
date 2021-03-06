# -*- coding: utf-8 -*-
"""
/***************************************************************************
 BiotopManagerDialog
                                 A QGIS plugin
 Dieses Plugin verwaltet Biotope
 Generated by Plugin Builder: http://g-sherman.github.io/Qgis-Plugin-Builder/
                             -------------------
        begin                : 2018-06-27
        git sha              : $Format:%H$
        copyright            : (C) 2018 by Geoinformatikbüro Dassau GmbH
        email                : info@gbd-consult.de
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

import os
from PyQt5 import uic
from PyQt5 import QtWidgets
from qgis.core import QgsProject

FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'assets', 'ui', 'delete_dialog.ui'))


class DeleteDialog(QtWidgets.QDialog, FORM_CLASS):
    """Get the information that must be stored for each deleted object
    """
    def __init__(self, parent=None):
        super(DeleteDialog, self).__init__(parent)
        self.setupUi(self)
        self.is_accepted = False
        self.valueRelation()

        self.pushButtonCancel.clicked.connect(self.close)
        self.pushButtonOk.clicked.connect(self.ok)

    def ok(self):
        """Check the content of the edit widgets
        """

        if not self.loeschung_wer.currentText():
            QtWidgets.QMessageBox.critical(self, "Fehler", "Der Bearbeiter der Archivierung muss angegeben werden.")
            return

        if not self.loeschung_bemerkung.toPlainText():
            QtWidgets.QMessageBox.critical(self, "Fehler", "Ein Begründung für die Archivierung muss angegeben werden.")
            return

        self.is_accepted = True
        self.close()

    def valueRelation(self):
        """Fill the ValueRelation for - loeschung_wer - 
        """
        kl = QgsProject.instance().mapLayersByName('kartierer')[0]

        for i in kl.getFeatures():
            feat = i['kartierer']
            self.loeschung_wer.addItem(feat)
