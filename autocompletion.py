import sublime
import sublime_plugin
import json
import os
import re

settings = sublime.load_settings("qooxdoo.sublime-settings")


class AutoCompletion(sublime_plugin.EventListener):
    def __init__(self):
        self.debug = "AutoCompletion" in settings.get("debug")
        self.__qxApi = None

    def _getApi(self):
        if not self.__qxApi:
            qxLibs = settings.get("libraries")
            if not qxLibs or len(qxLibs) == 0:
                if self.debug:
                    print "No libraries configured in qooxdoo.sublime-settings, scanning project folders."
                qxLibs = LibraryUtil.getQxLibs()
                if not "qooxdoo" in qxLibs:
                    if self.debug:
                        print "Searching project config for qooxdoo SDK path..."
                    fileName = sublime.active_window().active_view().file_name()
                    libRoot = LibraryUtil.getLibRoot(fileName)
                    qxPath = LibraryUtil.getQxPath(libRoot)
                    if qxPath:
                        qxLibs["qooxdoo"] = os.path.join(qxPath, "framework")

            apiPaths = LibraryUtil.getApiPaths(qxLibs)
            self.__qxApi = Api(apiPaths)
            self.__qxApi.debug = self.debug

        return self.__qxApi

    def on_query_completions(self, view, prefix, locations):
        # Only trigger within JS
        if not view.match_selector(locations[0], "source.js"):
            return []

        qxApi = self._getApi()
        if not qxApi:
            return []

        isEnvironmentGet = False
        isSingletonQuery = False
        isInstantiation = False

        # get the line text from the cursor back to last space
        result = []
        sel = view.sel()
        region = sel[0]
        line = view.line(region)
        lineText = view.substr(line)
        temp = re.split('\s', lineText)
        lineText = temp[-1]

        if temp[-2] and temp[-2] == "new":
            isInstantiation = True

        queryClass = re.search("(.*?[A-Z]\w*)", lineText)
        if queryClass:
            queryClass = queryClass.group(1)

            if lineText.split(".")[-2:-1][0] == "getInstance()":
                isSingletonQuery = True

            if queryClass == "qx.core.Environment" and (prefix == "g" or prefix == "ge" or prefix == "get"):
                isEnvironmentGet = True

        for className in qxApi.getData():
            if queryClass and queryClass == className:
                result.extend(qxApi.getClassCompletions(className, isEnvironmentGet, isSingletonQuery, isInstantiation))

            if className.startswith(lineText):
                result.extend(qxApi.getPartialCompletions(className, prefix, lineText))

        if len(result) > 0:
            result.sort()
            return (result, sublime.INHIBIT_WORD_COMPLETIONS | sublime.INHIBIT_EXPLICIT_COMPLETIONS)
        else:
            return result


class Api():
    def __init__(self, apiPaths):
        self.debug = False
        self.__apiPaths = apiPaths
        self.__classApi = {}
        self.__apiData = None

    def getClassCompletions(self, className, isEnvironmentGet, isSingletonQuery, isInstantiation):
        result = []
        methods = []
        classApi = self.getClassApi(className)

        if isSingletonQuery:
            methods = self.getMethods(classApi, "instance")

        elif isEnvironmentGet:
            envKeys = self.getEnvironmentKeys(classApi)
            for key in envKeys:
                keyName = "\"%s\"" % key
                entry = ("get", [keyName])
                methods.append(entry)

        else:
            methods = self.getMethods(classApi, "static")

        for entry in methods:
            #if prefix in entry[0]:
            if isSingletonQuery:
                methodName = className + "." + entry[0]
                paramStr = "(%s)" % ", ".join(entry[1])
                methodWithParams = entry[0] + paramStr

            elif isEnvironmentGet:
                paramStr = "(%s)" % ", ".join(entry[1])
                methodName = entry[0] + paramStr
                methodWithParams = entry[0] + paramStr

            else:
                methodName = className + "." + entry[0]
                paramStr = "(%s)" % ", ".join(entry[1])
                methodWithParams = methodName + paramStr
                if len(entry[1]) > 0:
                    # place the cursor to the left of the first parameter and select it
                    entry[1][0] = "${1:%s}" % entry[1][0]

            result.append((methodName, methodWithParams))

        return result

    def getPartialCompletions(self, className, prefix, lineText):
        result = []
        namespace = className.split(".")

        params = []
        isClass = namespace[-1][0].istitle()
        isStatic = True
        isSingleton = False

        queryDepth = len(lineText.split("."))
        matchDepth = len(className.split("."))

        if isClass and (queryDepth >= matchDepth - 1):
            # the match is a class, get the constructor params
            classApi = self.getClassApi(className)
            isSingleton = self.isSingleton(classApi)

            if not isSingleton:
                constructor = self.getConstructor(classApi)
                if constructor:
                    isStatic = False
                    params = self.getMethodParams(constructor)

        completion = prefix + className[len(lineText):]
        # If there's no dot (or maybe word boundary?) in the completion,
        # Sublime will replace the entire lineText so we need the full name
        if not "." in completion:
            completion = className
        if isClass:
            if isSingleton:
                completion = completion + ".getInstance()"
            if not isStatic:
                if len(params) > 0:
                    # place the cursor before the first parameter and select it
                    params[0] = "${1:%s}" % params[0]
                completion = completion + "(%s)" % ", ".join(params)
        if self.debug:
            print "prefix: %s, lineText: %s, className %s, completion: %s" % (prefix, lineText, className, completion)

        result.append((className, completion))

        return result

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

    def getMethods(self, classData, methodType):
        if methodType == "instance":
            methodType = "methods"
        else:
            methodType = "methods-static"
        methods = []
        if "children" in classData:
            for child in classData["children"]:
                if "type" in child and child["type"] == methodType:
                    for method in child["children"]:
                        methodName = method["attributes"]["name"]
                        if methodName[:2] != "__":
                            params = self.getMethodParams(method)
                            methods.append((methodName, params))
        return methods

    def getConstructor(self, classData):
        if "children" in classData:
            for child in classData["children"]:
                if "type" in child and child["type"] == "constructor":
                    if "children" in child:
                        for c in child["children"]:
                            if "type" in c and c["type"] == "method":
                                return c

        if "superClass" in classData["attributes"]:
            superClassName = classData["attributes"]["superClass"]
            superClass = self.getClassApi(superClassName)
            if superClass:
                return self.getConstructor(superClass)

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

    def isSingleton(self, classData):
        if "attributes" in classData and "isSingleton" in classData["attributes"]:
                return classData["attributes"]["isSingleton"]

        return False

    def getEnvironmentKeys(self, envApi):
        reg = re.compile(r"\<td\>([\w\.]+?)\<\/td\>", re.M)
        envKeys = []
        if "children" in envApi:
            for child in envApi["children"]:
                if "type" in child and child["type"] == "desc":
                    if "attributes" in child and "text" in child["attributes"]:
                        desc = child["attributes"]["text"]
                        match = reg.findall(desc)
                        if match:
                            match.sort()
                            envKeys = match
        return envKeys


