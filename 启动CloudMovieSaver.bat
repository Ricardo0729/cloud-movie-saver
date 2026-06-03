@echo off
title CloudMovieSaver
cd /d "%~dp0"
start pythonw -m cloud_movie_saver.main gui
exit
