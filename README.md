## Introduction
`redcamp` is a script which assists in the process of uploading Bandcamp releases to Redacted. Inspired by [REDBetter](https://github.com/Mechazawa/REDBetter-crawler)

## Disclaimers
* This script is meant as a helper tool, not a fully automated uploader. **Please review all your uploads before making them.** Failure to do so can result in a warning or worse.
* Bandcamp has no restrictions on what can be uploaded. The script has no way to discern a good release from a "spam release". Please make sure your upload meets the criteria before uploading.
> Zero Effort, Spam Releases - Creators that prolifically release zero effort content of no value (e.g Paul_DVR, Vap0rwave, Firmensprecher, Phyllomedusa, stretches), often solely for the purpose of spam or upload gain.
* Although most FLACs on Bandcamp are true lossless, some are lossy that have been transcoded. The script uses Lossless Audio Checker to check for possible transcodes, but it isn't 100% accurate. Please check the spectrals for each release before uploading.
* The script is not perfect, and sometimes makes mistakes. Use at your own risk.

## Dependencies

* Python 3.6 or newer
* `mktorrent`
* `coloredlogs`, `musicbrainzngs`, `mutagen`, `ptpimg_uploader`, and `verboselogs` Python modules
* `sox` and `ffmpeg`
* [Lossless Audio Checker](http://losslessaudiochecker.com/)
* [Firefox](https://www.mozilla.org/en-US/firefox/) (for `scrape.py`)
* `geckodriver_autoinstaller` and `selenium` Python modules (for `scrape.py`)


## Installation
> :information_source: If you have Python installed, run `setup.sh` to install and configure all of the necessary dependencies (requires sudo).

#### 1. Install Python

Python is available [here](https://www.python.org/downloads/).

#### 2. Install `mktorrent`

`mktorrent` must be built from source, rather than installed using a package manager. For Linux systems, run the following commands in a temporary directory:

~~~~
$> git clone git@github.com:Rudde/mktorrent.git
$> cd mktorrent
$> make && sudo make install
~~~~

If you are on a seedbox and you lack the privileges to install packages, you are best off contacting your seedbox provider and asking them to install the listed packages.

#### 3. Install `coloredlogs`, `musicbrainzngs`, `mutagen`, `ptpimg_uploader`, and `verboselogs` Python Modules

~~~~
pip install -r requirements.txt
~~~~

#### 4. Install `sox` and `ffmpeg`

These should all be available on your package manager of choice:
  * Debian: `sudo apt-get install sox ffmpeg`
  * Ubuntu: `sudo apt install sox ffmpeg`
  * macOS: `brew install sox ffmpeg`

#### 5. Install Lossless Audio Checker

For Linux systems, run the following commands in the script's directory:

~~~~
wget --content-disposition "http://losslessaudiochecker.com/dl/LAC-Linux-64bit.tar.gz"
tar xzvf LAC-Linux-64bit.tar.gz
rm LAC-Linux-64bit.tar.gz
~~~~

> :information_source: Step 6 and 7 only required if you want to run `scrape.py`.

#### 6. Install Firefox

Firefox is available [here](https://www.mozilla.org/en-US/firefox/new/).

#### 7. Install `geckodriver_autoinstaller` and `selenium` Python Modules

~~~~
pip install geckodriver_autoinstaller selenium
~~~~


### Configuration
Run `redcamp` by running the script included when you cloned the repository:

    $> ./redcamp.py

You will receive a notification stating that you should edit the configuration file located at:

    ~/.redcamp/config

Open this file in your preferred text editor, and configure as desired. The options are as follows:

##### redacted

* `api_key`: Your redacted.ch API key. Generate one in your access settings under your profile.
* `session_cookie`: Your redacted.ch session_cookie (optional).
* `data_dir`: The directory where your torrent downloads are stored.
* `output_dir`: The directory where the releases will be downloaded to.
* `torrent_dir`: The directory where the generated `.torrent` files are stored.

##### ptpimg

* `api_key`: Your ptpimg.me API key. To find it, login to https://ptpimg.me, open the page source (i.e. "View -> Developer -> View source" menu in Chrome), find the string api_key and copy the hexademical string from the value attribute.

You should also edit the variables `blacklisted_tags` and `cutoff_year` in `scrape.py`

## Usage
~~~~
usage: redcamp [-h] [--config CONFIG] [--download-releases] [--release-file RELEASE_FILE]

optional arguments:
  -h, --help            show this help message and exit
  --config CONFIG       Location of configuration file (default: ~/.redcamp/config)
  --download-releases   Download releases from file (default: False)
  --release-file RELEASE_FILE
                        Location of release file (default: ./releases.txt)
~~~~

### Examples
To scrape the Bandcamp homepage for new free releases:

    $> ./scrape.py

When you run the script it will ask for you the number of releases to grab, I recommend no more than 50 at a time. It will scrape the release URL and the download link (FLAC) and save them to `releases.txt`. This script requires Firefox ≥ 60 and `geckodriver`. If you have issues using this script I recommend commenting out the line `options.headless = True` and running it on a machine with a desktop environment so you can observe the output. If your Firefox version is too old run it on a different machine and copy the release file manually.

To download the releases in `releases.txt` and upload them:

    $> ./redcamp.py --download-releases

To process and upload the releases in `output_dir`:

    $> ./redcamp.py

If your releases are downloaded automatically REDCamp caches the URLs for later use, otherwise it will attempt to search Bandcamp for the album. Releases from Bandcamp follow the format "\<artist> - \<album>.zip". Releases are tagged using metadata from Bandcamp and MusicBrainz. If information is missing it will prompt the user to enter it manually. The script also checks if a release is a duplicate on Redacted and skips it.

Spectrals are automatically generated using `mkspectrograms.sh` and uploaded to ptpimg.me. If a session cookie is added, you can also report the album as a Lossy WEB. 

## Bugs and Feature Requests
If you have any issues using the script, or would like to suggest a feature, feel free to open an issue in the issue tracker, *provided that you have searched for similar issues already*. Pull requests are also welcome.

## Credits
* [Mechazawa](https://github.com/Mechazawa) for [REDBetter](https://github.com/Mechazawa/REDBetter-crawler)
* [AnstrommFeck](https://redacted.ch/user.php?id=7191) for [mkspectrograms.sh](https://redacted.ch/forums.php?action=viewthread&threadid=42695)
* [Lossless Audio Checker](http://losslessaudiochecker.com/)