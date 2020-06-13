#Install Python Modules
pip install -r requirements.txt

#Install Packages
sudo apt install ffmpeg sox

#Install mktorrent
if ! command -v mktorrent > /dev/null; then
    git clone git@github.com:Rudde/mktorrent.git
    cd mktorrent
    make && sudo make install
fi

#Install Lossless Audio Checker
wget --content-disposition "http://losslessaudiochecker.com/dl/LAC-Linux-64bit.tar.gz"
tar xzvf LAC-Linux-64bit.tar.gz
rm LAC-Linux-64bit.tar.gz

chmod +x redcamp.py
chmod +x mkspectrograms.sh