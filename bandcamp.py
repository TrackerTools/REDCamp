import re
import urllib.error

from bs4 import BeautifulSoup
from datetime import datetime
from urllib.parse import quote
from urllib.request import urlopen

def calc_length(tracks):
    length = 0
    for track in tracks:
        if len(track['length']) == 5:
            m, s = track['length'].split(":")
            length += 60 * int(m) + int(s)
        else:
            h, m, s = track['length'].split(":")
            length += 60 * 60 * int(h) + 60 * int(m) + int(s)
    m, s = divmod(length, 60)
    if (m > 60):
        h, m = divmod(m, 60)
        return f'{h:d}:{m:02d}:{s:02d}'
    return f'{m:02d}:{s:02d}'

def parse_results(query, album_name, artist_name):
    soup = BeautifulSoup(urlopen(query).read(), 'html.parser')

    results = soup.find_all("li", {"class":"searchresult album"})

    for result in results:
        info = result.find("div", {"class":"result-info"})
        heading = info.find("div", {"class":"heading"}).find("a").contents[0]
        subhead = info.find("div", {"class":"subhead"}).contents[0]
        itemurl = info.find("div", {"class":"itemurl"}).find("a").contents[0]

        album = heading.strip()
        artist = subhead.strip().lstrip("by ")

        if album == album_name and artist == artist_name:
            return itemurl

    return None

def get_album_url(album_name, artist_name):
    query_urls = []
    query_urls.append('https://bandcamp.com/search?q=' + quote(album_name))
    query_urls.append('https://bandcamp.com/search?q=' + quote(artist_name))
    query_urls.append('https://bandcamp.com/search?q=' + quote(album_name) + "%20" + quote(artist_name))
    query_urls.append('https://bandcamp.com/search?q=' + quote(artist_name) + "%20" + quote(album_name))
    
    for query in query_urls:
        results = parse_results(query, album_name, artist_name)
        if results:
            return results
    
    return None

def get_album_info(url):
    try:
        soup = BeautifulSoup(urlopen(url).read(), 'html.parser')
    except urllib.error.HTTPError:
        return False

    album = soup.find("h2", {"class":"trackTitle"}).contents[0].strip().replace("\u200B", "")
    artist = soup.find("span", {"itemprop":"byArtist"}).find("a").contents[0].replace("\u200B", "")
    cover_art = soup.find("a", {"class": "popupImage"})['href']

    tracks = []
    tracklist = soup.find_all("td", {"class":"title-col"})
    for track in tracklist:
        name = track.find("span", {"class":"track-title"}).contents[0].replace("\u200B", "")
        element = track.find("span", {"class":"time secondaryText"})
        if not element:
            continue
        length = element.contents[0].strip()
        tracks.append({"name":name, "length":length})

    length = calc_length(tracks)

    credits = soup.find("div", {"class":"tralbumData tralbum-credits"}).contents[0].strip()
    release_year = datetime.strptime(credits.strip("released "), '%B %d, %Y').year

    tags = []
    taglist = soup.find_all("a", {"class":"tag"})
    for tag in taglist:
        tag_text = tag.contents[0]
        if tag_text.islower():
            tags.append(tag_text.strip())
    
    return {"album":album, "artist":artist, "cover_art":cover_art, "length":length, "release_year":release_year, "tracks":tracks, "tags":tags, "url":url}
