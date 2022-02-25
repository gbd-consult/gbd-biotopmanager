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
from PyQt5.QtWidgets import QMessageBox
from qgis.core import QgsVectorLayer, QgsVectorDataProvider, QgsVectorLayerUtils, QgsGeometry, QgsFeature
from biotopmanager.common.singleton import Singleton
from biotopmanager.common.configuration import Configuration
from biotopmanager.common.locking import BiotopeLocking
from biotopmanager.common.database_connection import DatabaseConnection
from biotopmanager.common.user_credentials import PostgresUser
from biotopmanager.common.layer_manager import LayerManager
from biotopmanager.common.exception_handling import UnabelToLock, UnableToLoadLayers, UnabelToUnLock
from biotopmanager.common.utils.logging import qgis_log
from biotopmanager.common.biotope_model import BiotopeModel


class BiotopTransactions(metaclass=Singleton):
    """This class implements transaction between the original biotop layer and
    newly generated memory layers."""

    def __init__(self):
        self._conn = DatabaseConnection()
        self._conf = Configuration()
        self._locking = BiotopeLocking()
        self._pguser = PostgresUser()
        self._layer_manager = LayerManager()
        self._bm = BiotopeModel()

        self._update_list = []
        self._delete_list = []

    def transfer_from_biotop_to_edit(self) -> None:
        """Lock and copy selected features from the biotop postgis layer into the edit layer.

        1. Lock the selected features of the biotop postgis layer in the lock table
        2. Deep copy the selected features into the edit layer
        """

        qgis_log(message="transfer_from_biotop_to_edit")
        source_layer = self._layer_manager.biotope_layer
        target_layer = self._layer_manager.edit_layer

        selected_feature_ids = source_layer.selectedFeatureIds()

        if not selected_feature_ids:
            return

        if self._locking.lock(selected_feature_ids, user_id=self._pguser.user_id) is False:
            raise UnabelToLock("Biotope können nicht gesperrt werden.")
        self.copy_selected_features(source_layer=source_layer, target_layer=target_layer)

    def transfer_from_edit_to_biotop(self, dry_run: bool = True) -> dict:
        """Merge all features from the memory layer (source layer) into the biotop postgis layer (target layer).

        Args:
            dry_run: Perform a dry run and do not merge features, but return all feature that will be merged

        Merge strategy: See merge_source_to_target_layer()

        1. Merge all features into the target layer
        2. Unlock all features from the lock table
        3. Clean the source layer from all features

        Returns:
            dict
            A dictionary with list of ignored, updated and inserted feature identifiers

        """
        qgis_log(message="transfer_from_edit_to_biotop")
        source_layer = self._layer_manager.edit_layer
        target_layer = self._layer_manager.biotope_layer

        try:
            # Merge the data from the memory layer into the postgis layer
            result = self.merge_source_to_target_layer(source_layer=source_layer, target_layer=target_layer, dry_run=dry_run)
            if dry_run is True:
                return result
            # Delete all features from the memory layer
            data_provider = source_layer.dataProvider()
            data_provider.truncate()
            source_layer.updateExtents()
            return result
        except:
            raise
        finally:
            # unlock all objects, that were locked
            if dry_run is False:
                qgis_log(f"Unlock all objects for user {self._pguser.user_id}")
                if self._locking.unlock_user(user_id=self._pguser.user_id) is not True:
                    raise UnabelToUnLock("Biotope können nicht entsperrt werden.")

    def cancel_edit(self, dry_run: bool = True) -> dict:
        """Cancel the editing: remove all features from the edit layer and unlock them

        Args:
            dry_run: Perform a dry run; just check which objects will be removed from the edit layer

        Merge strategy: See merge_source_to_target_layer()

        1. Check which features will be merged into the target layer to list them to the user
           and return them in a dry run
        2. Clean the edit layer from all features
        3. Unlock all features from the lock table

        Returns:
            dict
            A dictionary with list of potentially ignored, updated and inserted feature identifiers

        """
        qgis_log(message="cancel_edit")
        source_layer = self._layer_manager.edit_layer
        target_layer = self._layer_manager.biotope_layer

        try:
            if dry_run is True:
                # Merge the data from the memory layer into the postgis layer to show the user
                # the consequence of the canceling
                result = self.merge_source_to_target_layer(source_layer=source_layer,
                                                           target_layer=target_layer, dry_run=True)
                return result
            # Delete all features from the memory layer
            data_provider = source_layer.dataProvider()
            data_provider.truncate()
            source_layer.updateExtents()
            if self._locking.unlock_user(user_id=self._pguser.user_id) is not True:
                raise UnabelToUnLock("Biotope können nicht entsperrt werden.")
        except:
            raise
        finally:
            # unlock all objects, that were locked by the user
            if dry_run is False:
                qgis_log(f"Unlock all objects for user {self._pguser.user_id}")
                if self._locking.unlock_user(user_id=self._pguser.user_id) is not True:
                    raise UnabelToUnLock("Biotope können nicht entsperrt werden.")

    def delete_selected_biotope(self, delete_who, delete_datum, delete_message) -> None:
        """Delete the selected features from the biotop layer and unlock them in the lock table
        """
        qgis_log(message="delete_selected_biotope")
        # Get the selected features
        source_layer = self._layer_manager.biotope_layer

        selected_feature_ids = source_layer.selectedFeatureIds()
        if selected_feature_ids:

            lock_sql = self._locking.lock_sql(selected_feature_ids, user_id=self._pguser.user_id)
            delete_sql = ""
            update_history = ""
            unlock_sql = self._locking.unlock_sql(selected_feature_ids, user_id=self._pguser.user_id)
            for id_ in selected_feature_ids:
                if self._locking.is_locked(biotop_id=id_, user_id=self._pguser.user_id) is True:
                    raise UnabelToLock("Fehler beim Löschen von Biotopen. Biotope können nicht gesperrt werden.")

                delete_sql += f"DELETE FROM {self._conf.biotope_schema}.{self._conf.biotope_table_name} " \
                              f"WHERE {self._conf.biotope_primary_key} = {id_};\n"
                statement = f"UPDATE {self._conf.history_schema}.{self._conf.historie_table_name} " \
                            f"SET loeschung_wer = %s, loeschung_wann = %s, loeschung_bemerkung = %s " \
                            f"WHERE {self._conf.biotope_primary_key} = {id_} AND action = 'D';\n"
                statement = self._conn.mogrify(statement=statement,
                                               args=[delete_who, delete_datum, delete_message])
                update_history += statement.decode("utf-8")

            # Create the transaction
            transaction = lock_sql + delete_sql + update_history + unlock_sql
            qgis_log(transaction)
            try:
                self._conn.execute_transaction(transaction)
                self._conn.commit()
            except Exception as e:
                raise UnabelToLock("Fehler beim Löschen von Biotopen: str(e)")

    def delete_selected_biotope_legacy(self) -> None:
        """Delete the selected features from the biotop layer and unlock them in the lock table
        """
        qgis_log(message="delete_selected_biotope")
        # Get the selected features
        source_layer = self._layer_manager.biotope_layer
        avoid_unlocking = False

        try:
            selected_feature_ids = source_layer.selectedFeatureIds()
            if selected_feature_ids:
                if self._locking.lock(selected_feature_ids, user_id=self._pguser.user_id) is False:
                    avoid_unlocking = True
                    raise UnabelToLock("Biotope können nicht gesperrt werden.")

                # Delete all selected features from the biotop layer
                data_provider = self._layer_manager.biotope_layer.dataProvider()
                data_provider.deleteFeatures(selected_feature_ids)
        except:
            raise
        finally:
            # unlock all objects, that were locked
            if avoid_unlocking is False:
                if self._locking.unlock_user(user_id=self._pguser.user_id) is not True:
                    raise UnabelToUnLock("Biotope können nicht entsperrt werden.")

    def copy_selected_features(self, source_layer: QgsVectorLayer, target_layer: QgsVectorLayer) -> None:
        """Copy all selected features from the original layer into the edit layer.

        Args:
            source_layer: The layer to copy selected features into the edit table
            target_layer: The edit layer
        """
        selected_ids = source_layer.selectedFeatureIds()
        statement_list = []
        column_names = self._bm.get_biotope_column_names()
        column_names = ",".join(column_names)

        for _id in selected_ids:
            insert = f"INSERT INTO {self._bm.edit_table} " \
                     f"SELECT {column_names} FROM {self._bm.biotope_table} " \
                     f"WHERE {self._bm.biotope_table}.{self._conf.biotope_primary_key} = {_id};"
            statement_list.append(insert)
        try:
            statement = "\n".join(statement_list)
            # qgis_log(statement)
            self._conn.execute_transaction(statement)
            target_layer.updateExtents()
        except Exception as e:
            self._conn.rollback()
            qgis_log(str(e))

    @staticmethod
    def copy_selected_features_qgis(source_layer: QgsVectorLayer, target_layer: QgsVectorLayer) -> None:
        """Copy all selected features from the source layer into the target layer.

        Args:
            source_layer: The layer to copy features from
            target_layer: The layer to copy features into
        """
        selected_features = source_layer.selectedFeatures()
        data_provider = target_layer.dataProvider()
        data_provider.addFeatures(selected_features)
        target_layer.updateExtents()

    def _compare_attributes(self, source_attrs: list, target_attrs: list) -> bool:
        """Compare two list and return True if they are equal

        Args:
            source_attrs: source attributes
            target_attrs: target attributes

        Returns:
            True if equal, False if different
        """
        if not source_attrs == target_attrs:
            return False
        return True

    def _compare_geometries(self, source_geo: QgsGeometry, target_geo: QgsGeometry) -> bool:
        """Compare two geometries and return True if they are almost equal and False
        if they differ slightly.

        Several simple checks are performed

        1. Area check, if differ return False
        2. Length check, if differ return False
        3. Number of vertices check, if differ return False
        4. Vertices check, if differ return False
        5. Return True

        Args:
            source_geo: source geometry
            target_geo: target geometry

        Returns:
            True if the geometries are almost equal, False if they are slightly different
        """

        EPSILON = 0.0001

        # Check area
        diff = abs(source_geo.area() - target_geo.area())
        if diff > EPSILON:
            # qgis_log("Area differ")
            return False

        # Check length
        diff = abs(source_geo.length() - target_geo.length())
        if diff > EPSILON:
            # qgis_log("Length differ")
            return False

        if len([x for x in source_geo.vertices()]) != len([x for x in target_geo.vertices()]):
            # qgis_log("Number vertices differ")
            return False

        for p1, p2, in zip(source_geo.vertices(), target_geo.vertices()):
            if abs(p1.x() - p2.x()) > EPSILON:
                # qgis_log("X coordinates differ")
                return False
            if abs(p1.y() - p2.y()) > EPSILON:
                # qgis_log("Y coordinates differ")
                return False
        return True

    def merge_source_to_target_layer(self, source_layer: QgsVectorLayer, target_layer: QgsVectorLayer,
                                     dry_run: bool = False) -> dict:
        """Merge all selected features from the source layer into the target layer.

        Merge strategy:

        - If the id of the source layer feature exists in the target layer, then the target layer feature
          will be updated if the features differ
        - If the id of the source layer feature does not exist in the target layer, then deep copy new feature
          into the target layer

        Args:
            source_layer: The layer to merge features from
            target_layer: The layer to merge features into
            dry_run: Set True to not perform any feature transfer, but count the insert, updates and ignores

        Returns:
            dict
            A dictionary with list of ignored, updated and inserted feature identifiers
        """

        modified_features = dict(update=list(), insert=list(), ignored=list())
        modified_geos = dict()
        modified_attr = dict()
        new_features = list()

        source_layer.commitChanges()

        feature_ids = source_layer.allFeatureIds()

        if not feature_ids:
            return modified_features

        # Check the primary key beforehand to avoid ugly errors
        # Primary key corruption can occur when the field calculator of the attribute table is misused
        for _id in feature_ids:
            # Get the actual feature
            feature = source_layer.getFeature(_id)
            pk = feature[self._conf.biotope_primary_key]

            try:
                pk = int(pk)
            except TypeError:
                QMessageBox.critical(None, "Fehler", f"Falscher Primäerschlüssel in der Datenbank. fid: {_id}, "
                                     f"Primärschlüssel {pk}")
                return modified_features

        for _id in feature_ids:
            # Get the actual feature
            feature = source_layer.getFeature(_id)
            pk = feature[self._conf.biotope_primary_key]
            # Check if the feature exists in the target layer
            target_feature = target_layer.getFeature(pk)
            # Check if a correct feature was returned
            if target_feature.isValid():

                check = self._bm.orig_edit_feature_equal(target_feature[self._conf.biotope_primary_key])

                if check is True:
                    modified_features["ignored"].append(feature[self._conf.biotope_identifier])
                    continue

                # Check if the features are different
                target_attrs = target_feature.attributes()
                source_attrs = feature.attributes()
                target_geo = target_feature.geometry()
                source_geo = feature.geometry()

                attrs_differ = self._compare_attributes(source_attrs=source_attrs, target_attrs=target_attrs)
                geo_differ = self._compare_geometries(source_geo=source_geo, target_geo=target_geo)
                qgis_log(f"Attr check: {attrs_differ} Geo Check: {geo_differ}")

                # Check if the features were not changed
                modified_features["update"].append(feature[self._conf.biotope_identifier])

                # Modified geometry
                if geo_differ is False:
                    modified_geos[target_feature.id()] = QgsGeometry(source_geo)

                # Modified attributes
                if attrs_differ is False:
                    # Create the attribute map
                    attr_map = dict()
                    for i in range(len(source_attrs)):
                        attr_map[i] = source_attrs[i]
                    modified_attr[target_feature.id()] = attr_map
            else:
                new_feature = QgsFeature(source_layer.fields())
                new_feature.setGeometry(QgsGeometry(feature.geometry()))
                new_feature.setAttributes(feature.attributes())
                new_features.append(new_feature)
                modified_features["insert"].append(new_feature[self._conf.biotope_identifier])

        if dry_run is False:
            try:
                target_layer.setReadOnly(False)
                target_data_provider = target_layer.dataProvider()
                # print(modified_attr, modified_geos, new_features)
                if modified_geos and modified_attr:
                    success = target_data_provider.changeFeatures(modified_attr, modified_geos)
                    qgis_log(f"Modified attributes and geometries {success}")
                elif modified_geos:
                    success = target_data_provider.changeGeometryValues(modified_geos)
                    qgis_log(f"Modified geometries {success}")
                elif modified_attr:
                    success = target_data_provider.changeAttributeValues(modified_attr)
                    qgis_log(f"Modified attributes {success}")
                if new_features:
                    success = target_data_provider.addFeatures(new_features)
                    qgis_log(f"New features {success}")
            except:
                raise
            finally:
                target_layer.setReadOnly(True)

        return modified_features


