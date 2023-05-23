from setuptools import setup, find_packages

setup(
    name='toorpia_utils',
    version='0.1.0',
    description='utilities for toorpia',
    author='toor Inc.',
    author_email='toorpia@toor.jpn.com',
    url='https://github.com/toorpia/utils',
    packages=find_packages(),
    install_requires=[
        'numpy',
    ],
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
    ],
)
