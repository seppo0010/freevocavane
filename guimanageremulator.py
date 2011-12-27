# coding: utf-8

from guicavane.Player import Player
from guicavane.Accounts import ACCOUNTS
from gui.PopupBox import PopupBox
import threading

class GuiManagerEmulator(object):
    def __init__(self):
        self.accounts = ACCOUNTS
    def background_task(self, func, callback=None, *args, **kwargs):
       def real_callback():
           try:
               callback((False, func()))
           except Exception as e:
               self.set_status_message(str(e))
               callback((True, None))
       thread = threading.Thread(target=real_callback)
       thread.start()
    def set_status_message(self, message):
        box = PopupBox(text=message)
        box.show()
        time.sleep(2)
        box.destroy()
