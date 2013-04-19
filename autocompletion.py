import sublime
import sublime_plugin
import json
import urllib
import os

DEBUG = False
API_URL = "http://demo.qooxdoo.org/current/apiviewer/script/apiindex.json"
INDEX_FILE = "apiindex.json"


class QxAutoCompleteCommand(sublime_plugin.EventListener):
    def __init__(self):
        self.apidata = self._getData()

    def _getData(self):
        if os.path.isfile(INDEX_FILE):
            fileObj = open(INDEX_FILE)
            data = json.load(fileObj)
            if DEBUG:
                print "Loading API data from file"
        else:
            indexFile = urllib.urlopen(API_URL)
            index = indexFile.read()
            index = json.loads(index)
            data = index["__fullNames__"]
            if DEBUG:
                print "Loading API data from URL"
            fileObj = open(INDEX_FILE, "w+")
            json.dump(data, fileObj)

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
        for className in self.apidata:
            if className.startswith(lineText):
                completion = prefix + className[len(lineText):]
                if len(prefix) == 1 and prefix[0].isupper():
                    completion = className
                if DEBUG:
                    print "prefix: %s, lineText: %s, className %s, completion: %s" % (prefix, lineText, className, completion)
                result.append((className, completion))

        if len(result) > 0:
            return (result, sublime.INHIBIT_WORD_COMPLETIONS | sublime.INHIBIT_EXPLICIT_COMPLETIONS)
        else:
            return result
