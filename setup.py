from setuptools import setup, find_packages


def readme():
  with open('README.md', 'r') as f:
    return f.read()


setup(
  name='mapyr',
  version='0.8.1',
  author='AIG',
  author_email='aig.livny@gmail.com',
  description='Small build system',
  long_description=readme(),
  long_description_content_type='text/markdown',
  url='https://github.com/AIG-Livny/mapyr',
  packages=find_packages(),
  install_requires=[],
  classifiers=[
    'Programming Language :: Python :: 3.11',
    'License :: OSI Approved :: MIT License',
    'Operating System :: OS Independent'
  ],
  keywords='mapyr build makefile c++',
  project_urls={
    'GitHub': 'https://github.com/AIG-Livny/mapyr'
  },
  python_requires='>=3.6'
)
