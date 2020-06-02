#!/usr/bin/env python3
import bandcamp
import redacted
import transcode

import re
import os
import sys
import json
import shutil
import mutagen
import argparse
import unicodedata
import configparser
import urllib.error
import urllib.request
import musicbrainzngs

from zipfile import ZipFile

import json

#https://redacted.ch/wiki.php?action=article&id=371
allowed_extensions = [".ac3", ".accurip", ".azw3", ".chm", ".cue", ".djv", ".djvu", ".doc", ".dmg", ".dts", ".epub", ".ffp", ".flac", ".gif", ".htm", ".html", ".jpeg", ".jpg", ".lit", ".log", ".m3u", ".m3u8", ".m4a", ".m4b", ".md5", ".mobi", ".mp3", ".mp4", ".nfo", ".pdf", ".pls", ".png", ".rtf", ".sfv", ".txt"]

#https://redacted.ch/wiki.php?action=article&id=44
tag_blacklist = ["vinyl", "flac", "soundtrack", "live", "soundboard", "hardcore", "garage", "freely.available"]

#https://redacted.ch/wiki.php?action=article&id=54
types = {
    "Album": "Album",
    "Compilation": "Compilation",
    "DJ-mix": "DJ Mix",
    "EP": "EP",
    "Interview": "Interview",
    "Live": "Live album",
    "Mixtape/Street": "Mixtape",
    "Remix": "Remix",
    "Single": "Single",
    "Soundtrack": "Soundtrack"
}

type_matches = {
    "Compilation": "Compilation",
    "Demo": "Demo",
    "EP": "EP",
    "E.P.": "EP",
    "Live": "Live album",
    "Mixtape": "Mixtape",
    "OST": "Soundtrack",
    "Remix": "Remix",
    "Single": "Single",
    "Soundtrack": "Soundtrack"
}

def clean(value):
    value = re.sub(r'[\|\/]', '-', str(value))
    value = re.sub(r'[<>:"\\|?*]', '', value).strip()
    return value

def slugify(value):
    value = unicodedata.normalize('NFKD', value).encode('ascii', 'ignore').decode('ascii')
    value = re.sub(r'[^\w\s-]', '', value).strip()
    return value

def guess_type(album):
    if len(album['tracks']) == 1:
        return "Single"

    for type in type_matches.keys():
        match = type.lower()
        if match in album['album'].lower() or match.replace(" ", "-") in album['tags']:
            return type_matches[type]
    
    return "Album"

def make_description(album):
    description = "[size=4][b]Tracklist[/b][/size]\n"
    i = 1
    for track in album['tracks']:
        description += "[b]" + str(i).rjust(2) + ".[/b]"
        description += " " + track['name'] + " "
        description += "[i](" + track['length'] + ")[/i]\n"
        i += 1

    description += "\n[b]Total Length:[/b] " + album['length'] + "\n"
    description += "\nMore Information: [url=" + album['url'] + "]Bandcamp[/url]"
    return description

def make_tagstr(album):
    blacklist = tag_blacklist
    album_name = album['album'].lower()
    artist_name = album['artist'].lower()

    blacklist.append(album_name)
    blacklist.append(artist_name)
    blacklist.append(album['release_year'])

    if " " in album_name:
        blacklist.append(re.sub(r'[ _]', '.', album_name))
    if " " in artist_name:
        blacklist.append(re.sub(r'[ _]', '.', artist_name))

    tags = []
    for tag in album['tags']:
        tag = re.sub(r'[ \-\/]', '.', tag).replace("&", "and").replace("'", "")
        if tag not in blacklist:
            tags.append(tag)

    return ", ".join(tags)

def print_album(album):
    print()
    print(f"Artist: {album['artist']}")
    if album['artist'] == "Various Artists":
        artists = ", ".join(album['artists'])
        print(f"Artists: {artists}")
    print(f"Album: {album['album']}")
    if 'release_title' in album:
        print(f"Release Title: {album['release_title']}")
    print(f"Release Type: {album['release_type']}")
    if 'initial_year' in album:
        print(f"Initial Year: {album['initial_year']}")
    print(f"Release Year: {album['release_year']}")
    if 'record_label' in album:
        print(f"Record Label: {album['record_label']}")
    if 'catalogue_number' in album:
        print(f"Catalogue Number: {album['catalogue_number']}")
    print(f"Format: FLAC")
    print(f"Bitrate: {album['bitrate']}")
    print(f"Media: WEB")
    print(f"Tags: {make_tagstr(album)}")
    print(f"Image: {album['cover_art']}")
    print(f"Release Description:\n\n{make_description(album)}\n")

