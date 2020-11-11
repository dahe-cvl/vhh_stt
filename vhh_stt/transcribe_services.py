import os
import re
import yaml
import json
import time
import numpy as np
from urllib.request import urlopen

class STT_Service:
	def __init__(self, language_code, enable_punctuation, cfg):
		self.language_code = language_code
		self.enable_punctuation = enable_punctuation
		self.cfg = cfg

	def recognize(self, clip_path):
		raise NotImplementedError()

from google.cloud import speech
class Google_STT_Service(STT_Service):
	def __init__(self, language_code, enable_punctuation, cfg):
		super().__init__(language_code, enable_punctuation, cfg)

		os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = self.cfg['credentials']

		# initialize client
		self.speech_client = speech.SpeechClient()
		self.speech_config = speech.RecognitionConfig(
			encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
			sample_rate_hertz=16000,
			enable_word_time_offsets=True,
			max_alternatives=30,
			language_code=self.language_code,
			enable_automatic_punctuation=self.enable_punctuation)

	def recognize(self, clip_path):
		with open(clip_path, 'rb') as audio_file:
			content = audio_file.read()

		audio = speech.RecognitionAudio(content=content)
		response = self.speech_client.recognize(self.speech_config, audio)

		# get time in milliseconds
		def format_time(time):
			return time.seconds * 10 ** 3 + time.nanos // 10 ** 6

		def format_word(word):
			return (word.word, format_time(word.start_time), format_time(word.end_time))

		# compose list of words
		words = [format_word(word) for result in response.results for word in result.alternatives[0].words]
		return words, response


from pocketsphinx import AudioFile
class Sphinx_STT_Service(STT_Service):
	def __init__(self, language_code, enable_punctuation, cfg):
		super().__init__(language_code, enable_punctuation, cfg)

		model_path = os.path.abspath(os.path.join('sphinx_models', language_code))
		self.config = {
			'verbose': False,
			'buffer_size': 2048,
			'no_search': False,
			'full_utt': False,
			'frate': 100,
			'hmm': os.path.join(model_path, language_code),
			'lm': os.path.join(model_path, language_code + '.lm.bin'),
			'dict': os.path.join(model_path, language_code + '.dict')
		}

	def recognize(self, clip_path):
		audio = AudioFile(audio_file=clip_path, **self.config)

		words = []
		for phrase in audio:
			for word in phrase.seg():
				if self.enable_punctuation and word.word == '</s>' and words:
					phrase_end = words[-1]
					# add period for last word
					words[-1] = (phrase_end[0] + '.', phrase_end[1], phrase_end[2])

				if word.word[0] in ['<', '[']:
					# dropping <s>, </s>, [SPEECH]
					continue
				# replace e.g. 'the(2)' with 'the'
				clean_word = re.sub(r'\([0-9]+\)', '', word.word)
				words.append((clean_word, word.start_frame * 10, word.end_frame * 10))

		return words, words


import azure.cognitiveservices.speech as speechsdk
class Azure_STT_Service(STT_Service):
	def __init__(self, language_code, enable_punctuation, cfg):
		super().__init__(language_code, enable_punctuation, cfg)

		credentials = yaml.safe_load(open(self.cfg['credentials']))
		speech_key, service_region = credentials['key'], credentials['region']
		self.speech_config = speechsdk.SpeechConfig(
			subscription=speech_key,
			region=service_region,
			speech_recognition_language=self.language_code
		)
		self.speech_config.request_word_level_timestamps()

	def recognize(self, clip_path):
		audio_config = speechsdk.AudioConfig(filename=clip_path)
		speech_recognizer = speechsdk.SpeechRecognizer(speech_config=self.speech_config, audio_config=audio_config)

		# collect responses
		responses = []
		def result_cb(evt):
			responses.append(json.loads(evt.result.json))

		done = False
		def stop_cb(evt):
			speech_recognizer.stop_continuous_recognition()
			nonlocal done
			done = True

		speech_recognizer.recognized.connect(result_cb)
		speech_recognizer.session_stopped.connect(stop_cb)
		speech_recognizer.canceled.connect(stop_cb)

		speech_recognizer.start_continuous_recognition()
		while not done:
			time.sleep(.5)

		# format responses into timestamped words
		def format_word(word, info):
			start_time = info['Offset'] // 10**4
			end_time = (info['Offset'] + info['Duration']) // 10**4
			if not self.enable_punctuation:
				word = info['Word']

			return word, start_time, end_time

		words = []
		for response in responses:
			if 'NBest' not in response:
				continue # sometimes 'RecognitionStatus': 'InitialSilenceTimeout' is returned without content
			best_index = np.argmax([res['Confidence'] for res in response['NBest']])
			best_response = response['NBest'][best_index]

			if 'Words' not in best_response:
				continue # sometimes no words are recognized

			words += [format_word(word, info) for word, info in
					 zip(best_response['Display'].split(), best_response['Words'])]

		return words, responses

