from setuptools import setup, find_packages
setup(
name='multiprocessed-socket',
version='0.1.0',
author='Jackson Frame',
author_email='frame_jackson@yahoo.com',
description='Creates a socket in a new process',
packages=find_packages(),
classifiers=[
'Programming Language :: Python :: 3',
'License :: OSI Approved :: MIT License',
'Operating System :: OS Independent',
],
install_requires=["netifaces"],
python_requires='>=3.6',
)