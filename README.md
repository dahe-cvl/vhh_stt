# Speech-to-Text

This package implements Speech-to-Text transcription functionality that interfaces with a series of transcription APIs.

## Installation

Make sure that `ffmpeg` is installed on the device, it is essential for the main transcription class.

Download the archive `dist/vhh_stt-<version>.tar.gz` and extract it to the desired package directory. To build the binary yourself from source, use `python setup.py sdist bdist_wheel` (make sure the `wheel` package is installed). The binary can be found in the `dist` folder.
For basic transcription functionality navigate to the package or `dist` directory and type `pip install .` or `pip install xxx.whl` to install.
If optional dependencies for scripts in the `Develop` directory should be install as well instead type `pip install .[dev]`.

Additionally, install the `pocketsphinx` python package. As this needs SWIG installed on your system (unless a pre-built binary is used), this must be done manually and is therefore not included in the requirements textfile.

If you intend to use the services Google Cloud Speed-to-Text, Azure Speech-to-Text or Amazon Transcribe make sure that `config.yaml` contains the correct path to the appropriate credentials file - see section *Service authentication and configuration* below.
If CMU Sphinx is used then the model files for the intended language must be provided - see section *CMU Sphinx models*.  

## Usage

The main file for transcription is `vhh_stt/transcribe.py` with its class `AudioTranscriber`. See `Demo/transcribe_demo.py` for sample code.

**Class Signature:**

`class AudioTranscriber(file_paths, language_code, working_dir=None, resume=None, **kwargs)`

Parameters:
* `file_paths ([str])` : A list of paths to audio or video files that should be transcribed.
* `language_code (str)` : The spoken language (e.g. "en-US").
* `working_dir (str, optional)` : The directory where results and temporary files are saved. If no argument is given then `working_dir` is set to `vhh_stt/working_dir`.
* `resume (bool, optional)` : Since transcription may take many hours the `AudioTranscriber` class is designed to be able to resume a transcription job if it is interrupted. If a `working_dir` argument is given then the default behaviour is `resume=True`, and `resume=False` otherwise.
* `kwargs (dict, optional)` : Any setting in `config.yaml` can be overwritten here.

**Methods:**

`AudioTranscriber.transcribe(n_clips=None)` : Start (or resume) a transcription job. 

Parameters:
* `n_clips (int, optional)` : If only a partial transcription is required then `n_clips` sets the number of clips to be processed.

Returns:
* `text (str)` : The transcribed text.

## Configuration

The main configuration file is `config.yaml`.

#### Parameters in the configuration file parameters:

**Transcription:**
* `service (str)` : The service to use for transcription. Possible values are "google", "azure", "amazon" and "sphinx".
* `enable_punctuation (bool)` : Request punctuated transcription.

**Audio:**

During initialization the audio component of all source files is converted to `.wav` files (temporarily stored at `<working_dir>/tmp/`. 
These files are first concatenated and then trimmed (see below). 
The result is a single source file that is stored at `<working_dir>/source.wav` and cut into clips during transcription.
Each API call to a transcription service is made on a single clip.
* `source_start_trim (int)` : Number of seconds to trim from the beginning of the source file.
* `source_end_trim (int)` : Number of seconds to trim from the end of the source file.
* `clip_length (int)` : Length of a clip in seconds.
* `clip_overlap (int)` : Number of seconds that clips overlap (to avoid words being cut in half or errors due to lacking context).

**Storage:**
* `store_clips (bool)` : Save the audio clip of each transcription request.
* `store_responses (bool)` : Save the raw responses returned by the transcription services. 
* `store_untrimmed_text (bool)` : Save the transcribed text before overlap due to `clip_overlap` has been removed.

**Service authentication and configuration:**

The `services` entry collects configuration parameters for individual transcription services.
* `services.google.credentials (str)` : Path to `.json` credentials file that contains the service account key.
* `services.azure.credentials (str)` : Path to  `.yaml` file containing the keys `key` and `region` with an Azure subscription key and region as values.
* `services.amazon.credentials (str)` : Path to `.ini` file containing AWS credentials. This file should also contain a line that specifies the AWS region (e.g. "region=us-east-1").
* `services.amazon.region (str)` : The AWS region.

See `Demo/demo_credentials` for the required content of credential files.

#### CMU Sphinx Models:

Models for CMU Sphinx are expected to be located at `vhh_stt/sphinx_models`.
For each language a subfolder `vhh_stt/sphinx_models/<language_code>/` must be created that contains:
* `<language_code> (directory path)` : Directory containing Hidden Markov Model files.
* `<language_code>.dict (file path)` : A dictionary file. 
* `<language_code>.lm.bin (file path)` : A language model.

Download links for models that have been collected by CMU Sphinx developers can be found [here](https://cmusphinx.github.io/wiki/download/).
