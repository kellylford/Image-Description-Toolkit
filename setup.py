#!/usr/bin/env python3
"""
Setup script for image-description-toolkit.
"""

from setuptools import setup, find_packages

# Read requirements.txt 
def read_requirements():
    with open('requirements.txt', 'r') as f:
        return [line.strip() for line in f if line.strip() and not line.startswith('#')]

setup(
    name="image-description-toolkit",
    version="0.1.0",
    author="kellylford",
    description="Experimental tools for image description interaction.",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/kellylford/Image-Description-Toolkit",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers", 
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
    python_requires=">=3.8",
    install_requires=read_requirements(),
    entry_points={
        "console_scripts": [
            "image-description-toolkit=image_description_toolkit.workflow:main",
        ],
    },
    include_package_data=True,
    package_data={
        "image_description_toolkit": ["*.json"],
    },
)