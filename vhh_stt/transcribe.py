import os
import re
import json
import yaml
import time
import subprocess
import pickle
import shutil

from vhh_stt.transcribe_services import Google_STT_Service, Sphinx_STT_Service, Azure_STT_Service, Amazon_STT_Service

class AudioTranscriber:
	def __init__(self, file_paths, language_code, working_dir=None, resume=None, **kwargs):
		custom_working_dir = working_dir is not None
		if working_dir is None:
			working_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'working_dir')

		script_path = os.path.dirname(os.path.abspath(__file__))
		file_paths = [os.path.abspath(path) for path in file_paths]

		# get config
		self.cfg = yaml.safe_load(open(os.path.join(script_path, '..', 'config', 'config.yaml')))
		self.cfg.update(kwargs)

		# switch to working directory
		self.working_dir = os.path.abspath(working_dir)
		if not os.path.exists(self.working_dir):
			os.makedirs(self.working_dir)
		previous_directory = os.getcwd()
		os.chdir(self.working_dir)

		# load state
		if resume is None:
			# if resume argument is not given then only resume if a custom working directory was given
			resume = custom_working_dir
		if not resume:
			self.clear_working_dir()

		self.state = self.load_state(file_paths, language_code)
		self.next_state = None

		# load transcription service
		os.chdir(script_path)
		services = {
			'google' : Google_STT_Service,
			'sphinx' : Sphinx_STT_Service,
			'azure' : Azure_STT_Service,
			'amazon' : Amazon_STT_Service,
		}
		self.service = services[self.cfg['service']](
			self.state['language_code'],
			self.cfg['enable_punctuation'],
			self.cfg['services'][self.cfg['service']]
		)
		os.chdir(previous_directory)

	def load_state(self, file_paths, language_code):
		state_path = 'state.json'
		if not os.path.exists(state_path):
			self.prepare_source_file(file_paths)
			state = {
				'language_code' : language_code,
				'clip_number' : 0,
				'current_time' : 0,
				'last_sound_time' : 0,
				'finished' : False
			}
			json.dump(state, open(state_path, 'w'))
		else:
			state = json.load(open(state_path))
		return state

	def save_state(self, state):
		self.state = state
		json.dump(state, open('state.json', 'w'))

	def clear_working_dir(self):
		if os.path.exists('state.json'):
			os.remove('state.json')

	def execute_command(self, command, popen=False):
		try:
			if popen:
				process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
				out, _ = process.communicate()
				return out
			else:
				subprocess.call(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
		except Exception as exception:
			print(str(exception))

	def prepare_source_file(self, file_paths):
		tmp_directory = 'tmp'
		if not os.path.exists(tmp_directory):
			os.makedirs(tmp_directory)

		# temporarily convert all files to wav before combining and trimming them
		# set 16k sample rate and single channel
		for i, file_path in enumerate(file_paths):
			if not os.path.exists(file_path):
				raise FileNotFoundError(file_path)
			# -i in_file
			# -ac # of channels
			# -ar sampling frequency
			# -vn no video
			# -y override without asking
			command = 'ffmpeg -y -i "%s" -vn -acodec pcm_s16le -ac 1 -ar 16000 %s/source%d.wav' \
					  % (file_path, tmp_directory, i)
			self.execute_command(command)

		# create file list for concatenate operation
		list_path = os.path.join(tmp_directory, 'files.txt')
		lines = ['file source%d.wav' % i for i in range(len(file_paths))]
		print('\n'.join(lines), file=open(list_path, 'w'))

		# concatenate files
		full_source_path = os.path.join(tmp_directory, 'full_source.wav')
		command = 'ffmpeg -y -f concat -i %s -c copy %s' % (list_path, full_source_path)
		self.execute_command(command)

		# trim start and end
		def format(seconds):
			return time.strftime('%H:%M:%S', time.gmtime(seconds))

		source_trim = (self.cfg['source_start_trim'], self.cfg['source_end_trim'])
		full_file_duration = self.file_duration(full_source_path)
		if full_file_duration <= source_trim[0] + source_trim[1]:
			raise IOError('%s: file duration is too short for parameters (source_start_trim, source_end_trim) = %r' %
						  (full_source_path, source_trim))

		source_path = 'source.wav'
		file_duration = full_file_duration - source_trim[0] - source_trim[1]
		command = 'ffmpeg -y -i %s -ss %s -t %s %s' \
				  % (full_source_path, format(source_trim[0]), format(file_duration), source_path)
		self.execute_command(command)

		# delete temporary directory
		shutil.rmtree(tmp_directory)

	def file_duration(self, path):
		command = 'ffprobe -show_format "%s"' % path
		out = self.execute_command(command, popen=True)
		duration = re.search(r'duration=([0-9]*\.?[0-9]+)', out.decode('utf-8')).group(1)
		return float(duration)

	def generate_clip(self, clip_path):
		def format(seconds):
			return time.strftime('%H:%M:%S', time.gmtime(seconds))

		# get clip from source
		command = 'ffmpeg -y -i %s -ss %s -t %s %s' \
				  % ('source.wav', format(self.next_state['current_time']), format(self.cfg['clip_length']), clip_path)
		self.execute_command(command)

	def next_clip(self):
		file_duration = self.file_duration('source.wav')
		if self.state['current_time'] >= file_duration:
			return None

		clip_path = 'clip%d.wav' % self.state['clip_number']
		self.generate_clip(clip_path)

		self.next_state['current_time'] += self.cfg['clip_length'] - self.cfg['clip_overlap']
		self.next_state['clip_number'] += 1
		return clip_path

	def trim_response(self, words):
		if not words:
			return '', ''

		# add time offset for clip
		time_offset = self.state['current_time'] * 1000
		words = [(word[0], word[1] + time_offset, word[2] + time_offset) for word in words]

		try:
			# first index where time starts later than ending of last word of previous clips
			splice_start = next(i for i, word in enumerate(words) if word[1] >= self.state['last_sound_time'])
			trimmed_words = words[splice_start:]
		except:
			trimmed_words = words

		# new time of last sound is stored in state
		self.next_state['last_sound_time'] = words[-1][2]

		text = ' '.join([word[0] for word in trimmed_words])
		untrimmed_text = ' '.join([word[0] for word in words])

		return text, untrimmed_text

	def transcribe_clip(self):
		self.next_state = self.state.copy()
		clip_path = self.next_clip()
		if clip_path is None:
			# done with processing
			self.next_state['finished'] = True
		else:
			words, response = self.service.recognize(clip_path)
			text, untrimmed_text = self.trim_response(words)

			print(text, end=' ', file=open('transcribed_text.txt', 'a+'))
			if self.cfg['store_untrimmed_text']:
				print(untrimmed_text, file=open('transcribed_text_untrimmed.txt', 'a+'))

			if not self.cfg['store_clips']:
				os.remove(clip_path)

			if self.cfg['store_responses']:
				response_path = 'response%d.p' % self.state['clip_number']
				pickle.dump({
					'time_offset': self.state['current_time'],
					'response': response
				}, open(response_path, 'wb'))

		self.save_state(self.next_state)
		return self.next_state['finished']

	def transcribe(self, n_clips=None):
		previous_directory = os.getcwd()
		os.chdir(self.working_dir)
		while True:
			if self.state['finished']:
				break

			if n_clips is not None and self.state['clip_number'] >= n_clips:
				break

			finished = self.transcribe_clip()
			if finished:
				os.remove('source.wav')
				break

		with open('transcribed_text.txt', 'r') as file:
			os.chdir(previous_directory)
			return file.read()
