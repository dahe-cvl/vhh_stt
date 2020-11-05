import os
import sys
sys.path.append('..')

from stt.transcribe import AudioTranscriber

file_paths = ['demo_clip.wav']
language_code = 'en-US'
working_dir = 'tmp'

# initialize transcription class
# kwargs are needed since by default start and end of the file are trimmed by 15min, but demo clip is only 50s long
transcriber = AudioTranscriber(file_paths, language_code, working_dir, source_start_trim=0, source_end_trim=0)
text = transcriber.transcribe()
print(text)