if __name__ == "__main__":
    """Small test
    """
    from qgis.core import QgsFeature, QgsGeometry, QgsPointXY
    from qgis.core import QgsApplication
    app = QgsApplication([], False)
    app.initQgis()

    conn = DatabaseConnection()
    conn.setup_default_connection()
    t = BiotopTransactions()

    source_layer = QgsVectorLayer("Point?field=ogc_fid:integer&field=area:integer&field=identity:string",
                                  "source layer", "memory")
    # Add the attributes of the biotop layer
    provider = source_layer.dataProvider()
    attrs = source_layer.fields()
    print(source_layer.isValid())

    source_layer.startEditing()
    for i in range(1, 11):
        g = QgsGeometry.fromPointXY(QgsPointXY(i,i))
        f = QgsFeature(attrs)
        f["ogc_fid"] = i
        f["identity"] = "obj %i"%i
        f["area"] = i + 100
        f.setGeometry(g)
        f.setId(i)
        source_layer.addFeature(f)
    source_layer.commitChanges()
    print("All feature ids:", source_layer.allFeatureIds())

    bt = BiotopTransactions()

    target_layer = QgsVectorLayer("Point?field=ogc_fid:integer&field=area:integer&field=identity:string",
                                  "target layer", "memory")

    source_layer.selectAll()
    bt.copy_selected_features_qgis(source_layer, target_layer)
    print(source_layer.featureCount())

    # Modify geometries from the source
    source_layer.startEditing()
    for i in range(1, 4):
        g = QgsGeometry.fromPointXY(QgsPointXY(i + 1,i + 1))
        source_layer.changeGeometry(i, g)
    source_layer.commitChanges()

    # Modify attributes from the source
    source_layer.startEditing()
    for i in range(3, 7):
        source_layer.changeAttributeValue(i, 1, i + 200)
    source_layer.commitChanges()

    # Add more features to source
    source_layer.startEditing()
    for i in range(1, 4):
        g = QgsGeometry.fromPointXY(QgsPointXY(i,i))
        f = QgsFeature(attrs)
        f["ogc_fid"] = i + 10
        f["identity"] = "obj %i"%(i + 10)
        f["area"] = i + 100
        f.setGeometry(g)
        f.setId(i)
        source_layer.addFeature(f)
    source_layer.commitChanges()
    print("All feature ids:", sorted(source_layer.allFeatureIds()))

    result = bt.merge_source_to_target_layer(source_layer, target_layer)
    print(result)

    if len(result["update"]) != 6:
        print("Error update")
    if len(result["insert"]) != 3:
        print("Error insert")
    if len(result["ignored"]) != 4:
        print("Error ignored")
