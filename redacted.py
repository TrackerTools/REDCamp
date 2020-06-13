import re
import os
import html
import json
import time
import logging
import requests
import mechanicalsoup

headers = {
    'Connection': 'keep-alive',
    'Cache-Control': 'max-age=0',
    'User-Agent': 'REDCamp',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Encoding': 'gzip,deflate,sdch',
    'Accept-Language': 'en-US,en;q=0.8',
    'Accept-Charset': 'ISO-8859-1,utf-8;q=0.7,*;q=0.3'
}

class LoginException(Exception):
    pass

class RequestException(Exception):
    pass

class RedactedAPI:
    def __init__(self, username=None, password=None, session_cookie=None, logger=None):
        self.session = requests.Session()
        self.session.headers.update(headers)
        self.username = username
        self.password = password
        self.session_cookie = session_cookie
        self.authkey = None
        self.passkey = None
        self.userid = None
        self.tracker = "https://flacsfor.me/"
        self.last_request = time.time()
        self.rate_limit = 2.0
        self.logger = logger
        self._login()

    def _login(self):
        if self.session_cookie is not None:
            try:
                self._login_cookie()
            except:
                self.logger.error("Invalid Session Cookie")
                self._login_username_password()
        else:
            self._login_username_password()

    def _login_cookie(self):
        '''Logs in user using session cookie'''
        mainpage = 'https://redacted.ch/'
        cookiedict = {"session": self.session_cookie}
        cookies = requests.utils.cookiejar_from_dict(cookiedict)

        self.session.cookies.update(cookies)
        r = self.session.get(mainpage)
        try:
            accountinfo = self.request('index')
            self.authkey = accountinfo['authkey']
            self.passkey = accountinfo['passkey']
            self.userid = accountinfo['id']
        except:
            raise LoginException

    def _login_username_password(self): 
        '''Logs in user using username and password'''
        if not self.username or self.username == "":
            self.logger.error("Username not set")
            raise LoginException
        loginpage = 'https://redacted.ch/login.php'
        data = {'username': self.username, 'password': self.password}
        r = self.session.post(loginpage, data=data)
        if r.status_code != 200:
            raise LoginException
        try:
            accountinfo = self.request('index')
            self.authkey = accountinfo['authkey']
            self.passkey = accountinfo['passkey']
            self.userid = accountinfo['id']
        except:
            raise LoginException

    def logout(self):
        self.session.get("https://redacted.ch/logout.php?auth=%s" % self.authkey)

    def request(self, action, **kwargs):
        '''Makes an AJAX request at a given action page'''
        while time.time() - self.last_request < self.rate_limit:
            time.sleep(0.1)

        ajaxpage = 'https://redacted.ch/ajax.php'
        params = {'action': action}
        if self.authkey:
            params['auth'] = self.authkey
        params.update(kwargs)
        r = self.session.get(ajaxpage, params=params, allow_redirects=False)
        self.last_request = time.time()
        if r.status_code == 404:
            return {}
        try:
            parsed = json.loads(r.content)
            if parsed['status'] != 'success':
                raise RequestException
            return parsed['response']
        except ValueError:
            raise RequestException

    def get_artist(self, artist=None, format=None):
        '''Get all releases for a given artist'''
        res = self.request('artist', artistname=artist)
        if 'torrentgroup' not in res:
            return {'torrentgroup': []}
        torrentgroups = res['torrentgroup']
        keep_releases = []
        for release in torrentgroups:
            #Remove Unicode Chars
            name = html.unescape(release['groupName']).encode('ascii', 'ignore')
            release['groupName'] = name.decode("utf-8")
            keeptorrents = []
            for t in release['torrent']:
                if not format or t['format'] == format:
                    keeptorrents.append(t)
            release['torrent'] = list(keeptorrents)
            if len(release['torrent']):
                keep_releases.append(release)
        res['torrentgroup'] = keep_releases
        return res

    def is_duplicate(self, release):
        artist = release['artist']
        if 'artists' in release and len(release['artists']):
            artist = release['artists'][0]

        group = self.get_artist(artist=artist, format="FLAC")
        for result in group['torrentgroup']:
            if result['groupName'] == release['album']:
                for torrent in result['torrent']:
                    if torrent['format'] == "FLAC" and torrent['encoding'] == release['bitrate']:
                        return True
                break

        return False

    #RED has an API endpoint for uploads now: ajax.php?action=upload
    #This function will be rewritten to use API keys in the future
    def upload(self, torrent, release):
        browser = mechanicalsoup.StatefulBrowser(
            soup_config={'features': 'lxml'},
            raise_on_404=True
        )

        browser.session.headers = self.session.headers
        browser.session.cookies = self.session.cookies
        browser.open("https://redacted.ch/upload.php")

        form = browser.select_form('form[class="create_form"]')

        if 'artists' in release and len(release['artists']):
            form.set("artists[]", release['artists'][0])
        else:
            form.set("artists[]", release['artist'])
        
        if 'release_title' in release:
            form.set("remaster_title", release['release_title'])
        if 'record_label' in release:
            form.set("remaster_record_label", release['record_label'])
        if 'remaster_catalogue_number' in release:
            form.set("remaster_catalogue_number", release['catalogue_number'])

        if 'initial_year' in release:
            form.set("year", release['initial_year'])
        else:
            form.set("year", release['release_year'])

        form.set("file_input", torrent)
        form.set("type", "0")
        form.set("title", release['album'])
        form.set("releasetype", release['release_type'])
        form.set("remaster_year", release['release_year'])
        form.set("format", "FLAC")
        form.set("bitrate", release['bitrate'])
        form.set("media", "WEB")
        form.set("tags", release['tags'])
        form.set("image", release['cover_art'])
        form.set("album_desc", release['album_description'])
        form.set("release_desc", release['release_description'])
        
        browser.submit_selected()

        return browser.get_url()

    def add_artist(self, permalink, artist):
        browser = mechanicalsoup.StatefulBrowser(
            soup_config={'features': 'lxml'},
            raise_on_404=True
        )

        browser.session.headers = self.session.headers
        browser.session.cookies = self.session.cookies
        browser.open(permalink)

        form = browser.select_form('form[class="add_form"]', 1)
        form.set("aliasname[]", artist)
        browser.submit_selected()
