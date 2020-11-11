import os
import sys
sys.path.append('..')

from vhh_stt.transcribe import AudioTranscriber
from audio_paths import paths

identifier = 'OH_ZP1_259'
service = 'amazon'
data = paths[identifier]

file_paths = [os.path.join('../data/audio/', path) for path in data['paths']]
language_code = data['language_code']
working_dir = os.path.join('audio_transcripts', identifier + '_' + service)

transcriber = AudioTranscriber(file_paths, language_code, working_dir, service=service)
text = transcriber.transcribe()
print(text)