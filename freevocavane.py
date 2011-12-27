#!/usr/bin/env python
# coding: utf-8

import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
print sys.path

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

'''
site_liststore = []
for module in Hosts.AVALIABLE_APIS:
    display_name = module.display_name

    site_liststore.append([display_name, module])

# Set last site active
api_names = [x.display_name for x in Hosts.AVALIABLE_APIS]
print api_names
api = site_liststore[1][1]
print api
search = api.Show.search()
#self.name_list_model.append([show.name, show])
shows = []
for i in search:
	if i.name == 'Grey\'s Anatomy':
		show = i
		print i
		break
	shows.append(i)

print show

seasons = []
for s in show.seasons:
	seasons.append(s)
season = seasons[1]
print season

episodes = []
for s in season.episodes:
	print s
	episodes.append(s)
episode = episodes[0]
print episode

print episode.get_subtitle_url()
if len(episode.file_hosts) > 1:
	for host in episode.file_hosts:
		print host
else:
	print episode.file_hosts.itervalues().next().itervalues().next()
#Player(GuiManagerEmulator(), episode, './', download_only=True)
'''
