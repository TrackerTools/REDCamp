#!/usr/bin/env python3

import bandcamp
import redacted
import transcode
import utils

import re
import os
import sys
import json

import argparse
import configparser
import hashlib
import shutil
import urllib.error
import urllib.request

import coloredlogs
import logging
import verboselogs

import musicbrainzngs
import mutagen

allowed_extensions = [".ac3", ".accurip", ".azw3", ".chm", ".cue", ".djv", ".djvu", ".doc", ".dmg", ".dts", ".epub", ".ffp", ".flac", ".gif", ".htm", ".html", ".jpeg", ".jpg", ".lit", ".log", ".m3u", ".m3u8", ".m4a", ".m4b", ".md5", ".mobi", ".mp3", ".mp4", ".nfo", ".pdf", ".pls", ".png", ".rtf", ".sfv", ".txt"]

tag_blacklist = ["web", "flac", "compilation", "demo", "dj.mix", "ep", "mixtape", "remix", "single", "soundtrack", "live", "soundboard", "hardcore", "garage"]

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

verboselogs.install()
logger = logging.getLogger(__name__)
coloredlogs.DEFAULT_LOG_FORMAT='%(levelname)s %(message)s'
coloredlogs.install(level='INFO', logger=logger)

def rename_tracks(dir):
    album = None
    artist = None

    for root, dirs, files in os.walk(dir):
        for file in files:
            file_name, file_extension = os.path.splitext(file)
            if file_extension not in allowed_extensions:
                os.remove(os.path.join(root, file))
            if file_extension == ".flac":
                file_path = os.path.join(root, file)
                metadata = mutagen.File(file_path)
                if not album and not artist:
                    album = metadata['album'][0]
                    artist = metadata['artist'][0]
                new_file = metadata['tracknumber'][0].rjust(2, '0') + " " + utils.clean(metadata['title'][0]) + ".flac"
                os.rename(file_path, os.path.join(root, new_file))

    return [album, artist]

def rename_dir(dir, artist, album):
    parent_dir = os.path.dirname(dir)
    new_dir = os.path.join(parent_dir, utils.clean(artist) + " - " + utils.clean(album) + " [FLAC]")
    os.rename(dir, new_dir)
    return new_dir

def search_musicbrainz(release):
    results = musicbrainzngs.search_releases(artist=release['artist'], release=release['album'], limit=5)
    for result in results["release-list"]:
        for artist in result['artist-credit']:
            if type(artist) is not 'dict':
                continue
            if artist['name'] == release['artist'] and result['title'] == release['album']:
                #Get Release Type
                logger.info(f"Result: {result['title']} by {artist['name']}")
                primary_type = result['release-group']['primary-type']
                secondary_types = result['release-group']['secondary-type-list']
                for release_type in secondary_types:
                    if release_type in types.keys():
                        release['release_type'] = types[release_type]
                        break
                else:
                    if primary_type in types.keys():
                        release['release_type'] = primary_type
                    else:
                        release['release_type'] = "Album"
                #Get Record Label / Catalogue Number
                for label in result['label-info-list']:
                    release['record_label'] = label['label']['name']
                    if 'catalog-number' in label:
                        release['catalogue_number'] = label['catalog-number']
                        break
                return

def guess_type(release):
    if len(release['tracks']) == 1:
        return "Single"

    if release['artist'] == "Various":
        return "Compilation"

    for type in type_matches.keys():
        match = type.lower()
        if match in release['album'].lower() or match in release['tags']:
            return type_matches[type]
    
    return "Album"

def add_artists(release):
    release['artists'] = []
    for track in release['tracks']:
        match = re.match(r'^(.+) - (.+)$', track['name'])
        if not match:
            break
        artist = match.group(1)
        if artist not in release['artists']:
            release['artists'].append(artist)
    else:
        release['release_type'] = "Compilation"
        release['artist'] = "Various Artists"


def make_album_desc(release):
    description = "[size=4][b]Tracklist[/b][/size]\n"

    for i, track in enumerate(release['tracks']):
        description += "[b]" + str(i + 1).rjust(2) + ".[/b]"
        description += " " + track['name'] + " "
        description += "[i](" + track['length'] + ")[/i]\n"

    description += "\n[b]Total Length:[/b] " + release['length'] + "\n"
    description += "\nMore Information: [url=" + release['url'] + "]Bandcamp[/url]"

    return description

def make_release_desc(release, links):
    description = "[hide=Spectrograms]\n"

    for link in links:
        description += f"[img]{link}[/img]\n"
    
    description += "[/hide]"
    description += "\n\nUploaded using [url=https://github.com/TrackerTools/REDCamp]REDCamp[/url]"

    return description

