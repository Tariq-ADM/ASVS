# Written by Tariq A.
#Repository ---> github.com/tariq-chameleon/ASVS.git
# Thanks to https://www.rototron.info for inspiring me to use the numpy FFT
# https://www.wavtones.com/functiongenerator.php allowed me to generate audio signals
# https://www.audiocheck.net/audiofrequencysignalgenerator_sweep.php allowed me to generate audio signals
# http://www.orangefreesounds.com   allowed to test lounge music and melodic upbeats
# Additional wav files were found online and are put in Documentation/Impl.../Med../

# Main purpose is visualizing the Human Audio Spectrum ~16 Hz - ~16 kHz
# .wav files are read directly. .mp3 files are decoded to 16-bit PCM first
# (pip install miniaudio) and then follow the same block/FFT path.


#from multiprocessing import PROCESS
try:
    import alsaaudio as ALSA          # only used by the commented-out playback path
except ImportError:
    ALSA = None
import wave as WAVE
from struct import unpack
import numpy as NP
import os as OS
import sys as SYS
import io
from cli_visualizer import cli_visualize as CLIV
from time import sleep


#-------------------------------------------------------------------------
# VARs
SLP_DURA = 2            # 3 secs delay before starting
FREQ_DOMAIN = [0,0,0,0,0,0,0,0,0,0]
weighting = [2,2,8,8,16,16,32,32,64,64]

FREQ_LVL_CUR_THRES=[15,12,0,0,0,0,0,0,0,0]     #Thresholding frequency levels in Real-time

FREQ_DOMAIN_CEILING = 20           #Domain roof. FYI: floor is at 0
FREQ_DOMAIN_NUM_RANGES = 10
BLOCKS = 4096    #2^x
SAMPLING_RATE = 0
NUM_CH = 0
AMP= []
# End of #VARs
#-------------------------------------------------------------------------


#-------------------------------------------------------------------------
def open_audio(path):
   """Open a .wav file, or decode a .mp3 into an in-memory 16-bit WAV."""
   ext = OS.path.splitext(path)[1].lower()
   if ext == '.mp3':
      return open_mp3(path)
   if ext in ('.wav', '.wave'):
      return WAVE.open(path, 'rb')
   SYS.exit("Unsupported file type '%s'. Use a .wav or .mp3 file." % ext)


def open_mp3(path):
   """Decode an MP3 to interleaved 16-bit PCM and hand it to the wave reader.

   The whole file is decoded up front so the visualizer can keep reading
   fixed-size blocks the same way it does for WAV.
   """
   try:
      import miniaudio
   except ImportError:
      SYS.exit("Reading MP3 files needs the miniaudio package.\n"
               "Install it with: pip install miniaudio")
   try:
      decoded = miniaudio.mp3_read_file_s16(path)
   except miniaudio.DecodeError as exc:
      SYS.exit("Could not decode MP3 '%s': %s" % (path, exc))

   print("Decoded MP3 to 16-bit PCM: %d ch, %d Hz, %.2f s" % (
      decoded.nchannels, decoded.sample_rate, decoded.duration))
   buf = io.BytesIO()
   with WAVE.open(buf, 'wb') as out:
      out.setnchannels(decoded.nchannels)
      out.setsampwidth(2)
      out.setframerate(decoded.sample_rate)
      out.writeframes(decoded.samples.tobytes())
   buf.seek(0)
   # Wave_read keeps this buffer alive for the rest of the run.
   return WAVE.open(buf, 'rb')
#-------------------------------------------------------------------------


#-------------------------------------------------------------------------
# Return AMP array index corresponding to a particular frequency
def piff(arG):
   return int(2*BLOCKS*arG/SAMPLING_RATE) #arG = 1 --> (2*4096*1)/22050

def band_level(amp, start_hz, end_hz):
   """Mean magnitude of one frequency window.

   A short final block, or a band above Nyquist, used to make np.mean()
   hit an empty slice and raise ValueError. Those bands report 0.
   """
   start = piff(start_hz)
   end = piff(end_hz)
   if start < 0:
      start = 0
   if end > len(amp):
      end = len(amp)
   if end <= start:
      return 0
   return int(NP.mean(amp[start:end]))

