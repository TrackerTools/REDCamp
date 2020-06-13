#Install Python Modules
pip install -r requirements.txt

#Install SoX
sudo apt install sox

#Install Lossless Audio Checker
wget --content-disposition "http://losslessaudiochecker.com/dl/LAC-Linux-64bit.tar.gz"
tar xzvf LAC-Linux-64bit.tar.gz
rm LAC-Linux-64bit.tar.gz

#Install mkspectrograms.sh
curl "https://pastebin.com/raw/PUbAMsaB" -o mkspectrograms.sh
chmod +x mkspectrograms.sh