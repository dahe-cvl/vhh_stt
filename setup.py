from setuptools import setup

with open('README.md', 'r') as file:
    long_description = file.read()

# read requirements
install_requires=[]
with open("requirements.txt", "r") as f:
    reqs = f.readlines()
    for i in range(len(reqs)):
        req = reqs[i]
        if i < len(reqs)-1:
            req = req[:-1]
        if req[0] is not '#':
            install_requires.append(req)

dev_requirements = [
    'gensim', # Develop/evaluate.py
    'nltk', # Develop/evaluate.py
    'scipy', # Develop/evaluate.py
    'pdftotext' # Develop/parse_pdf.py
]

package_data = {
    'config' : ['config.yaml'],
    'Demo' : ['demo_clip.wav']
}

# install stt package
setup(
    name='vhh_stt',
    version='1.0.0',
    author='Thomas Heitzinger',
    author_email='thomas.heitzinger@tuwien.ac.at',
    description='Speech-to-Text Package',
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='https://github.com/dahe-cvl/vhh_stt',
    install_requires=install_requires,
    extras_require={'dev' : dev_requirements},
    package_data=package_data,
    packages=['vhh_stt', 'config', 'credentials', 'Demo', 'Develop']
)
