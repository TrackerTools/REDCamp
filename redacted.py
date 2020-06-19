import re
import os
import html
import json
import time
import logging
import requests

import utils

headers = {
    'Connection': 'keep-alive',
    'Cache-Control': 'max-age=0',
    'User-Agent': 'REDCamp',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Encoding': 'gzip,deflate,sdch',
    'Accept-Language': 'en-US,en;q=0.8',
    'Accept-Charset': 'ISO-8859-1,utf-8;q=0.7,*;q=0.3'
}

types = {
    "Album": 1,
    "Soundtrack": 3,
    "EP": 5,
    "Anthology": 6,
    "Compilation": 7,
    "Single": 9,
    "Live album": 11,
    "Remix": 13,
    "Bootleg": 14,
    "Interview": 15,
    "Mixtape": 16,
    "Demo": 17,
    "Concert Recording": 18,
    "DJ Mix": 19,
    "Unknown": 21
}

class LoginException(Exception):
    pass

class RequestException(Exception):
    pass

class RedactedAPI:
    def __init__(self, api_key=None, logger=None):
        self.session = requests.Session()
        self.session.headers.update(headers)
        self.api_key = api_key
        self.authkey = None
        self.passkey = None
        self.tracker = "https://flacsfor.me/"
        self.last_request = time.time()
        self.rate_limit = 2.0
        self.logger = logger
        self._login()

    def _login(self):
        '''Logs in user using API key'''
        mainpage = 'https://redacted.ch/'

        self.session.headers.update(Authorization=self.api_key)
        try:
            accountinfo = self.request('index')
            self.authkey = accountinfo['authkey']
            self.passkey = accountinfo['passkey']
        except:
            raise LoginException

    def request(self, action, **kwargs):
        '''Makes an AJAX request at a given action page'''
        while time.time() - self.last_request < self.rate_limit:
            time.sleep(0.1)

        ajaxpage = 'https://redacted.ch/ajax.php'
        params = {'action': action}
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
            print(r.status_code)
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

    def upload(self, torrent, release):
        upload = {}

        if 'artists' in release and len(release['artists']):
            for i, artist in enumerate(release['artists']):
                upload[f"artists[{i}]"] = artist
                upload[f"importance[{i}]"] = 1
        else:
            upload["artists[]"] = release['artist']
            upload["importance[]"] = 1

        if 'release_title' in release:
            upload["remaster_title"] = release['release_title']
        if 'record_label' in release:
            upload["remaster_record_label"] = release['record_label']
        if 'remaster_catalogue_number' in release:
            upload["remaster_catalogue_number"] = release['catalogue_number']

        if 'initial_year' in release:
            upload["year"] = int(release['initial_year'])
        else:
            upload["year"] = int(release['release_year'])

        upload["type"] = 0
        upload["title"] = release['album']
        upload["releasetype"] = types[release['release_type']]
        upload["remaster_year"] = int(release['release_year'])
        upload["format"] = "FLAC"
        upload["bitrate"] = release['bitrate']
        upload["media"] = "WEB"
        upload["tags"] = release['tags']
        upload["image"] = release['cover_art']
        upload["album_desc"] = release['album_description']
        upload["release_desc"] = release['release_description']

        files = {'file_input': open(torrent, 'rb')}

        r = self.session.post('https://redacted.ch/ajax.php?action=upload', data=upload, files=files)
        return json.loads(r.content)

    #We have to use a session cookie here because the API doesn't have a report endpoint
    def report_lossy(self, session_cookie, torrent, image, url):
        cookies = {'session': session_cookie}
        data = {'categoryid': 1, 'submit': True, 'type': 'lossywebapproval'}

        data['auth'] = self.authkey
        data['torrentid'] = int(torrent)
        data['proofimages'] = image
        data['extra'] = f"Downloaded from [url={url}]Bandcamp[/url]"

        r = requests.post('https://redacted.ch/reportsv2.php?action=takereport', cookies=cookies, data=data, headers=headers)
        return r.content