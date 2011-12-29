# -*- coding: iso-8859-1 -*-
from item import Item
from guicavane import Hosts
from guicavane.Player import Player
from guicavane.Utils.UrlOpen import UrlOpen
from guicavane.Hosts.Base import BaseMovie, BaseEpisode
from guimanageremulator import GuiManagerEmulator
from gui.PopupBox import PopupBox

from video import VideoItem
import config
import time
import menu
import os
import string
from guicavane import Downloaders

class FCMenu(Item):

    def __init__(self):
        Item.__init__(self)
        self.type = 'tv'
        self.gui_manager = GuiManagerEmulator()


    def main_menu(self, arg, menuw):
        items = []
        for module in Hosts.AVALIABLE_APIS:
            display_name = module.display_name

            items.append(menu.MenuItem(display_name, action=self.selected_source, arg=module))

        menuw.pushmenu(menu.Menu('Stream', items, item_types='stream'))

    def selected_source(self, arg, menuw):
        api = arg
        items = []
        search = api.Show.search()
        for show in search:
            items.append(menu.MenuItem(show.name, action=self.selected_show, arg=(api, show)))
            
        menuw.pushmenu(menu.Menu('stream', items, item_types='stream'))

    def selected_show(self, arg, menuw):
        api, show = arg
        items = []
        for season in show.seasons:
            items.append(menu.MenuItem(show.name + ' Season ' + str(season.number), action=self.selected_season, arg=(api, show, season)))
        menuw.pushmenu(menu.Menu('stream', items, item_types='stream'))

    def selected_season(self, arg, menuw):
        api, show, season = arg
        items = []
        for episode in season.episodes:
            items.append(menu.MenuItem(show.name + ' Season ' + str(season.number) + ' Episode ' + str(episode.number) + ' ' + str(episode.name), action=self.selected_episode, arg=(api, show, season, episode)))
        menuw.pushmenu(menu.Menu('stream', items, item_types='stream'))

    def selected_episode(self, arg, menuw):
        api, show, season, episode = arg
        items = []
        for host in episode.file_hosts.iterkeys():
            items.append(menu.MenuItem(host, action=self.selected_host, arg=(api, show, season, episode, host)))
        menuw.pushmenu(menu.Menu('stream', items, item_types='stream'))

    def selected_host(self, arg, menuw):
        api, show, season, episode, host = arg
        items = []
        for quality in episode.file_hosts[host].iterkeys():
            items.append(menu.MenuItem(quality, action=self.selected_quality, arg=(api, show, season, episode, host, quality)))
        menuw.pushmenu(menu.Menu('stream', items, item_types='stream'))

    def selected_quality(self, arg, menuw):
        api, show, season, episode, host, quality = arg

        self.video_item = None
        self.menuw = menuw
        self.file_object = episode
        self.selected_host = host
        self.selected_quality = quality
        config.VIDEO_SHOW_DATA_DIR = '/media/disk/video'
        self.file_path = os.path.join(config.VIDEO_SHOW_DATA_DIR, self.get_filename(episode))
        box = PopupBox(text='Starting download... will start playing shortly')
        box.show()
        time.sleep(2)
        box.destroy()

        if os.path.exists(self.file_path):
            # TODO: check file completition?
            self.play()
            return

        url_open = UrlOpen()
        url = self.file_object.get_subtitle_url(quality=self.selected_quality)
        filename = self.file_path.replace(".mp4", ".srt")
        url_open(url, filename=filename)

        print episode.file_hosts[host][quality]
        self.gui_manager.background_task(self.pre_download, self.play)
        self.downloader = Downloaders.get(host, self.gui_manager, episode.file_hosts[host][quality])
        self.downloader.process_url(None, self.file_path)

    def pre_download(self):
        """ Downloads some content to start safely the player. """
        while not os.path.exists(self.file_path):
            time.sleep(1)

        if self.downloader.file_size != 0:
            # Waits %1 of the total download
            percent = self.downloader.file_size * 0.01

            while self.downloader.downloaded_size < percent:
                time.sleep(1)
        else:
            # Waits 2MB, just an arbitrary amount
            while self.downloader.downloaded_size < 2 * 1024 * 1024:
                time.sleep(0.5)

    def play(self):
        if self.video_item:
            return
        self.video_item = VideoItem('file://' + self.file_path, None)
        self.video_item.play(menuw=self.menuw)

    def get_filename(self, file_object):
        """ Returns the file path of the file. """

        valid_chars = "-_.() %s%s" % (string.ascii_letters, string.digits)

        result = "<show> <season>x<episode> <name>.mp4"
        result = result.replace("<show>", file_object.show.name)
        result = result.replace("<season>", "%.2d" % \
            int(file_object.season.number))
        result = result.replace("<episode>", "%s" % \
            str(file_object.number))
        result = result.replace("<name>", file_object.name)
        return result
