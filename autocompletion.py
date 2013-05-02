import sublime
import sublime_plugin
import json
import urllib
import os


class QxAutoCompleteCommand(sublime_plugin.EventListener):
    def __init__(self):
        self.settings = sublime.load_settings("qooxdoo.sublime-settings")
        self.debug = self.settings.get("autocomplete_debug")

        self.apidata = self.getData()

    def getData(self):
        data = {}
        apiPaths = self.settings.get("autocomplete_api_paths")
        for lib, path in apiPaths.iteritems():
            libData = None
            cachePath = os.path.abspath("api_cache")
            indexFile = os.path.join(cachePath, "apiindex_" + lib + ".json")

            if os.path.isfile(indexFile):
                if self.debug:
                    print "Loading cached %s API data from file %s" % (lib, indexFile)
                fileObj = open(indexFile)
                libData = json.load(fileObj)
            else:
                if os.path.isfile(path):
                    if self.debug:
                        print "Collecting %s API data from file system path %s" % (lib, path)
                    libData = self.loadDataFromFile(path)
                else:
                    if self.debug:
                        print "Collecting %s API data from URL %s" % (lib, path)
                    libData = self.loadDataFromUrl(path)

                if libData:
                    if self.debug:
                        print "Writing %s API data cache to file %s" % (lib, indexFile)
                    if not os.path.isdir(cachePath):
                        os.makedirs(cachePath)
                    fileObj = open(indexFile, "w+")
                    json.dump(libData, fileObj)

            data[lib] = libData

        return data

    def loadDataFromUrl(self, url):
        indexFile = urllib.urlopen(url)
        index = indexFile.read()
        index = json.loads(index)
        data = index["__fullNames__"]

        return data

    def loadDataFromFile(self, path):
        indexFile = open(path)
        index = json.load(indexFile)
        data = index["__fullNames__"]

        return data

    def on_query_completions(self, view, prefix, locations):
        # Only trigger within JS
        if not view.match_selector(locations[0], "source.js"):
            return []

        sel = view.sel()
        region = sel[0]
        line = view.line(region)
        lineText = view.substr(line)
        lineText = lineText.strip().rsplit(" ")[-1]

        result = []
        for lib in self.apidata:
            for className in self.apidata[lib]:
                if className.startswith(lineText):
                    completion = prefix + className[len(lineText):]
                    if len(prefix) == 1 and prefix[0].isupper():
                        completion = className
                    if True or self.debug:
                        print "prefix: %s, lineText: %s, className %s, completion: %s" % (prefix, lineText, className, completion)
                    result.append((className, completion))

        if len(result) > 0:
            return (result, sublime.INHIBIT_WORD_COMPLETIONS | sublime.INHIBIT_EXPLICIT_COMPLETIONS)
        else:
            return result