def make_tagstr(release):
    blacklist = tag_blacklist

    blacklist.append(re.sub(r'[ _\-\/]', '.', release['album'].lower()))
    blacklist.append(re.sub(r'[ _\-\/]', '.', release['artist'].lower()))
    blacklist.append(str(release['release_year']))

    tags = []
    for tag in release['tags']:
        tag = re.sub(r'[ _\-\/]', '.', tag).strip(".")
        tag = re.sub(r'[\'\(\)]', '', tag.replace("&", "and"))
        if tag not in blacklist and tag not in tags:
            tags.append(tag)

    return ", ".join(tags)

def print_release(release):
    print("-----------------------------------------")
    print(f"Artist: {release['artist']}")
    if 'artists' in release and len(release['artists']):
        artists = ", ".join(release['artists'])
        print(f"Artists: {artists}")
    print(f"Album: {release['album']}")
    if 'release_title' in release:
        print(f"Release Title: {release['release_title']}")
    print(f"Release Type: {release['release_type']}")
    if 'initial_year' in release:
        print(f"Initial Year: {release['initial_year']}")
    print(f"Release Year: {release['release_year']}")
    if 'record_label' in release:
        print(f"Record Label: {release['record_label']}")
    if 'catalogue_number' in release:
        print(f"Catalogue Number: {release['catalogue_number']}")
    print(f"Format: FLAC")
    print(f"Bitrate: {release['bitrate']}")
    print(f"Media: WEB")
    print(f"Tags: {make_tagstr(release)}")
    print(f"Image: {release['cover_art']}")
    print(f"Album Description:\n{make_album_desc(release)}\n")
    print(f"Release Description:\n{release['release_description']}")
    print("-----------------------------------------")

