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


class Singleton(type):
    """Singleton class copied from a stackoverflow post:
    https://stackoverflow.com/questions/6760685/creating-a-singleton-in-python

    This singleton must be used as metaclass:

    class MyClass(BaseClass, metaclass=Singleton):
        pass

    """
    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)
        return cls._instances[cls]


if __name__ == "__main__":
    import doctest

    doctest.testmod()
