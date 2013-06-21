qooxdoo-sublime
===============

A qooxdoo package for Sublime Text 2

Autocompletion
--------------
Suggests classes and static methods from any qooxdoo library including the framework itself.

Configuration
_____________

Run ``generate.py api-data`` for any qooxdoo library you wish to use in your project. If you're using a qooxdoo SDK (as opposed to a clone of the Git repository) you can skip this step for the framework since it comes with pre-built API data.

Next, open the ``qooxdoo.sublime-settings`` configuration file and locate the ``libraries`` key. The value is a map where each key is an identifier for a qooxdoo library. These names are arbitrary except for the qooxdoo framework, which must always be named ``qooxdoo``. The corresponding value is the file system path of the library's root directory (i.e. the folder containing the "Manifest.json" file). Enter the information for all libraries you wish to include.

Finally, restart Sublime Text. This forces qooxdoo-sublime to re-scan the configured libraries. You should now see suggestions for matching class names as you type.

Default Behavior
________________

If no libraries are configured in the qooxdoo-sublime's settings, it will automatically search all folders in the current Sublime project for API data to be included in the list of autocomplete suggestions. This can take a while and will not work for libraries where ``Manifest.json`` is located in a subdirectory of the folder, so it is preferable to explicitly configure the libraries as described above.
