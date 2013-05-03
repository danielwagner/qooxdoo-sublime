import sublime
import sublime_plugin
import json
import os
import re


class QxAutoCompleteCommand(sublime_plugin.EventListener):
    def __init__(self):
        self.settings = sublime.load_settings("qooxdoo.sublime-settings")
        self.debug = self.settings.get("autocomplete_debug")
        self.apidata = self.getData()
        self.classApi = {}

    def getData(self):
        data = []
        apiPaths = self.settings.get("autocomplete_api_paths")
        for path in apiPaths:
            path = os.path.join(path, "apiindex.json")
            libData = None

            if os.path.isfile(path):
                if self.debug:
                    print "Collecting API data from file system path %s" % (path)
                libData = self.loadDataFromFile(path)
            else:
                if self.debug:
                    print "Couldn't load API data: %s does not exist!" % path
                continue

            if libData:
                for entry in libData:
                    if not entry in data:
                        data.append(entry)

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

        # get the line text from the cursor back to last space
        result = []
        sel = view.sel()
        region = sel[0]
        line = view.line(region)
        lineText = view.substr(line)
        lineText = re.split('\s', lineText)[-1]

        queryClass = re.search("(.*?[A-Z]\w*)", lineText)
        if queryClass:
            queryClass = queryClass.group(1)

        if len(result) == 0:
            for className in self.apidata:
                if queryClass and queryClass == className:
                    # the query is a fully qualified class name
                    # Extract the final part of the class name from the query
                    classApi = self.getClassApi(queryClass)
                    for entry in classApi:
                        if prefix in entry:
                            methodName = queryClass + "." + entry
                            result.append((methodName, methodName))

                elif className.startswith(lineText):
                    # query is a partial class name
                    completion = prefix + className[len(lineText):]
                    if len(prefix) == 1 and prefix[0].isupper():
                        completion = className
                    if self.debug:
                        print "prefix: %s, lineText: %s, className %s, completion: %s" % (prefix, lineText, className, completion)
                    result.append((className, completion))

        if len(result) > 0:
            return (result, sublime.INHIBIT_WORD_COMPLETIONS | sublime.INHIBIT_EXPLICIT_COMPLETIONS)
        else:
            return result

    def getClassApi(self, className):
        if className in self.classApi:
            return self.getStaticMethods(self.classApi[className])

        apiPaths = self.settings.get("autocomplete_api_paths")
        for path in apiPaths:
            classPath = os.path.join(path, className + ".json")
            if os.path.isfile(classPath):
                classData = json.load(open(classPath))
                self.classApi[className] = classData
                return self.getStaticMethods(classData)
        if self.debug:
            print "Couldn't load class API for " + className
        return []

    def getStaticMethods(self, classData):
        statics = []
        if "children" in classData:
            for child in classData["children"]:
                if "type" in child and child["type"] == "methods-static":
                    for method in child["children"]:
                        statics.append(method["attributes"]["name"])
        return statics
