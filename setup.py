from setuptools import setup

with open('README.md', 'r') as file:
    long_description = file.read()

requirements = [
    'pyyaml',
    'numpy',
    'google-cloud-speech', # google
    'pocketsphinx', # cmusphinx
    'azure-cognitiveservices-speech', # azure
    'boto3', # amazon
]

dev_requirements = [
    'gensim', # Develop/evaluate.py
    'nltk', # Develop/evaluate.py
    'scipy', # Develop/evaluate.py
    'pdftotext' # Develop/parse_pdf.py
]

package_data = {
    'stt' : ['config.yaml'],
    'Demo' : ['demo_clip.wav', 'demo_credentials/*']
}

# install stt package
setup(
    name='vhh_stt',
    version='0.1.0',
    author='Thomas Heitzinger',
    author_email='thomas.heitzinger@tuwien.ac.at',
    description='Speech-to-Text Package',
    long_description=long_description,
    long_description_content_type='text/markdown',
    #url='https://github.com/dahe-cvl/vhh_sbd',
    install_requires=requirements,
    extras_require={'dev' : dev_requirements},
    package_data=package_data,
    packages=['stt', 'Demo', 'Develop']
)