def main():
    parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter, prog='redcamp')
    parser.add_argument('--config', help='Location of configuration file', default=os.path.expanduser('~/.redcamp/config'))
    parser.add_argument('--cache', help='Location of cache file', default=os.path.expanduser('~/.redcamp/cache'))
    parser.add_argument('--download-releases', help='Download releases from file', action='store_true')
    parser.add_argument('--release-file', help='Location of release file', default=os.path.abspath('./releases.txt'))

    args = parser.parse_args()
    config = configparser.RawConfigParser()

    try:
        open(args.config)
        config.read(args.config)
    except:
        if not os.path.exists(os.path.dirname(args.config)):
            os.makedirs(os.path.dirname(args.config))
        config.add_section('redacted')
        config.set('redacted', 'api_key', '')
        config.set('redacted', 'session_cookie', '')
        config.set('redacted', 'data_dir', '')
        config.set('redacted', 'output_dir', '')
        config.set('redacted', 'torrent_dir', '')
        config.set('redacted', 'piece_length', '18')
        config.add_section('ptpimg')
        config.set('ptpimg', 'api_key', '')
        config.write(open(args.config, 'w'))
        logging.error(f"Please edit the config file: {args.config}")
        sys.exit(0)

    data_dir = os.path.expanduser(config.get('redacted', 'data_dir'))
    output_dir = os.path.expanduser(config.get('redacted', 'output_dir'))
    torrent_dir = os.path.expanduser(config.get('redacted', 'torrent_dir'))

    #Read Cache
    cache = utils.read_file(args.cache)
    if cache:
        cache = json.loads(cache)
    else:
        cache = {}

    #Download Releases
    if args.download_releases:
        for release in utils.read_file(args.release_file).strip().split("\n"):
            release_url, download_link = release.split(", ")

            try:
                response = urllib.request.urlopen(download_link)
            except urllib.error.HTTPError:
                logger.error(f"Invalid URL. Skipping...")
                continue

            file_name = response.info().get_filename().encode('latin-1').decode('utf-8')
            file_path = os.path.join(output_dir, file_name)

            if os.path.exists(file_path):
                continue

            while True:
                try:
                    logger.info(f"Downloading Release: {file_name}")
                    urllib.request.urlretrieve(download_link, file_path)
                    break
                except urllib.error.ContentTooShortError:
                    logger.error("Download Error. Restarting...")
                    os.remove(file_path)
                    continue

            cache[file_name] = release_url

    #Write Cache
    utils.write_file(args.cache, json.dumps(cache, indent=4, sort_keys=True))

    api_key = config.get('redacted', 'api_key')

    try:
        session_cookie = os.path.expanduser(config.get('redacted', 'session_cookie'))
    except configparser.NoOptionError:
        session_cookie = None

    logger.info("Logging in to RED")
    api = redacted.RedactedAPI(api_key, logger)

    logger.info("Logging in to MusicBrainz")
    musicbrainzngs.set_useragent("REDCamp", "1.0", "https://github.com/TrackerTools/REDCamp")

    #Get Candidates
    logger.info("Getting Candidates")
    candidates = []
    for root, dirs, files in os.walk(output_dir):
        for file in files:
            if (re.match(r'^(.+) - (.+).zip$', file)):
                candidates.append(os.path.join(root, file))

    for release_path in candidates:
        #Unzip File
        release_file = os.path.basename(release_path)
        release_dir = utils.unzip_file(release_path, data_dir)

        #Rename Files
        album, artist = rename_tracks(release_dir)
        
        #Rename Directory
        release_dir = rename_dir(release_dir, artist, album)

        #Get Album Info from Bandcamp
        logger.info(f"Release: {album} by {artist}")
        if release_file in cache:
            url = cache[release_file]
        else:
            logger.info(f"Searching Bandcamp for {album}")
            url = bandcamp.get_album_url(album, artist)
        if not url:
            logger.error(f"No Results for {album}")
            url = input("Enter Album URL: ")

        release = bandcamp.get_album_info(url)
        if not release:
            logger.error("Invalid URL. Skipping...")
            shutil.rmtree(release_dir)
            continue

        #Get Album Info from MusicBrainz
        logger.info(f"Searching MusicBrainz for {album}")
        search_musicbrainz(release)

        #Guess Release Type
        if 'release_type' not in release:
            logger.warning("[WRN] No Release Type. Guessing...")
            release['release_type'] = guess_type(release)

        #Check Compilation
        if release['release_type'] == "Compilation" or release['artist'] != artist:
            add_artists(release)

        #Check Bitrate
        if transcode.is_24bit(release_dir):
            release['bitrate'] = "24bit Lossless"
        else:
            release['bitrate'] = "Lossless"

        #Check Lossless
        result = transcode.is_lossless(release_dir)
        if result != "Clean":
            logger.warning(f"LAC Reports Release as {result}")
            logger.warning(f"Please Check Spectrals")

        #Generate Spectrograms
        logger.info("Generating Spectrograms")
        spectral_links = transcode.make_spectrograms(release_dir, config.get('ptpimg', 'api_key'))
        release['release_description'] = make_release_desc(release, spectral_links)

        #Review Release
        skip = False

        while True:
            print_release(release)

            if not len(make_tagstr(release)):
                logger.error("No Tags")
                release['tags'] = input("Enter Tags: ").split(", ")
                continue

            print("[A]pply, [B]lacklist Tags, [E]dit, [S]kip")
            option = input("Select an option: ")

            if option == "A":
                break
            elif option == "B":
                tag_blacklist.extend(input("Tags: ").split(", "))
            elif option == "E":
                print("Album, Artist, Year, Title, Type, Label")
                edit = input("Select an option: ")
                if edit == "Album":
                    release['album'] = input("Album: ")
                if edit == "Artist":
                    release['artist'] = input("Artist: ")
                elif edit == "Year":
                    release['initial_year'] = input("Initial Year: ")
                elif edit == "Title":
                    release['release_title'] = input("Release Title: ")
                elif edit == "Type":
                    release['release_type'] = input("Release Type: ")
                    if release['release_type'] == "Compilation":
                        release['artists'] = input("Artists: ").split(", ")
                        release['artist'] = "Various Artists"
                elif edit == "Label":
                    release['record_label'] = input("Record Label: ")
            elif option == "S":
                skip = True
                break

        if skip:
            shutil.rmtree(release_dir)
            continue

        #Make Tags and Description
        release['tags'] = make_tagstr(release)
        release['album_description'] = make_album_desc(release)

        #Check for Duplicate Releases
        if api.is_duplicate(release):
            logger.info("Duplicate Release. Skipping...")
            shutil.rmtree(release_dir)
            break

        #Make Torrent
        torrent = os.path.join(output_dir, f"redcamp_{str(int(hashlib.md5(release_file.encode('utf-8')).hexdigest(), 16))[0:12]}.torrent")
        if not os.path.exists(torrent):
            transcode.make_torrent(torrent, release_dir, api.tracker, api.passkey, config.get('redacted', 'piece_length'))

        #Upload to RED
        response = api.upload(torrent, release)
        
        if response['status'] == 'failure':
            logging.error(f"Upload Failed: {response['error']}")
            shutil.rmtree(release_dir)
            os.remove(torrent)
            continue

        torrentid = response['response']['torrentid']
        logger.success(f"Uploaded to https://redacted.ch/torrents.php?torrentid={torrentid}")

        shutil.move(torrent, torrent_dir)

        #Report Lossy WEB
        if session_cookie:
            option = input("Report Lossy WEB? [y/n]: ")
            if option == "y":
                api.report_lossy(session_cookie, torrentid, spectral_links[0], release['url'])

        os.remove(release_path)

if __name__ == "__main__":
    main()