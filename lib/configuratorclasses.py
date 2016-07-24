#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import re

class Config_Value(object):

    def __init__(self, name):
        self.name = name
        self.options = []
        self.reactions = {}

    def addOption(self, option, reaction):
        if option not in self.options:
            self.options.append(option)
        # if the key "option" is not existing in the reactions-dict, add an empty list as value
        self.reactions.setdefault(option, [])
        # add the reaction to the list if it is not included
        if reaction not in self.reactions.get(option):
            self.reactions.get(option).append(reaction)
        return True

class Command_chain(object):

    def __init__(self):
        self.chain = ""

    def addCommand(self, cmd):
        if self.chain == "":
            self.chain = self.chain + cmd
        else:
            self.chain = self.chain + " && " + cmd

    def hasCommand(self, cmd):
        return cmd in self.chain

    def __str__(self):
        return self.chain

class DesktopFile(object):

    def __init__(self, path):
        self.path = path
        self.applicationname="NotSet"
        self.exec_command = "echo 'No Command specified'"
        self.enabled = True
        self.comment = ""
        self.empty_content = """
        [Desktop Entry]
        Type=Application
        Name={name}
        Exec={exec_command}
        Comment={comment}
        Terminal=false
        {enable}NotShowIn=LXDE
                       """
        self.content = ""

    def isExisting(self):
        return os.path.isfile(path=self.path)

    def loadExisting(self):
        with open(self.path, 'r') as myfile:
            self.content = myfile.read()
        try:
            self.applicationname = re.search('(?<=Name=).*', self.content, re.IGNORECASE).group(0)
        except AttributeError: # case None-Type (not found)
            self.applicationname = "NotSet"

        try:
            self.exec_command = re.search('(?<=Exec=).*', self.content, re.IGNORECASE).group(0)
        except AttributeError: # case None-Type (not found)
            self.exec_command = "echo 'No Command specified'"

        try:
            self.comment = re.search('(?<=Comment=).*', self.content, re.IGNORECASE).group(0)
        except AttributeError:
            self.comment = ""

        try:
            self.enabled = False if len(re.findall('\nNotShowIn=', self.content, re.IGNORECASE)) > 0 else True
        except:
            self.enabled = True
        return True

    def setApplicationName(self, name):
        self.applicationname = name
        return True

    def getApplicationName(self):
        return self.applicationname

    def setExecCommand(self, command):
        self.exec_command = command
        return True

    def getExecCommand(self):
        return self.exec_command

    def setComment(self, comment):
        self.comment = comment
        return True

    def getComment(self):
        return self.comment

    def isEnabled(self):
        return self.enabled

    def setEnabled(self, _bool):
        self.enabled = _bool
        return True

    def write(self):
        """
        [Desktop Entry]
        Type=Application
        Name={name}
        Exec={exec_command}
        Comment={comment}
        Terminal=false
        {enable}NotShowIn=LXDE
        """
        self.empty_content.format(name=self.applicationname,
                                  exec_command=self.exec_command,
                                  comment=self.comment,
                                  enable="#" if not self.enabled else "")

        with open(self.path, 'w') as myfile:
            myfile.write(self.empty_content)

        return True


class Execution_Command(object):

    def __init__(self, basecommand):
        self.command = basecommand

    def addPrefix(self, prefix):
        self.command = str(prefix).decode("utf-8") + " " + self.command
        return True

    def addPostfix(self, postfix):
        self.command = self.command + " " + str(postfix).decode("utf-8")
        return True

    def __str__(self):
        return self.command