class LibraryUtil():

    @staticmethod
    def getQxLibName(manifestPath):
        if not os.path.isfile(manifestPath):
            return None
        try:
            manifest = json.load(open(manifestPath, "r"))
            if "info" in manifest and "qooxdoo-versions" in manifest["info"]:
                # looks like a valid qx library manifest
                if "name" in manifest["info"]:
                    return manifest["info"]["name"]
        except Exception:
            qxV = LibraryUtil.findJsonValue(open(manifestPath, "r"), "qooxdoo-versions")
            if qxV:
                return LibraryUtil.findJsonValue(open(manifestPath, "r"), "name")

        return None

    @staticmethod
    def getQxPath(libRoot):
        qxPath = None
        libConfig = os.path.join(libRoot, "config.json")

        if (os.path.isfile(libConfig)):
            if LibraryUtil.debug:
                print "Found project config at %s." % libConfig
            try:
                config = json.load(open(libConfig, "r"))
                if "let" in config and "QOOXDOO_PATH" in config["let"]:
                    qxPath = config["let"]["QOOXDOO_PATH"]
            except Exception:
                qxPath = LibraryUtil.findJsonValue(open(libConfig, "r"), "QOOXDOO_PATH")

            if qxPath:
                qxPath = os.path.abspath(os.path.join(libRoot, qxPath))

        return qxPath

    @staticmethod
    def getApiPaths(qxLibs):
        apiPaths = []
        libNames = qxLibs.keys()
        if "qooxdoo" in libNames:
            libNames.remove("qooxdoo")
            libNames.insert(0, "qooxdoo")

        for qxLibName in libNames:
            libPath = qxLibs[qxLibName]
            if LibraryUtil.debug:
                    print "Looking for '%s' API data..." % qxLibName
            apiPath = os.path.join(libPath, "api", "script")
            if os.path.isdir(apiPath):
                if LibraryUtil.debug:
                    print "Found API data for library %s in directory %s." % (qxLibName, apiPath)
                apiPaths.append(apiPath)

        return apiPaths

    @staticmethod
    def findJsonValue(handle, key):
        regExp = '"%s"\s*?:\s*?(.*?)\s*?\,?$' % key
        for line in handle:
            match = re.search(regExp, line)
            if match and not "//" in line.split(key)[0]:
                return match.group(1).replace('"', '').strip()

        return None

    @staticmethod
    def getLibRoot(fileName):
        if LibraryUtil.debug:
            print "Searching for library root of '%s'..." % fileName
        dirName = os.path.dirname(fileName)
        dirName = dirName.split(os.sep)
        while len(dirName) > 0:
            currentDir = os.sep.join(dirName)
            manifest = os.path.join(currentDir, "Manifest.json")
            if (os.path.isfile(manifest)):
                if LibraryUtil.debug:
                    print "Root directory is %s." % currentDir
                return currentDir
            dirName.pop()

        return None

    @staticmethod
    def getQxLibs():
        qxLibs = {}
        folders = sublime.active_window().folders()
        for folder in folders:
            manifestPath = os.path.join(folder, "Manifest.json")
            qxLibName = LibraryUtil.getQxLibName(manifestPath)
            if qxLibName and not qxLibName in qxLibs:
                qxLibs[qxLibName] = os.path.dirname(manifestPath)

        return qxLibs

LibraryUtil.debug = "LibraryUtil" in settings.get("debug")
