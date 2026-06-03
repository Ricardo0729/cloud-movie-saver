#!/usr/bin/env python3
"""CloudMovieSaver - 云盘电影资源搜索保存工具"""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

with open("requirements.txt", "r", encoding="utf-8") as fh:
    requirements = [line.strip() for line in fh if line.strip() and not line.startswith("#")]

setup(
    name="cloud-movie-saver",
    version="1.0.0",
    author="Ricardo0729",
    author_email="124856482+Ricardo0729@users.noreply.github.com",
    description="云盘电影资源搜索保存工具 - 搜索电影并自动保存到百度云盘/夸克网盘/迅雷云盘，按类别自动整理",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/Ricardo0729/cloud-movie-saver",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Environment :: Console",
        "Intended Audience :: End Users/Desktop",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Multimedia :: Video",
        "Topic :: Internet :: WWW/HTTP :: Indexing/Search",
    ],
    python_requires=">=3.8",
    install_requires=requirements,
    entry_points={
        "console_scripts": [
            "cloud-movie-saver=cloud_movie_saver.main:main",
            "cms=cloud_movie_saver.main:main",
        ],
    },
    include_package_data=True,
    project_urls={
        "Bug Reports": "https://github.com/Ricardo0729/cloud-movie-saver/issues",
        "Source": "https://github.com/Ricardo0729/cloud-movie-saver",
    },
)