import logging
import boto3
from botocore.exceptions import ClientError
class Amazon_STT_Service(STT_Service):
	def __init__(self, language_code, enable_punctuation, cfg):
		super().__init__(language_code, enable_punctuation, cfg)

		os.environ['AWS_SHARED_CREDENTIALS_FILE'] = os.path.abspath(cfg['credentials'])
		self.s3_client = boto3.client('s3', region_name=cfg['region'])
		self.transcribe_client = boto3.client('transcribe')
		self.region = cfg['region']

	def recognize(self, clip_path):
		bucket_name = 'vhh'
		bucket_clip_name = 'clip.wav'
		job_name = 'vhh_stt'
		job_uri = 'https://%s.s3.amazonaws.com/%s' % (bucket_name, bucket_clip_name)

		def create_bucket(bucket_name):
			try:
				response = self.s3_client.list_buckets()

				if bucket_name not in [bucket['Name'] for bucket in response['Buckets']]:
					if self.region == 'us-east-1':
						# no constraint needed if region is 'us-east-1'
						# https://docs.aws.amazon.com/AmazonS3/latest/API/API_CreateBucket.html
						self.s3_client.create_bucket(Bucket=bucket_name)
					else:
						bucket_cfg = {'LocationConstraint': self.region}
						self.s3_client.create_bucket(Bucket=bucket_name, CreateBucketConfiguration=bucket_cfg)

			except ClientError as e:
				logging.error(e)
				return False
			return True

		def upload_file(file_name, bucket, object_name='clip.wav'):
			try:
				self.s3_client.upload_file(file_name, bucket, object_name)
			except ClientError as e:
				logging.error(e)
				return False
			return True

		create_bucket(bucket_name)
		upload_file(clip_path, bucket_name, object_name=bucket_clip_name)

		try:
			# if there already is an old job delete it
			self.transcribe_client.delete_transcription_job(TranscriptionJobName=job_name)
		except:
			pass
		self.transcribe_client.start_transcription_job(
			TranscriptionJobName=job_name,
			Media={'MediaFileUri': job_uri},
			MediaFormat='wav',
			LanguageCode=self.language_code,
			Settings={
				'ShowAlternatives' : True,
				'MaxAlternatives' : 10,
			}
		)
		while True:
			status = self.transcribe_client.get_transcription_job(TranscriptionJobName=job_name)
			if status['TranscriptionJob']['TranscriptionJobStatus'] in ['COMPLETED', 'FAILED']:
				break
			time.sleep(5)

		if status['TranscriptionJob']['TranscriptionJobStatus'] == 'FAILED':
			raise RuntimeError('transcription failed with status %r' % status)

		json_string = urlopen(status['TranscriptionJob']['Transcript']['TranscriptFileUri']).read().decode('utf-8')
		data = json.loads(json_string)

		def format_word(item):
			start_time = int(float(item['start_time']) * 1000)
			end_time = int(float(item['end_time']) * 1000)

			best_index = np.argmax([float(alt['confidence']) for alt in item['alternatives']])
			word = item['alternatives'][best_index]['content']

			return word, start_time, end_time

		words = []
		for item in data['results']['items']:
			if item['type'] == 'punctuation':
				if not self.enable_punctuation:
					continue
				phrase_end = words[-1]
				# add period for last word
				words[-1] = (phrase_end[0] + item['alternatives'][0]['content'], phrase_end[1], phrase_end[2])
			else:
				words.append(format_word(item))

		return words, data
