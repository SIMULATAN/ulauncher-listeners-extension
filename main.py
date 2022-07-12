import struct
import sys
import time
import socket
from http.client import HTTPConnection

import psutil
import webbrowser

from time import sleep
from subprocess import Popen, PIPE
from subprocess import check_output
from urllib.parse import urlparse

from ulauncher.api.client.Extension import Extension
from ulauncher.api.client.EventListener import EventListener
from ulauncher.api.shared.event import KeywordQueryEvent, ItemEnterEvent
from ulauncher.api.shared.item.ExtensionResultItem import ExtensionResultItem
from ulauncher.api.shared.action.RenderResultListAction import RenderResultListAction
from ulauncher.api.shared.action.ExtensionCustomAction import ExtensionCustomAction
from ulauncher.api.shared.action.OpenUrlAction import OpenUrlAction

ACTION_GOTO_ADDR = 'goto_local_addr'
ICON_PATH = "images/icon.png"

OPTION_BROWSER_SELECTOR = "browser_selector"
OPTIONVAL_BRS_DEFAULT = "default"
OPTIONVAL_BRS_CUSTOM = "custom"
OPTION_BROWSER_EXECUTABLE = "browser_executable"


class LocalListenersExtension(Extension):

    def __init__(self):
        super(LocalListenersExtension, self).__init__()
        self.subscribe(KeywordQueryEvent, KeywordQueryEventListener())
        self.subscribe(ItemEnterEvent, ItemEnterEventListener())


class KeywordQueryEventListener(EventListener):

    def on_event(self, event: KeywordQueryEvent, extension):
        query = event.get_argument()
        items = []

        lc = psutil.net_connections("inet")

        def get_pid_name(name):
            try:
                return struct.unpack(">d", check_output(["ps", "-p", name, "-o", "comm="]))
            except Exception:
                return None

        listeners = []
        for c in lc:
            (ip, port) = c.laddr

            if c.type == socket.SOCK_STREAM and c.status == psutil.CONN_LISTEN:
                pid_name = "(unknown)"
                if c.pid:
                    name = get_pid_name(str(c.pid))
                    if name:
                        pid_name = name.strip()
                listeners.append([pid_name, str(ip), str(port)])

        if query:
            listeners = [p for p in listeners if query.lower() in p[1].lower()]

        if listeners and len(listeners) > 0:
            col_width = max(len(listener[0]) for listener in listeners) + 2
            for listener in listeners:
                address = listener[1] + ":" + listener[2]
                data = {"action": ACTION_GOTO_ADDR, "address": address}
                items.append(ExtensionResultItem(icon=ICON_PATH,
                                                 name=str(listener[0]).ljust(col_width) + address,
                                                 description="Browse to " + address,
                                                 on_enter=ExtensionCustomAction(data, keep_app_open=False)))
        else:
            items = [ExtensionResultItem(icon=ICON_PATH,
                                        name="No local listeners found",
                                        description="No local listeners found",
                                        # there are no results so ulauncher shouldn't highlight the query in this "result"
                                        highlightable=False)]

        return RenderResultListAction(items)


class ItemEnterEventListener(EventListener):

    def check_url(self, url):
        url = urlparse(url)
        conn = HTTPConnection(url.netloc)
        conn.request("HEAD", url.path)
        if conn.getresponse():
            return True
        else:
            return False

    def add_scheme(self, address):
        url_http = "http://" + address
        url_https = "https://" + address
        if self.check_url(url_https):
            return url_https
        elif self.check_url(url_http):
            return url_http

        return None

    def on_event(self, event, extension):
        data = event.get_data()
        items = []

        if data["action"] == ACTION_GOTO_ADDR:
            url = self.add_scheme(data["address"])
            if url == None:
                return
            else:
                if extension.preferences[OPTION_BROWSER_SELECTOR] == OPTIONVAL_BRS_DEFAULT:
                    webbrowser.open_new_tab(url)
                elif extension.preferences[OPTION_BROWSER_SELECTOR] == OPTIONVAL_BRS_CUSTOM:
                    command = [extension.preferences[OPTION_BROWSER_EXECUTABLE]]
                    command.append(data["address"])
                    Popen(command)

            return

        return RenderResultListAction(items)


if __name__ == "__main__":
    LocalListenersExtension().run()
