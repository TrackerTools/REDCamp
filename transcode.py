import re
import os
import shutil
import subprocess
import mutagen.flac

import ptpimg_uploader

def ext_matcher(*extensions):
    '''
    Returns a function which checks if a filename has one of the specified extensions.
    '''
    return lambda f: os.path.splitext(f)[-1].lower() in extensions

def locate(root, match_function, ignore_dotfiles=True):
    '''
    Yields all filenames within the root directory for which match_function returns True.
    '''
    for path, dirs, files in os.walk(root):
        for filename in (os.path.abspath(os.path.join(path, filename)) for filename in sorted(files) if match_function(filename)):
            if ignore_dotfiles and os.path.basename(filename).startswith('.'):
                pass
            else:
                yield filename

def is_24bit(flac_dir):
    '''
    Returns True if any FLAC within flac_dir is 24 bit.
    '''
    flacs = (mutagen.flac.FLAC(flac_file) for flac_file in locate(flac_dir, ext_matcher('.flac')))
    return any(flac.info.bits_per_sample > 16 for flac in flacs)

def make_torrent(torrent, input_dir, tracker, passkey, piece_length):
    if not os.path.exists(os.path.dirname(torrent)):
        os.makedirs(os.path.dirname(torrent))
    tracker_url = '%(tracker)s%(passkey)s/announce' % {
        'tracker' : tracker,
        'passkey' : passkey,
    }
    command = ["mktorrent", "-s", "RED", "-p", "-a", tracker_url, "-o", torrent, "-l", piece_length, input_dir]
    subprocess.check_output(command, stderr=subprocess.STDOUT)
    return torrent

def is_lossless(flac_dir):
    flac_file = next(locate(flac_dir, ext_matcher('.flac')))
    wav_file = os.path.splitext(flac_file)[0] + ".wav"
    subprocess.call(["ffmpeg", "-i", flac_file, wav_file], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    output = subprocess.check_output(["./LAC", wav_file]).decode()
    result = re.search(r'Result: (\w+)', output).group(1)
    os.remove(wav_file)
    return result

def make_spectrograms(flac_dir, api_key):
    api = ptpimg_uploader.PtpimgUploader(api_key)
    flac_file = next(locate(flac_dir, ext_matcher('.flac')))
    subprocess.call(["./mkspectrograms.sh", flac_file], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    spectral_dir = os.path.join(flac_dir, "Spectrograms")
    spectrals = locate(spectral_dir, ext_matcher('.png'))
    links = api.upload_files(*spectrals)
    shutil.rmtree(spectral_dir)
    return links