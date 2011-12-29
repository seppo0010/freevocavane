# coding: utf-8

from guicavane.Player import Player
from guicavane.Accounts import ACCOUNTS
from gui.PopupBox import PopupBox
from ThreadRunner import ThreadRunner
import threading
import time

class GuiManagerEmulator(object):
    def __init__(self):
        self.accounts = ACCOUNTS
    def background_task(self, func, callback=None, *args, **kwargs):
        if callback == None:
            def real_callback((is_error, result)):
                pass
        else:
            def real_callback(result):
               callback(result)
        if "unfreeze" in kwargs : del kwargs["unfreeze"]
        if "freeze" in kwargs: del kwargs["freeze"]
        if "status_message" in kwargs: del kwargs["status_message"]
        ThreadRunner(real_callback, func, *args, **kwargs)

    def set_status_message(self, message):
        box = PopupBox(text=message)
        box.show()
        time.sleep(2)
        box.destroy()
