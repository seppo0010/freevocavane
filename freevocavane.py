#!/usr/bin/env python
# coding: utf-8

import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from fcmenu import FCMenu
import plugin

#
# Plugin interface to integrate the tv module into Freevo
#
class PluginInterface(plugin.MainMenuPlugin):
    """
    TV main menu option
    """

    def items(self, parent):
        import menu
        return [ menu.MenuItem('', action=FCMenu().main_menu,
            arg=('stream', 0), type='main', parent=parent, skin_type='stream') ]
