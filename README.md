qooxdoo-sublime
===============

A qooxdoo package for Sublime Text 2

Autocompletion
--------------
Suggests classes and static methods from any qooxdoo library including the framework itself.

Configuration
_____________
Run ``generate.py api-data`` for any qooxdoo library you wish to use in your project. If you're using a qooxdoo SDK you can skip this step since it comes with pre-built API data. Note the directory created by the job: By default, this will be ``<library_dir>/api/script>``.

Next, open the ``qooxdoo.sublime-settings`` configuration file and locate the ``autocomplete_api_paths`` key. The value is an array of API data directories. Enter the script directories gained in the prevous script here and restart Sublime Text.
