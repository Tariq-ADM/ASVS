ASVS (Audio Spectrum Visualising System)



Required packages (possibly some are not mentioned)
-python 3
-python2-tools
-python alsaaudio
-python wave
-python struct
-python numpy
-miniaudio   (only for .mp3: pip install miniaudio)
-python setuptools
-alsa-lib
-alsa-tools
-alsa-utils
-ffmpeg
-gcc
-make
-scons
-swig
-Python RPIO



Source code found in Documentation/Source/play.py
Sample wav files are found in Documentation/Implementation/Media/


Current Usage:

$ python3 play.py    AUDIO_FILE_PATH_HERE

- .wav files are visualized as before.
- .mp3 files are decoded to 16-bit PCM with miniaudio, then use the same FFT path.
  Install the decoder with: pip install miniaudio
- Also due to UI inexperience, the CLI window will be to be adjusted to the size of the
data being printed to avoid bad looking new prints (due to new-line each iteration)
there connecting remotely (i.e. ssh) is recommended.

- python3 is required. The pyalsaaudio import is optional because playback is commented out.


