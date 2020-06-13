import re
import os
import unicodedata

from zipfile import ZipFile

def read_file(path):
    if not os.path.exists(path):
        return ""
    with open(path, 'r') as file:
        data = file.read()
        file.close()
    return data

def write_file(path, data):
    with open(path, 'w') as file:
        file.write(data)
        file.close()

def clean(value):
    value = re.sub(r'[\|\/]', '-', value)
    value = re.sub(r'[<>:"\\|?*]', '', value).strip()
    return value

def slugify(value):
    value = unicodedata.normalize('NFKD', value).encode('ascii', 'ignore').decode('ascii')
    value = re.sub(r'[^\w\s-]', '', value).strip()
    return value

def unzip_file(file, dir):
        dir += "/" + os.path.basename(file).rstrip(".zip")
        with ZipFile(file, 'r') as zf:
            zf.extractall(dir)
        return dir