def main():
    global tag_blacklist

    parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter, prog='redcamp')
    parser.add_argument('--config', help='Location of configuration file', default=os.path.expanduser('~/.redcamp/config'))
    parser.add_argument('--download-releases', help='Download releases from file', action='store_true')
    parser.add_argument('--release-file', help='Location of release file', default=os.path.expanduser('./releases.txt'))

    args = parser.parse_args()
    config = configparser.RawConfigParser()

    try:
        open(args.config)
        config.read(args.config)
    except:
        if not os.path.exists(os.path.dirname(args.config)):
            os.makedirs(os.path.dirname(args.config))
        config.add_section('redacted')
        config.set('redacted', 'username', '')
        config.set('redacted', 'password', '')
        config.set('redacted', 'session_cookie', '')
        config.set('redacted', 'data_dir', '')
        config.set('redacted', 'output_dir', '')
        config.set('redacted', 'torrent_dir', '')
        config.set('redacted', 'piece_length', '18')
        config.write(open(args.config, 'w'))
        print(f"Please edit the config file: {args.config}")
        sys.exit(0)

    data_dir = os.path.expanduser(config.get('redacted', 'data_dir'))
    output_dir = os.path.expanduser(config.get('redacted', 'output_dir'))
    torrent_dir = os.path.expanduser(config.get('redacted', 'torrent_dir'))

    #Read Cache
    cache_path = os.path.expanduser("~/.redcamp/cache")
    if os.path.exists(cache_path):
        with open(cache_path, 'r') as cache_file:
            cache = json.load(cache_file)
            cache_file.close()
    else:
        cache = {}

    #Download Releases
    if args.download_releases:
        with open(args.release_file, "r") as release_file:
            for release in release_file:
                line = release.strip().split(", ")

                release_url = line[0]
                download_link = line[1]

                #Get Headers
                try:
                    response = urllib.request.urlopen(download_link)
                except urllib.error.HTTPError:
                    print(f"[ERR] Invalid URL. Skipping...")
                    continue

                #Get Filename
                file_name = response.info().get_filename().encode('latin-1').decode('utf-8')
                file_path = os.path.join(output_dir, file_name)

                #Check if File Exists
                if os.path.exists(file_path):
                    continue

                #Download File
                while True:
                    try:
                        print(f"[INF] Downloading Release {file_name}")
                        urllib.request.urlretrieve(download_link, file_path)
                        break
                    except urllib.error.ContentTooShortError:
                        print("[ERR] Download Error. Restarting...")
                        os.remove(file_path)
                        continue

                cache[file_name] = release_url

    #Write Cache
    with open(cache_path, 'w') as cache_file:
        json.dump(cache, cache_file)
        cache_file.close()

    username = config.get('redacted', 'username')
    password = config.get('redacted', 'password')

    #Get Session Cookie if Exists
    try:
        session_cookie = os.path.expanduser(config.get('redacted', 'session_cookie'))
    except configparser.NoOptionError:
        session_cookie = None

    print("[INF] Logging in to RED")
    api = redacted.RedactedAPI(username, password, session_cookie)

    print("[INF] Logging in to MusicBrainz")
    musicbrainzngs.set_useragent("REDCamp", "1.0")

    #Get Candidates
    print("[INF] Getting Candidates")
    candidates = []
    for root, dirs, files in os.walk(output_dir):
        for file in files:
            if (re.match(r'^(.+) - (.+).zip$', file)):
                candidates.append(os.path.join(root, file))

    for release_file in candidates:
        #Unzip File
        base_file = os.path.basename(release_file)
        base_dir = base_file.rstrip(".zip")
        print(f"[INF] Unzipping {base_file}")
        release_dir = os.path.join(data_dir, base_dir)
        with ZipFile(release_file, 'r') as zf:
            zf.extractall(release_dir)
        
        album_name = ""
        artist_name = ""

        #Rename Files
        for root, dirs, files in os.walk(release_dir):
            for file in files:
                file_name, file_extension = os.path.splitext(file)
                if file_extension not in allowed_extensions:
                    os.remove(os.path.join(root, file))
                if file_extension == ".flac":
                    metadata = mutagen.File(os.path.join(root, file))
                    if not album_name and not artist_name:
                        album_name = metadata['album'][0]
                        artist_name = metadata['artist'][0]
                    new_file = metadata['tracknumber'][0].rjust(2, '0') + " " + clean(metadata['title'][0]) + ".flac"
                    os.rename(os.path.join(root, file), os.path.join(root, new_file))
        
        #Rename Directory
        new_dir = os.path.join(data_dir, clean(artist_name) + " - " + clean(album_name))
        os.rename(release_dir, new_dir)
        release_dir = new_dir

        #Get Album Info from Bandcamp
        print(f"[INF] Release: {album_name} by {artist_name}")
        if base_file in cache:
            url = cache[base_file]
        else:
            print(f"[INF] Searching Bandcamp for {album_name}")
            url = bandcamp.get_album_url(album_name, artist_name)
        if not url:
            print(f"[ERR] No Results for {album_name}")
            print("Enter Album URL: ", end="")
            url = input()

        album = bandcamp.get_album_info(url)
        if not album:
            print("[ERR] Invalid URL. Skipping...")
            shutil.rmtree(release_dir)
            continue

        #Get Album Info from MusicBrainz
        print(f"[INF] Searching MusicBrainz for {album_name}")
        releases = musicbrainzngs.search_releases(artist=album['artist'], release=album['album'], limit=5)
        for release in releases["release-list"]:
            for artist in release['artist-credit']:
                if type(artist) is not 'dict':
                    continue
                if artist['name'] == album['artist'] and release['title'] == album['album']:
                    #Get Release Type
                    print(f"[INF] Found Match {release['title']} by {artist['name']}")
                    primary_type = release['release-group']['primary-type']
                    secondary_types = release['release-group']['secondary-type-list']
                    for release_type in secondary_types:
                        if release_type in types.keys():
                            album['release_type'] = types[release_type]
                            break
                    else:
                        if primary_type in types.keys():
                            album['release_type'] = primary_type
                        else:
                            album['release_type'] = "Album"
                    #Get Record Label / Catalogue Number
                    for label in release['label-info-list']:
                        album['record_label'] = label['label']['name']
                        if 'catalog-number' in label:
                            album['catalogue_number'] = label['catalog-number']
                            break
                    break
            else:
                continue
            break

        #Guess Release Type
        if 'release_type' not in album:
            print("[WRN] No Release Type. Guessing...")
            album['release_type'] = guess_type(album)

        #Get Artists
        if album['release_type'] == "Compilation" or album['artist'] == "Various" or album['artist'] != artist_name:
            album['artists'] = []
            for track in album['tracks']:
                match = re.match(r'^(.+) - (.+)$', track['name'])
                if not match:
                    break
                artist = match.group(1)
                if artist not in album['artists']:
                    album['artists'].append(artist)
            else:
                album['release_type'] = "Compilation"
                album['artist'] = "Various Artists"

        #Check Bitrate
        if transcode.is_24bit(release_dir):
            album['bitrate'] = "24bit Lossless"
        else:
            album['bitrate'] = "Lossless"

        #Verify Release
        skip = False

        while True:
            print_album(album)

            if not len(make_tagstr(album)):
                print("[ERR] No Tags")
                print("Enter Tags: ", end="")
                album['tags'] = input().split(", ")
                continue

            print("[A]pply, [B]lacklist Tags, [E]dit, [S]kip")
            print("Select an option: ", end="")
            option = input()
            if option == "A":
                break
            elif option == "B":
                print("Tags: ", end="")
                tags = input().split(", ")
                tag_blacklist = tag_blacklist + tags
            elif option == "E":
                print("Album, Artist, Year, Title, Type, Label")
                print("Select an option: ", end="")
                edit = input()
                if edit == "Album":
                    print("Album: ", end="")
                    album['album'] = input()
                if edit == "Artist":
                    print("Artist: ", end="")
                    album['artist'] = input()
                elif edit == "Year":
                    print("Initial Year: ", end="")
                    album['initial_year'] = input()
                elif edit == "Title":
                    print("Release Title: ", end="")
                    album['release_title'] = input()
                elif edit == "Type":
                    print("Release Type: ", end="")
                    album['release_type'] = input()
                    if album['release_type'] == "Compilation":
                        print("Artists: ", end="")
                        album['artist'] = "Various Artists"
                        album['artists'] = input().split(", ")
                elif edit == "Label":
                    print("Record Label: ", end="")
                    album['record_label'] = input()
            elif option == "S":
                skip = True
                break

        if skip:
            shutil.rmtree(release_dir)
            continue

        #Make Tags and Description
        album['tags'] = make_tagstr(album)
        album['description'] = make_description(album)

        #Check for Duplicate Releases
        if album['artist'] == "Various Artists":
            artist = album['artists'][0]
        else:
            artist = album['artist']

        group = api.get_artist(artist=artist, format="FLAC")
        for release in group['torrentgroup']:
            if release['groupName'] == album['album']:
                for torrent in release['torrent']:
                    if torrent['format'] == "FLAC" and torrent['encoding'] == album['bitrate']:
                        print("[INF] Duplicate Release. Skipping...")
                        shutil.rmtree(release_dir)
                        break
                break

        #Make Torrent
        torrent = os.path.join(output_dir, slugify(album['album'])) + ".torrent"
        if not os.path.exists(torrent):
            transcode.make_torrent(torrent, release_dir, api.tracker, api.passkey, config.get('redacted', 'piece_length'))

        #Upload to RED
        permalink = api.upload(torrent, album)

        #Add Artists
        if album['artist'] == "Various Artists":
            for artist in album['artists']:
                api.add_artist(permalink, artist)

        #Move Torrent to Watch Folder
        shutil.move(torrent, torrent_dir)
        
        #Cleanup
        os.remove(release_file)

if __name__ == "__main__":
    main()
