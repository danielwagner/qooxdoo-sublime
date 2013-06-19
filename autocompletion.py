import sublime
import sublime_plugin
import json
import os
import re


class QxAutoCompleteCommand(sublime_plugin.EventListener):
    def __init__(self):
        self.settings = sublime.load_settings("qooxdoo.sublime-settings")
        self.debug = self.settings.get("autocomplete_debug")
        self.qxApi = QxApi(self.settings.get("autocomplete_api_paths"))
        self.qxApi.debug = self.debug

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

        for className in self.qxApi.getData():
            if queryClass and queryClass == className:
                # the query is a fully qualified class name
                # Extract the final part of the class name from the query
                classApi = self.qxApi.getClassApi(queryClass)
                statics = self.qxApi.getStaticMethods(classApi)
                for entry in statics:
                    if prefix in entry[0]:
                        methodName = queryClass + "." + entry[0]
                        if len(entry[1]) > 0:
                            # place the cursor before the first parameter and select it
                            entry[1][0] = "${1:%s}" % entry[1][0]
                        methodWithParams = methodName + "(%s)" % ", ".join(entry[1])
                        result.append((methodName, methodWithParams))

            elif className.startswith(lineText):
                params = []
                namespace = className.split(".")
                isClass = namespace[-1].istitle()
                isStatic = True
                queryDepth = len(lineText.split("."))
                matchDepth = len(className.split("."))

                if isClass and (queryDepth >= matchDepth - 1):
                    # the match is a class, get the constructor params
                    classApi = self.qxApi.getClassApi(className)
                    constructor = self.qxApi.getConstructor(classApi)
                    if constructor:
                        isStatic = False
                        params = self.qxApi.getMethodParams(constructor)

                # query is a partial class name
                completion = prefix + className[len(lineText):]
                # If there's no dot (or maybe word boundary?) in the completion,
                # Sublime will replace the entire lineText so we need the full name
                if not "." in completion:
                    completion = className
                if isClass and not isStatic:
                    if len(params) > 0:
                        # place the cursor before the first parameter and select it
                        params[0] = "${1:%s}" % params[0]
                    completion = completion + "(%s)" % ", ".join(params)
                if self.debug:
                    print "prefix: %s, lineText: %s, className %s, completion: %s" % (prefix, lineText, className, completion)

                result.append((className, completion))

        if len(result) > 0:
            result.sort()
            return (result, sublime.INHIBIT_WORD_COMPLETIONS | sublime.INHIBIT_EXPLICIT_COMPLETIONS)
        else:
            return result


class QxApi():
    def __init__(self, apiPaths):
        self.debug = False
        self.__apiPaths = apiPaths
        self.__classApi = {}
        self.__apiData = None

    def getData(self):
        if not self.__apiData:
            self.__apiData = self._getData()

        return self.__apiData

    def _getData(self):
        data = []
        for path in self.__apiPaths:
            indexPath = os.path.join(path, "apiindex.json")
            libData = None

            if os.path.isfile(indexPath):
                if self.debug:
                    print "Collecting API data from file system path %s" % (indexPath)
                libData = self._loadDataFromFile(indexPath)
            else:
                sublime.error_message("Couldn't load API data: %s does not exist!\nPlease make sure the correct path is configured in Packages/qooxdoo-sublime/qooxdoo.sublime-settings and API data has been generated for the qx library (generate.py api)." % indexPath)
                self.__apiPaths.remove(path)
                continue

            if libData:
                for entry in libData:
                    if not entry in data:
                        data.append(entry)

        return data

    def _loadDataFromFile(self, path):
        indexFile = open(path)
        index = json.load(indexFile)
        data = index["__fullNames__"]

        return data

    def getClassApi(self, className):
        if className in self.__classApi:
            return self.__classApi[className]

        for path in self.__apiPaths:
            classPath = os.path.join(path, className + ".json")
            if os.path.isfile(classPath):
                classData = json.load(open(classPath))
                self.__classApi[className] = classData
                return classData
        if self.debug:
            print "Couldn't load class API for " + className
        return []

    def getStaticMethods(self, classData):
        statics = []
        if "children" in classData:
            for child in classData["children"]:
                if "type" in child and child["type"] == "methods-static":
                    for method in child["children"]:
                        methodName = method["attributes"]["name"]
                        if methodName[:2] != "__":
                            params = self.getMethodParams(method)
                            statics.append((methodName, params))
        return statics

    def getConstructor(self, classData):
        if "children" in classData:
            for child in classData["children"]:
                if "type" in child and child["type"] == "constructor":
                    if "children" in child:
                        for c in child["children"]:
                            if "type" in c and c["type"] == "method":
                                return c
        return None

    def getMethodParams(self, method):
        params = []
        if "children" in method:
            for child in method["children"]:
                if "type" in child and child["type"] == "params":
                    if "children" in child:
                        for param in child["children"]:
                            if "attributes" in param and "name" in param["attributes"]:
                                params.append(param["attributes"]["name"])
        return params
