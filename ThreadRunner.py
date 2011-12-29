#!/usr/bin/env python
# coding: utf-8

"""
ThreadRunner.

This module provides the class GtkThreadRunner that is used
to run a function on a thread and return the result when it's done
"""

import Queue
import threading
import traceback
import kaa
import time
from guicavane.Utils.Log import console
from StringIO import StringIO

class ThreadRunner(threading.Thread):
    """
    Run `func` in a thread with `args` and `kwargs` as arguments, when
    finished call callback with the result obtained or an exception caught.
    """

    def __init__(self, callback, func, *args, **kwargs):
        threading.Thread.__init__(self)
        self.setDaemon(True)

        self.callback = callback
        self.func = func
        self.args = args
        self.kwargs = kwargs

        self.result = Queue.Queue()

        self.start()
        self.check_thread = threading.Thread(target=self.check)
        self.check_thread.start()

    def run(self):
        """
        Main function of the thread, run func with args and kwargs
        and get the result, call callback with the result

        if an exception is thrown call callback with the exception
        """

        try:
            result = (False, self.func())
        except Exception, ex:
            result = (True, ex)

            if hasattr(self.func, "im_class"):
                if self.func.im_class == type:
                    methodname = "%s.%s" % (self.func.__self__.__name__, \
                                            self.func.im_func.func_name)
                else:
                    methodname = "%s.%s" % (self.func.im_class.__name__, \
                                            self.func.im_func.func_name)
            else:
                methodname = "%s" % self.func

            error_str = StringIO()
            error_str.write("running: %s, args: %s, kwargs: %s\nDetails:\n" % \
                (methodname, self.args, self.kwargs))

            traceback.print_exc(file=error_str)
            error_str.seek(0)
            print (error_str.read())

        self.result.put(result)

    def check(self):
        """ Check if func finished. """


        try:
            result = self.result.get(True, 300)
        except Queue.Empty:
            return True

        t = kaa.MainThreadCallback(self.callback, result)
	t()

        return False
