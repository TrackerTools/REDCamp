## Introduction
`redcamp` is a script which automates the process of uploading free Bandcamp releases to Redacted. Inspired by [REDBetter](https://github.com/Mechazawa/REDBetter-crawler)

## Disclaimers
* This script is meant as a helper tool, not a fully automated uploader. **Please review all your uploads before making them.** Failure to do so can result in a warning or worse.
* Bandcamp has no restrictions on what can be uploaded. The script has no way to discern a good release from a "spam release". Please make sure your upload meets the criteria before uploading.
> Zero Effort, Spam Releases - Creators that prolifically release zero effort content of no value (e.g Paul_DVR, Vap0rwave, Firmensprecher, Phyllomedusa, stretches), often solely for the purpose of spam or upload gain.
* Although most FLACs on Bandcamp are true lossless, some are lossy that have been transcoded. The script does not check spectrals, and failure to report a lossy WEB after uploading can result in a warning.
* The script is not perfect, and sometimes makes mistakes. Use at your own risk.

## Installation
### Dependencies
* Python 3.5 or newer
* `coloredlogs`, `mechanicalsoup`, `musicbrainzngs`, `mutagen`, `ptpimg_uploader`, and `selenium` Python modules. You can install these with `pip install -r requirements.txt`. Depending on your user priveleges, you may need to use `sudo`, so try: `sudo -H pip install -r requirements.txt`
* [`geckodriver`](https://github.com/mozilla/geckodriver/releases): This requires Firefox and a desktop environment. Make sure it’s in your PATH, e.g., place it in /usr/bin or /usr/local/bin.
* [`sox`](http://sox.sourceforge.net/): This should be available on your package manager of choice.
* [`mktorrent`](https://github.com/Rudde/mktorrent): Just installing it with a package manager won't do in this case. We need to build it from source, because otherwise an option that we need is not enabled. For Linux systems, run the following commands in a temporary directory:

~~~~
$> git clone git@github.com:Rudde/mktorrent.git
$> cd mktorrent
$> make && sudo make install
~~~~

If you are on a seedbox and you lack the privileges to install packages, you are best off contacting your seedbox provider and asking them to install the listed packages.

### Configuration
Run `redcamp` by running the script included when you cloned the repository:

    $> ./redcamp.py

You will receive a notification stating that you should edit the configuration file located at:

    ~/.redcamp/config

Open this file in your preferred text editor, and configure as desired. The options are as follows:
* `username`: Your redacted.ch username.
* `password`: Your redacted.ch password.
* `session_cookie`: Your redacted.ch session_cookie (optional).
* `data_dir`: The directory where your torrent downloads are stored.
* `output_dir`: The directory where the releases will be downloaded to.
* `torrent_dir`: The directory where the generated `.torrent` files are stored.

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

When you run the script it will ask for you the number of releases to download, I recommend no more than 50 at a time. It will scrape the release URL and the download link (FLAC) and save them to `releases.txt`.
This script needs to be run on a machine with Firefox and a desktop environment. If you're running this on a seedbox you can use VNC or x2go. Tested on Windows and Linux.

To download the releases in `releases.txt` and upload them:

    $> ./redcamp.py --download-releases

To process and upload the releases in `output_dir`:

    $> ./redcamp.py

If your releases are downloaded automatically REDCamp caches the URLs for later use, otherwise it will attempt to search Bandcamp for the album. Releases from Bandcamp follow the format "\<artist> - \<album>.zip".
Releases are tagged using metadata from Bandcamp and MusicBrainz. If information is missing it will prompt the user to enter it manually. The script also checks if a release is a duplicate on Redacted and skips it.

## Bugs and Feature Requests

If you have any issues using the script, or would like to suggest a feature, feel free to open an issue in the issue tracker, *provided that you have searched for similar issues already*. Pull requests are also welcome.

## Credits
* [Mechazawa](https://github.com/Mechazawa) for [REDBetter](https://github.com/Mechazawa/REDBetter-crawler)
* [AnstrommFeck](https://redacted.ch/user.php?id=7191) for [mkspectrograms.sh](https://redacted.ch/forums.php?action=viewthread&threadid=42695)
* [Lossless Audio Checker](http://losslessaudiochecker.com/)