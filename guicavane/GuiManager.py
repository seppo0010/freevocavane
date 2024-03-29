#!/usr/bin/env python
# coding: utf-8
# pylint: disable-msg=E1101,W0613

"""
GuiManager. Takes care of the gui events.
"""

import os
import sys
import gtk
import base64
import urllib
import webbrowser

import Hosts
from Paths import *
from Constants import *
from SList import SList
from Wizard import Wizard
from Config import Config
from Player import Player
from Gettext import gettext
from Utils.Log import console
from Accounts import ACCOUNTS
from Settings import SettingsDialog
from ThreadRunner import GtkThreadRunner
from Hosts.Base import BaseMovie, BaseEpisode

log = console("GuiManager")


class GuiManager(object):
    """ Main class, loads the gui and handles all events. """

    def __init__(self):
        """ Creates the main window. """

        # Attributes
        self.avaliable_modes = []

        self.current_show = None
        self.current_season = None

        is_first_time = not os.path.exists(CONFIG_FILE)
        self.config = Config.get()

        # API
        try:
            self.api = getattr(Hosts, self.config.get_key("site")).api
        except Exception, error:
            self.api = Hosts.AVALIABLE_APIS[0]

        self.marks = SList(MARKS_FILE)
        self.favorites = SList(FAVORITES_FILE)
        self.accounts = ACCOUNTS
        self.settings_dialog = SettingsDialog(self)

        # Gtk builder
        self.builder = gtk.Builder()
        self.builder.add_from_file(MAIN_GUI_FILE)
        self.builder.connect_signals(self)

        # Getting the used widgets
        glade_objects = [
            "main_window", "statusbar_label", "progress_box", "progress",
            "progress_label", "name_filter", "name_filter_clear", "name_list",
            "name_list_model", "file_viewer", "file_viewer_model",
            "mode_combo", "mode_liststore", "site_combo",
            "search_button", "search_clear", "search_entry", "search_hbox",
            "sidebar", "sidebar_vbox", "path_label", "info_window",
            "info_title", "info_label", "info_image", "file_viewer_menu",
            "error_label", "error_dialog", "header_hbox", "main_hpaned",
            "about_dialog", "site_liststore",
        ]

        for glade_object in glade_objects:
            setattr(self, glade_object, self.builder.get_object(glade_object))

        # Set up the filter for the show list
        self.name_list_model_filter = self.name_list_model.filter_new()
        self.name_list_model_filter.set_visible_func(generic_visible_func,
            (self.name_filter, NAME_LIST_COLUMN_TEXT))
        self.name_list.set_model(self.name_list_model_filter)

        # Get last mode, needs to be before the filling combo functions
        last_mode = self.config.get_key("last_mode")

        # Fill combobox
        self.fill_sites_combobox()
        self.fill_mode_combobox()

        # Start on last mode
        try:
            self.mode_combo.set_active(self.avaliable_modes.index(last_mode))
        except:
            self.set_mode_shows()

        # Login
        self.background_task(self.login_accounts, freeze=False)

        if is_first_time:
            wizard = Wizard(self.main_window)
            wizard.show()

        # Set last window position and size
        last_x, last_y = self.config.get_key("last_window_pos")
        last_width, last_height = self.config.get_key("last_window_size")
        self.main_window.move(last_x, last_y)
        self.main_window.resize(last_width, last_height)

        # Now we show the window
        self.main_window.show_all()

    def login_accounts(self):
        accounts = self.config.get_key("accounts")
        for account in accounts:
            account_name = account[0]
            username = account[1]["username"]
            password = base64.b64decode(account[1]["password"])

            try:
                account_obj = ACCOUNTS[account_name]
            except KeyError:
                log.warn("account not recognized: %s" % account_name)
                continue

            if username and password:
                account_obj.login(username, password)

    def freeze(self, status_message=gettext("Loading...")):
        """ Freezes the gui so the user can't interact with it. """

        self.header_hbox.set_sensitive(False)
        self.main_hpaned.set_sensitive(False)
        self.set_status_message(status_message)

    def unfreeze(self):
        """ Sets the widgets to be usable. """

        self.header_hbox.set_sensitive(True)
        self.main_hpaned.set_sensitive(True)
        self.set_status_message("")

    def background_task(self, func, callback=None, *args, **kwargs):
        """
        Freezes the gui, starts a thread with func.
        When it's done, unfreezes the gui and calls callback with the result.

        The results it's a tuple (is_error, result) with a boolean if
        an error has ocurred and the exception, or the result if there
        was no errors.
        """

        status_message = gettext("Loading...")
        freeze = True

        if "status_message" in kwargs:
            status_message = kwargs["status_message"]
            del kwargs["status_message"]

        if "freeze" in kwargs:
            freeze = kwargs["freeze"]
            del kwargs["freeze"]

        if freeze:
            self.freeze(status_message)
        else:
            kwargs["unfreeze"] = False

        if "unfreeze" in kwargs and not kwargs["unfreeze"]:
            real_callback = callback
            del kwargs["unfreeze"]
        else:
            def real_callback(result):
                self.unfreeze()
                callback(result)

        if callback == None:
            def real_callback((is_error, result)):
                pass

        GtkThreadRunner(real_callback, func, *args, **kwargs)

    def fill_sites_combobox(self):
        """ Fills the sites combobox with the avaliable apis. """

        for module in Hosts.AVALIABLE_APIS:
            display_name = module.display_name

            imagepath = os.path.join(SITES_IMAGES_DIR, module.display_image)
            pixbuf = None

            if os.path.exists(imagepath):
                image = gtk.Image()
                image.set_from_file(imagepath)
                pixbuf = image.get_pixbuf()

            self.site_liststore.append([display_name, module, pixbuf])

        # Set last site active
        last_site = self.api.display_name
        api_names = [x.display_name for x in Hosts.AVALIABLE_APIS]
        self.site_combo.set_active(api_names.index(last_site))

    def fill_mode_combobox(self):
        """ Fills the modes combobox with the avaliable modes
        to the current selected api. """

        try:
            last_mode = self.get_mode()
        except:
            last_mode = None

        self.avaliable_modes = []
        avaliable_modes = []

        for implementation in self.api.implements:
            if implementation in MODES:
                avaliable_modes.append(MODES[implementation])
                self.avaliable_modes.append(implementation)

        # Favorites it's present if shows it's.
        # And it's 2º in the combobox
        if "Shows" in self.avaliable_modes:
            avaliable_modes.insert(1, MODES["Favorites"])
            self.avaliable_modes.insert(1, "Favorites")

        if "Movies" in self.avaliable_modes:
            self.search_hbox.set_sensitive(True)
        else:
            self.search_hbox.set_sensitive(False)

        self.mode_liststore.clear()
        for mode in avaliable_modes:
            self.mode_liststore.append([mode])

        if last_mode in self.avaliable_modes:
            self.mode_combo.set_active(self.avaliable_modes.index(last_mode))
        else:
            self.mode_combo.set_active(0)

    def set_status_message(self, message):
        """ Sets the message shown in the statusbar.  """

        self.statusbar_label.set_label(message)

    def set_mode_shows(self, *args):
        """ Sets the current mode to shows. """

        self.sidebar.show()
        self.search_entry.set_text("")
        self.name_filter.set_text("")
        self.path_label.set_text("")
        self.name_list_model.clear()
        self.background_task(self.api.Show.search, self.display_shows,
                             status_message=gettext("Obtaining shows list"))

    def set_mode_movies(self):
        """ Sets the current mode to movies. """

        self.name_list_model.clear()
        self.search_entry.grab_focus()
        self.sidebar.hide()
        self.path_label.set_text("")
        self.name_filter.set_text("")

    def set_mode_favorites(self):
        """ Sets the current mode to favorites. """

        self.sidebar.show()
        self.search_entry.set_text("")
        self.path_label.set_text("")
        self.name_filter.set_text("")

        self.background_task(self.favorites.get_all, self.display_favorites,
                             status_message=gettext("Loading favorites"))

    def set_mode_latest(self):
        """ Sets the curret mode to latest movies. """

        self.sidebar.hide()
        self.background_task(self.api.Movie.get_latest, self.display_movies,
            status_message=gettext("Loading latest movies..."))

    def set_mode_recomended(self):
        """ Sets the curret mode to recomended movies. """

        self.sidebar.hide()
        self.background_task(self.api.Movie.get_recomended, self.display_movies,
            status_message=gettext("Loading recomended movies..."))

    def update_favorites(self, favorites):
        for fav_name in favorites:
            if fav_name not in self.favorites.get_all():
                self.favorites.add(fav_name)

        if self.get_mode() == "Favorites":
            self.set_mode_favorites()

    def get_mode(self):
        model = self.mode_combo.get_model()
        active = max(0, self.mode_combo.get_active())
        mode_text = self.avaliable_modes[active]

        return mode_text

    def get_site(self):
        """ Returns the current site. i.e the value of the mode combobox.
        The result will be the constant SITE_* (see constants definitions). """

        model = self.site_combo.get_model()
        active = self.site_combo.get_active()
        site_text = model[active][SITES_COLUMN_TEXT]
        site_module = model[active][SITES_COLUMN_OBJECT]

        return (site_text, site_module)

    def report_error(self, message):
        """ Shows up an error dialog to the user. """

        self.error_label.set_label(message)
        self.error_dialog.show_all()
        self.set_status_message("")
        self.unfreeze()

    def display_favorites(self, (is_error, result)):
        self.name_list_model.clear()

        if is_error:
            self.report_error(gettext("Error loading favorites: %s") % result)
            return

        for favorite in result:
            try:
                show = self.api.Show.search(favorite).next()
            except StopIteration:
                log.warn("didin't find %s in show list" % favorite)
                continue

            self.name_list_model.append([show.name, show])

    def display_shows(self, (is_error, result)):
        """ Displays the shows. """

        self.name_list_model.clear()
        self.file_viewer_model.clear()

        if is_error:
            if isinstance(result, NotImplementedError):
                message = gettext("Not avaliable for this site")
            else:
                message = gettext("Problem fetching shows:\n\n" \
                                  "details: %s") % result

            self.report_error(message)
            return

        for show in result:
            self.name_list_model.append([show.name, show])

    def display_seasons(self, (is_error, result)):
        """ Fills the file viewer with the seasons. """

        if is_error:
            message = gettext("Problem fetching seasons:\n\n" \
                              "details: %s") % result

            self.report_error(message)
            return

        self.file_viewer_model.clear()

        for season in result:
            self.file_viewer_model.append([ICON_FOLDER, season.name, season])

    def display_episodes(self, (is_error, result)):
        """ Fills the file viewer with the episodes. """

        if is_error:
            message = gettext("Problem fetching episodes:\n\n" \
                              "details: %s") % result

            self.report_error(message)
            return

        self.file_viewer_model.clear()
        marks = self.marks.get_all()

        # Add the 'up' folder
        self.file_viewer_model.append([ICON_FOLDER, "..", None])


        for episode in result:
            episode_name = "%s - %s" % (episode.number, episode.name)
            icon = ICON_FILE_MOVIE

            self.file_viewer_model.append([icon, episode_name, episode])

        self.refresh_marks()

    def refresh_marks(self):
        marks = self.marks.get_all()

        for row in self.file_viewer_model:
            iteration = self.file_viewer_model.get_iter(row.path)
            obj = row[FILE_VIEW_COLUMN_OBJECT]

            if not obj:
                continue

            if isinstance(obj, self.api.Movie):
                mark_string = "%s" % obj.name
            elif isinstance(obj, self.api.Episode):
                mark_string = "%s-%s-%s" % (self.current_show.name,
                    self.current_season.name, obj.name)

            if mark_string in marks:
                self.file_viewer_model.set_value(iteration,
                    FILE_VIEW_COLUMN_PIXBUF, ICON_FILE_MOVIE_MARK)

    def display_movies(self, (is_error, result)):
        """ Fills the file viewer with the movies from the search results. """

        if is_error:
            if isinstance(result, NotImplementedError):
                message = gettext("Not avaliable for this site")
            else:
                message = gettext("Problem fetching movies, " \
                                  "please try again in a few minutes.\n"
                                  "details: %s" % result)

            self.report_error(message)
            return

        self.file_viewer_model.clear()

        for movie in result:
            name = movie.name
            icon = ICON_FILE_MOVIE
            self.file_viewer_model.append([icon, name, movie])

        self.refresh_marks()


    # ================================
    # =         CALLBACKS            =
    # ================================

    def _on_destroy(self, *args):
        """ Called when the window closes.  """

        # Save window position and size
        window_pos = self.main_window.get_position()
        window_size = self.main_window.get_size()
        self.config.set_key("last_window_pos", window_pos)
        self.config.set_key("last_window_size", window_size)

        # We kill gtk
        gtk.main_quit()

    def _on_mode_change(self, *args):
        """ Called when the mode combobox changes value. """

        last_mode = self.get_mode()

        if last_mode not in self.avaliable_modes:
            return

        self.config.set_key("last_mode", last_mode)
        self.file_viewer_model.clear()

        # Call the corresponding set_mode method
        getattr(self, "set_mode_%s" % last_mode.lower().replace(" ", "_"))()

    def _on_site_change(self, *args):
        """ Called when the mode combobox changes value. """

        site_text, site_module = self.get_site()

        self.config.set_key("site", site_text)
        self.api = site_module

        self.file_viewer_model.clear()
        self.fill_mode_combobox()

    def _on_show_selected(self, tree_view, path, column):
        """ Called when the user selects a show from the name list. """

        self.file_viewer_model.clear()

        model = tree_view.get_model()
        selected_show = model[path][NAME_LIST_COLUMN_OBJECT]

        self.current_show = selected_show
        self.path_label.set_text(selected_show.name)

        def fetch_seasons():
            return [x for x in selected_show.seasons]

        self.background_task(fetch_seasons, self.display_seasons,
            status_message=gettext("Loading show %s...") % selected_show.name)

    def _on_file_viewer_open(self, widget, path, *args):
        """ Called when the user double clicks on a file
        inside the file viewer. """

        file_object = self.file_viewer_model[path][FILE_VIEW_COLUMN_OBJECT]

        mode = self.get_mode()

        if isinstance(file_object, self.api.Movie):
            Player(self, file_object)
        elif isinstance(file_object, self.api.Season):
            self.current_season = file_object

            self.path_label.set_text("%s / %s" % \
                    (self.current_show.name, self.current_season.name))

            def fetch_episodes():
                return [x for x in file_object.episodes]

            self.background_task(fetch_episodes, self.display_episodes)

        elif isinstance(file_object, self.api.Episode):
            Player(self, file_object)
        elif file_object == None:

            def fetch_seasons():
                return [x for x in self.current_show.seasons]

            self.background_task(fetch_seasons, self.display_seasons,
                status_message=gettext("Loading show %s...") % \
                                       self.current_show.name)

    def _on_name_filter_change(self, *args):
        """ Called when the textbox to filter names changes. """

        self.name_list_model_filter.refilter()

    def _on_name_filter_clear_clicked(self, *args):
        """ Clears the name filter input. """

        self.name_filter.set_text("")

    def _on_name_filter_keypress(self, widget, event):
        """ Called when the user presses a key in the name
        filter. It clears it out if the key is escape. """

        key = gtk.gdk.keyval_name(event.keyval)
        if key == "Escape":
            self.name_filter.set_text("")

    def _on_name_button_press(self, view, event):
        """ Called when the user press any mouse button on the name list. """

        if event.button == 3:  # 3 it's right click
            if self.get_mode() == "Favorites":
                popup_menu = self.builder.get_object("name_favorites_menu")
            else:
                popup_menu = self.builder.get_object("name_shows_menu")

            popup_menu.popup(None, None, None, event.button, event.time)

    def _on_add_favorite(self, *args):
        """ Adds the selected show from favorites.  """

        path, _ = self.name_list.get_cursor()
        model = self.name_list.get_model()
        selected = model[path][NAME_LIST_COLUMN_TEXT]

        if selected not in self.favorites.get_all():
            self.favorites.add(selected)

    def _on_remove_favorite(self, *args):
        """ Removes the selected show from favorites. """

        path, _ = self.name_list.get_cursor()
        model = self.name_list.get_model()
        selected = model[path][NAME_LIST_COLUMN_TEXT]

        if selected in self.favorites.get_all():
            self.favorites.remove(selected)
            self.set_mode_favorites()

    def _on_file_button_press(self, view, event):
        """ Called when the user press any mouse button on the file viewer. """

        if event.button == 3:  # Right button
            path, _ = view.get_cursor()
            model = view.get_model()
            file_object = model[path][FILE_VIEW_COLUMN_OBJECT]

            if isinstance(file_object, self.api.Episode) or \
               isinstance(file_object, self.api.Movie):
                self.file_viewer_menu.popup(None, None, None,
                    event.button, event.time)

    def _on_menu_play_clicked(self, *args):
        """ Called when the user click on the play context menu item. """

        path, _ = self.file_viewer.get_cursor()
        file_object = self.file_viewer_model[path][FILE_VIEW_COLUMN_OBJECT]
        Player(self, file_object)

    def _on_menu_download_only_clicked(self, widget):
        """ Called when the user click on the download only
        context menu item. """

        self._on_menu_download_clicked(widget, download_only=True)

    def _on_menu_download_clicked(self, widget, download_only=False):
        """ Called when the user click on the download and
        play context menu item. """

        chooser = gtk.FileChooserDialog(title=gettext("Dowload to..."),
                  parent=self.main_window,
                  action=gtk.FILE_CHOOSER_ACTION_SELECT_FOLDER,
                  buttons=(gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL,
                  gtk.STOCK_SAVE, gtk.RESPONSE_OK))

        last_download_dir = self.config.get_key("last_download_directory")
        chooser.set_current_folder(last_download_dir)
        response = chooser.run()

        if response != gtk.RESPONSE_OK:
            chooser.destroy()
            return

        save_to = chooser.get_filename()
        self.config.set_key("last_download_directory", save_to)
        chooser.destroy()

        path, _ = self.file_viewer.get_cursor()
        file_object = self.file_viewer_model[path][FILE_VIEW_COLUMN_OBJECT]
        Player(self, file_object, save_to, download_only=download_only)

    def _on_name_key_press(self, treeview, event):
        """ Called when the users presses a key on the name filter list. """

        chr_numbers = range(48, 57) + range(65, 91) + range(97, 123)
        acceptedchars = map(chr, chr_numbers)

        key = gtk.gdk.keyval_name(event.keyval)
        if key in acceptedchars:
            self.name_filter.set_text(key)
            self.name_filter.grab_focus()
            self.name_filter.set_position(len(self.name_filter.get_text()))

    def _on_choose_host(self, widget):
        """ Called when the user presses choose host from the context menu. """

        path, _ = self.file_viewer.get_cursor()
        file_object = self.file_viewer_model[path][FILE_VIEW_COLUMN_OBJECT]
        Player(self, file_object, choose_host=True)

    def mark_selected(self, *args):
        """ Called when the user clicks on Mark item in the context menu. """

        selection = self.file_viewer.get_selection()
        model, iteration = selection.get_selected()
        obj = model.get_value(iteration, FILE_VIEW_COLUMN_OBJECT)
        model.set_value(iteration, FILE_VIEW_COLUMN_PIXBUF, ICON_FILE_MOVIE_MARK)

        if isinstance(obj, self.api.Movie):
            mark_string = "%s" % obj.name
        elif isinstance(obj, self.api.Episode):
            mark_string = "%s-%s-%s" % (self.current_show.name,
                self.current_season.name, obj.name)

        self.marks.add(mark_string)

    def unmark_selected(self, *args):
        """ Called when the user clicks on Mark item in the context menu. """

        marks = self.marks.get_all()

        selection = self.file_viewer.get_selection()
        model, iteration = selection.get_selected()
        episode = model.get_value(iteration, FILE_VIEW_COLUMN_OBJECT)

        mark_string = "%s-%s-%s" % (self.current_show.name,
            self.current_season.name, episode.name)

        if episode.id in marks:
            model.set_value(iteration, FILE_VIEW_COLUMN_PIXBUF, ICON_FILE_MOVIE)
            self.marks.remove(episode.id)

        if mark_string in marks:
            model.set_value(iteration, FILE_VIEW_COLUMN_PIXBUF, ICON_FILE_MOVIE)
            self.marks.remove(mark_string)

    def open_in_original(self, *args):
        """ Open selected episode or movie on his original website. """

        path, _ = self.file_viewer.get_cursor()
        file_object = self.file_viewer_model[path][FILE_VIEW_COLUMN_OBJECT]
        try:
            url = file_object.original_url
        except NotImplementedError:
            self.report_error(gettext("Option not avaliable in this site"))
            return
        except:
            self.report_error(gettext("Error opening original url: %s") % error)
            return

        webbrowser.open(url)

    def _on_search_clear_clicked(self, *args):
        """ Clears the search input. """

        self.search_entry.set_text("")

    def _on_search_activate(self, *args):
        """ Called when the user does a search. """

        # Sets the correct mode
        self.set_mode_movies()
        self.mode_combo.set_active(self.avaliable_modes.index("Movies"))

        query = self.search_entry.get_text()
        self.background_task(self.api.Movie.search,
            self.display_movies, query,
            status_message=gettext("Searching movies with title %s...") % query)

    def _on_about_clicked(self, *args):
        """ Opens the about dialog. """

        self.about_dialog.run()
        self.about_dialog.hide()

    def _on_open_settings(self, *args):
        """ Called when the user opens the preferences from the menu. """

        self.settings_dialog.show()

    def _on_info_clicked(self, *args):
        """ Called when click on the context menu info item. """

        path, _ = self.file_viewer.get_cursor()
        file_object = self.file_viewer_model[path][FILE_VIEW_COLUMN_OBJECT]

        empty_case = gtk.gdk.pixbuf_new_from_file(IMAGE_CASE_EMPTY)
        self.info_image.set_from_pixbuf(empty_case)

        self.background_task(self.download_show_image, self.set_info_image,
                             file_object, freeze=False)

        def fetch_info():
            full_description = file_object.info["description"] + "\n\n" + \
                gettext("<b>Cast:</b> ") + ", ".join(file_object.info["cast"]) + "\n" + \
                gettext("<b>Genere:</b> ") + file_object.info["genere"] + "\n" + \
                gettext("<b>Language:</b> ") + file_object.info["language"]

            return file_object.name, full_description

        self.background_task(fetch_info, self.set_info, freeze=True)

    def set_info(self, (is_error, result)):
        if is_error:
            if isinstance(result, NotImplementedError):
                message = gettext("Information not supported for this site")
            else:
                message = gettext("Error downloading information: %s") % result

            self.report_error(message)
            return

        self.info_title.set_label(result[0])
        self.info_label.set_label(result[1])
        self.info_window.show()

    def _on_info_window_close(self, *args):
        """ Called when the info window is closed. """

        self.info_window.hide()

    def download_show_image(self, file_object):
        """ Downloads the current show image and returs the path to it. """

        self.unfreeze()

        images_dir = self.config.get_key("images_dir")
        if isinstance(file_object, self.api.Episode):
            name = file_object.show.name.lower()
        else:
            name = file_object.name.lower()

        name = name.replace(" ", "_") + ".jpg"
        image_path = os.path.join(images_dir, name)

        if not os.path.exists(image_path):
            url_open = urllib.urlopen(file_object.info["image"])
            img = open(image_path, "wb")
            img.write(url_open.read())
            img.close()
            url_open.close()

        return image_path

    def set_info_image(self, (is_error, result)):
        """ Sets the image of the current episode. """

        if is_error:
            msg = gettext("Problem downloading show image")
            self.set_status_message(msg)
            log.error(msg)
            log.error(result)
            return

        image_path = result

        pixbuf = gtk.gdk.pixbuf_new_from_file(image_path)
        case = gtk.gdk.pixbuf_new_from_file(IMAGE_CASE)

        width = pixbuf.props.width
        height = pixbuf.props.height

        case = case.scale_simple(width, height, gtk.gdk.INTERP_BILINEAR)
        case.composite(pixbuf, 0, 0, width, height, 0, 0, 1.0, 1.0,
                       gtk.gdk.INTERP_HYPER, 255)

        self.info_image.set_from_pixbuf(pixbuf)

    def on_player_finish(self, error):
        """
        Called when the user closes the player.
        """

        self._unfreeze()

        if error:
            self.set_status_message(str(error))

    def _on_hide_error_dialog(self, button):
        """ Called when the user closes the error dialog. """
        self.error_dialog.hide()


def generic_visible_func(model, iteration, (entry, text_column)):
    """
    Filters the treeview based on the text found on `entry`.
    text_column should be the column index where the text can be
    found.
    """

    filtered_text = entry.get_text()

    row_text = model.get_value(iteration, text_column)

    if row_text:
        # Case insensitive search
        filtered_text = filtered_text.lower()
        row_text = row_text.lower()

        return filtered_text in row_text

    return False
