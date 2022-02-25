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
import os.path
import webbrowser
from qgis.core import QgsSettings
from PyQt5.QtCore import QSettings, QTranslator, qVersion, QCoreApplication
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QAction

# Initialize Qt resources from file resources.py
from .resources import *
# Import the code for the dialog
from biotopmanager.login_dialog import LoginDialog
from biotopmanager.biotop_manager_history_dialog import BiotopManagerHistoryDialog
from biotopmanager.common.ui_processes import transfer_from_biotop_to_edit, \
    transfer_from_edit_to_biotop, delete_biotope, cancel_edit, start_biotop_editing


class BiotopManager:
    """QGIS Plugin Implementation."""

    def __init__(self, iface):
        """Constructor.

        :param iface: An interface instance that will be passed to this class
            which provides the hook by which you can manipulate the QGIS
            application at run time.
        :type iface: QgsInterface
        """
        # Enable Macros for this Session
        s = QgsSettings()
        s.setValue('qgis/enableMacros','SessionOnly')

        # Save reference to the QGIS interface
        self.iface = iface
        # initialize plugin directory
        self.plugin_dir = os.path.dirname(__file__)
        # initialize locale
        locale = QSettings().value('locale/userLocale')[0:2]
        locale_path = os.path.join(
            self.plugin_dir,
            'i18n',
            'BiotopManager_{}.qm'.format(locale))

        if os.path.exists(locale_path):
            self.translator = QTranslator()
            self.translator.load(locale_path)

            if qVersion() > '4.3.3':
                QCoreApplication.installTranslator(self.translator)

        # Declare instance attributes
        self.actions = []
        self.menu = self.tr(u'&GBD Biotopmanager')
        # TODO: We are going to let the user set this up in a future iteration
        self.toolbar = self.iface.addToolBar(u'GBD Biotopmanager')
        self.toolbar.setObjectName(u'GBD Biotopmanager')

        self.login_dialog = None
        self.history_dialog = None

    # noinspection PyMethodMayBeStatic
    def tr(self, message):
        """Get the translation for a string using Qt translation API.

        We implement this ourselves since we do not inherit QObject.

        :param message: String for translation.
        :type message: str, QString

        :returns: Translated version of message.
        :rtype: QString
        """
        # noinspection PyTypeChecker,PyArgumentList,PyCallByClass
        return QCoreApplication.translate('BiotopManager', message)


    def add_action(
        self,
        icon_path,
        text,
        callback,
        enabled_flag=True,
        add_to_menu=True,
        add_to_toolbar=True,
        tool_tip=None,
        whats_this=None,
        parent=None):
        """Add a toolbar icon to the toolbar.

        :param icon_path: Path to the icon for this action. Can be a resource
            path (e.g. ':/plugins/foo/bar.png') or a normal file system path.
        :type icon_path: str

        :param text: Text that should be shown in menu items for this action.
        :type text: str

        :param callback: Function to be called when the action is triggered.
        :type callback: function

        :param enabled_flag: A flag indicating if the action should be enabled
            by default. Defaults to True.
        :type enabled_flag: bool

        :param add_to_menu: Flag indicating whether the action should also
            be added to the menu. Defaults to True.
        :type add_to_menu: bool

        :param add_to_toolbar: Flag indicating whether the action should also
            be added to the toolbar. Defaults to True.
        :type add_to_toolbar: bool

        :param tool_tip: Optional text to show in a popup when mouse pointer
            hovers over the action.
        :type tool_tip: str

        :param parent: Parent widget for the new action. Defaults None.
        :type parent: QWidget

        :param whats_this: Optional text to show in the status bar when the
            mouse pointer hovers over the action.

        :returns: The action that was created. Note that the action is also
            added to self.actions list.
        :rtype: QAction
        """

        icon = QIcon(icon_path)
        action = QAction(icon, text, parent)
        action.triggered.connect(callback)
        action.setEnabled(enabled_flag)

        if tool_tip is not None:
            action.setToolTip(tool_tip)

        if whats_this is not None:
            action.setWhatsThis(whats_this)

        if add_to_toolbar:
            self.toolbar.addAction(action)

        if add_to_menu:
            self.iface.addPluginToMenu(
                self.menu,
                action)

        self.actions.append(action)

        return action

    def initGui(self):
        """Create the menu entries and toolbar icons inside the QGIS GUI."""

        self.add_action(
            icon_path=":/plugins/biotop_manager/assets/icons/leaf-login-01.svg",
            text=self.tr(u'Login Biotopmanager Datenbank'),
            tool_tip=self.tr(u'Login Biotopmanager Datenbank'),
            whats_this=self.tr(u'Login Biotopmanager Datenbank'),
            callback=self.run_login_dialog,
            parent=self.iface.mainWindow())

        self.add_action(
            icon_path=":/plugins/biotop_manager/assets/icons/leaf-add-01.svg",
            text=self.tr(u'Neue Biotope erstellen'),
            tool_tip=self.tr(u'Neue Biotope erstellen'),
            whats_this=self.tr(u'Neue Biotope erstellen'),
            callback=self.start_editing,
            parent=self.iface.mainWindow())

        self.add_action(
            icon_path=":/plugins/biotop_manager/assets/icons/leaf-edit-01.svg",
            text=self.tr(u'Ausgewählte Biotope editieren und sperren'),
            tool_tip=self.tr(u'Ausgewählte Biotope editieren und sperren'),
            whats_this=self.tr(u'Ausgewählte Biotope editieren und sperren'),
            callback=self.transfer_from_biotop_to_edit,
            parent=self.iface.mainWindow())

        self.add_action(
            icon_path=":/plugins/biotop_manager/assets/icons/leaf-save-01.svg",
            text=self.tr(u'Editierte Biotope zurückführen und entsperren'),
            tool_tip=self.tr(u'Editierte Biotope zurückführen und entsperren'),
            whats_this=self.tr(u'Editierte Biotope zurückführen und entsperren'),
            callback=self.transfer_from_edit_to_biotop,
            parent=self.iface.mainWindow())

        self.add_action(
            icon_path=":/plugins/biotop_manager/assets/icons/leaf-cancel-01.svg",
            text=self.tr(u'Editieren abbrechen und Biotope Bearbeitungslayer leeren'),
            tool_tip=self.tr(u'Editieren abbrechen und Biotope Bearbeitungslayer leeren'),
            whats_this=self.tr(u'Editieren abbrechen und Biotope Bearbeitungslayer leeren'),
            callback=self.cancel_edit,
            parent=self.iface.mainWindow())

        self.add_action(
            icon_path=":/plugins/biotop_manager/assets/icons/leaf-archive-02.svg",
            text=self.tr(u'Ausgewählte Biotope archivieren'),
            tool_tip=self.tr(u'Ausgewählte Biotope archivieren'),
            whats_this=self.tr(u'Ausgewählte Biotope archivieren'),
            callback=self.delete_biotope,
            parent=self.iface.mainWindow())

        self.add_action(
            icon_path=":/plugins/biotop_manager/assets/icons/leaf-history-02.svg",
            text=self.tr(u'Historie ausgewählter Biotope anzeigen'),
            tool_tip=self.tr(u'Historie ausgewählter Biotope anzeigen'),
            whats_this=self.tr(u'Historie ausgewählter Biotope anzeigen'),
            callback=self.run_history_dialog,
            parent=self.iface.mainWindow())

        self.add_action(
            icon_path=":/plugins/biotop_manager/assets/icons/leaf-help-01.svg",
            text=self.tr(u'Handbuch Biotopmanager'),
            tool_tip=self.tr(u'Handbuch Biotopmanager'),
            whats_this=self.tr(u'Handbuch Biotopmanager'),
            callback=self.start_help_browser,
            parent=self.iface.mainWindow())

    def unload(self):
        """Removes the plugin menu item and icon from QGIS GUI."""
        for action in self.actions:
            self.iface.removePluginMenu(
                self.tr(u'&Biotopmanager'),
                action)
            self.iface.removeToolBarIcon(action)
        # remove the toolbar
        del self.toolbar

    def run_login_dialog(self):
        if self.login_dialog is None:
            self.login_dialog = LoginDialog(iface=self.iface)
        self.login_dialog.show()

    def run_history_dialog(self):
        if self.history_dialog is None:
            self.history_dialog = BiotopManagerHistoryDialog(iface=self.iface)
        self.history_dialog.show()

    def transfer_from_biotop_to_edit(self):
        transfer_from_biotop_to_edit(iface=self.iface)

    def transfer_from_edit_to_biotop(self):
        transfer_from_edit_to_biotop(iface=self.iface)

    def delete_biotope(self):
        delete_biotope(iface=self.iface)

    def cancel_edit(self):
        cancel_edit(iface=self.iface)

    def start_editing(self):
        start_biotop_editing(iface=self.iface)

    def start_help_browser(self):
        url = os.path.join(self.plugin_dir, "help", "index.html")
        webbrowser.open_new(url)