def GET_LVLs(data, BLOCKS,SAMPLING_RATE):
   global FREQ_DOMAIN

   # Convert raw 16-bit little-endian frames to a numpy array.
   # Drop a trailing odd byte so unpack does not raise on a short block.
   usable = len(data) - (len(data) % 2)
   if usable < 2:
      return NP.zeros(FREQ_DOMAIN_NUM_RANGES, dtype=int)
   data = unpack("%dh" % (usable // 2), data[:usable])
   data = NP.array(data, dtype='h')

   # Apply FFT - real data
   FFT=NP.fft.rfft(data)
   # Remove last element in array to make it the same size as BLOCKS
   FFT=NP.delete(FFT,len(FFT)-1)



   # Find average 'amplitude' for specific frequency ranges in Hz
   AMP = NP.abs(FFT)   #absolute

   FREQ_DOMAIN[0]= band_level(AMP, 0, 30)                              # 0
   FREQ_DOMAIN[1]= band_level(AMP, 35, 100)                            #
   FREQ_DOMAIN[2]= band_level(AMP, 150, 300)                           #
   FREQ_DOMAIN[3]= band_level(AMP, 320, 500)                           #
   FREQ_DOMAIN[4]= band_level(AMP, 600, 1000)                          # 1
   FREQ_DOMAIN[5]= band_level(AMP, 1100, 2500)
   FREQ_DOMAIN[6]= band_level(AMP, 3000, 5000)
   FREQ_DOMAIN[7]= band_level(AMP, 5000, 7000)
   FREQ_DOMAIN[8]= band_level(AMP, 7100, 10000)
   FREQ_DOMAIN[9]= band_level(AMP, 10100, 16000)


   # Tidy up column values
   FREQ_DOMAIN=NP.divide(NP.multiply(FREQ_DOMAIN,weighting),1000000)
   # Set floor at 0 and ceiling at 20
   FREQ_DOMAIN=(FREQ_DOMAIN.clip(00,FREQ_DOMAIN_CEILING))
   FREQ_DOMAIN = FREQ_DOMAIN.astype(int)        #convert Domain to int, floats is not interesting atm

   return FREQ_DOMAIN
#-------------------------------------------------------------------------


def main():
   global SAMPLING_RATE, NUM_CH, BLOCKS

   if len(SYS.argv) < 2:
      SYS.exit("Usage: python3 play.py AUDIO_FILE.wav|AUDIO_FILE.mp3")

   WAVFILE = str(SYS.argv[1])
   print("\nMain purpose is visualizing the Human Audio Spectrum ~16 Hz - ~16 kHz")
   print("\n")
   print("Input file: " + WAVFILE)

   if not OS.path.isfile(WAVFILE):
      SYS.exit("File not found: " + WAVFILE)

   #-------------------------------------------------------------------------
   # WAVSAMPLE
   # Audio setup. MP3 is decoded to 16-bit PCM before this point.
   WAVSAMPLE = open_audio(WAVFILE)
   SAMPLING_RATE = WAVSAMPLE.getframerate()
   NUM_CH = WAVSAMPLE.getnchannels()

   print ("Blocks at a time: " + str(BLOCKS))
   print("The number of channels: "+ str(NUM_CH))
   print("The sampling rate: " + str(SAMPLING_RATE) + " Hz")
   print("\n")
   # End of #WAVSAMPLE
   #-------------------------------------------------------------------------

   #-------------------------------------------------------------------------
   # ALSA (Enable to output audio)
   # ALSA_OUT = ALSA.PCM(ALSA.PCM_PLAYBACK, ALSA.PCM_NORMAL)
   # ALSA_OUT.setchannels(NUM_CH)
   # ALSA_OUT.setrate(SAMPLING_RATE)
   # ALSA_OUT.setformat(ALSA.PCM_FORMAT_S16_LE)
   # ALSA_OUT.setperiodsize(BLOCKS)
   # End of #ALSA
   #-------------------------------------------------------------------------

   #-------------------------------------------------------------------------
   # Read audio sample
   data = WAVSAMPLE.readframes(BLOCKS)

   try:
      print("Initializing main loop (Exit with Ctrl + C)......")
      sleep(SLP_DURA)

      # Main loop (Exit with Ctrl + C)
      while data:
         # ALSA (Enable to output audio)
         # ALSA_OUT.write(data)                                 # Output the original file


         FREQ_DOMAIN=GET_LVLs(data, BLOCKS,SAMPLING_RATE)     # Calculate FFT of the current data-block
         CLIV(FREQ_DOMAIN)                                    # Visualize the current Frequency Domain on CLI


         CMD = 'echo -en %d,%d,%d,%d,%d,%d,%d,%d,%d,%d > socket' %(FREQ_DOMAIN[0],FREQ_DOMAIN[1],FREQ_DOMAIN[2],FREQ_DOMAIN[3],FREQ_DOMAIN[4],FREQ_DOMAIN[5],FREQ_DOMAIN[6],FREQ_DOMAIN[7],FREQ_DOMAIN[8],FREQ_DOMAIN[9])
         #print(SocketBuffer)
         OS.system(CMD)
         # if FREQ_DOMAIN[1] >= FREQ_LVL_CUR_THRES[1]:          # Thresholding
         #   if __name__ == '__main__':
         #       VIZEProc = PROCESS(target=VIZE, args=(18,))  # Send signal to GPIO
         #       VIZEProc.start()

         data = WAVSAMPLE.readframes(BLOCKS)                  # Read the next data-block
   except KeyboardInterrupt:
      pass
   finally:
      WAVSAMPLE.close()
   #-------------------------------------------------------------------------


if __name__ == '__main__':
   main()
