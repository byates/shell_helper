###################################################################################################
# Python prerequisites:
#  * Pyhton 2.7
###################################################################################################

# import sys
import os
import glob
import shutil
import subprocess
import callbacks
import argparse
from Queue import Queue, Empty

class ShellHelper(object):
    """
    Class to support shell operations.
    """

    __LogFile = None

    def __init__(self, logfile = None):
        if logfile:
            self.OpenLogFile(LogFileName = logfile, Append = False)

    def __del__(self):
        self.CloseLogFile()

    def OpenLogFile(self, LogFileName, Append = False):
        """
        Opens a LOG file where all output from commands executed via the Run() method will
        be sent.  The output will also be sent to the callback function if one is specified.
        """
        if Append:
            Filemode = 'a'
        else:
            Filemode = 'w'

        self.CloseLogFile()

        try:
            self.__LogFile = open(LogFileName, Filemode)
        except IOError:
            self.__LogFile = None

    def __MaybeAddToLog(self, line):
        """
        Adds the line to the log file if one is open.
        """
        if (self.__LogFile != None) and line:
            self.__LogFile.write(line + '\n')

    def CloseLogFile(self):
        """
        Closes any previously open log file.
        """
        if self.__LogFile != None:
            self.__LogFile.close()
            self.__LogFile = None

    def __CleanupCmdOutput(self, line):
        """
        Command output captured from stdout.readline() may have multiple line feeds.  We will
        strip those.
        """
        for _i in range(3):
            line = line.rstrip('\x0a')
            line = line.rstrip('\x0d')
        return(line)

    def __CallRunCallback(self, line):
        """
        Sends the new line to the registered callback (if any)
        """
        if line:
            callbacks.RunAllCallbacks(self, 'run_callback', line)

    def RegisterRunCallback(self, callback_function):
        '''Registers the callback to be invoked when there is output from a Run() session.'''
        callback = callbacks.PermanentCallback(callback_function)
        callbacks.RegisterCallback(self, 'run_callback', callback)

    def ClearCallback(self, callback_function):
        '''Removes a previously registered callback.'''
        callbacks.ClearCallback(self, 'run_callback', callback_function)

    def ClearAllCallbacks(self):
        '''Removes all previously registered callbacks.'''
        callbacks.ClearCallbacks(self, 'run_callback')

    def RunCmd(self, cmd, workingDir = "", echo_cmd = True):
        """
        Runs a command and sends the output to a log file (if one is open) or to the callback
        function (if one is specified).
        """
        orig_path = os.getcwd()
        if workingDir:
            os.chdir(workingDir)

        if echo_cmd:
            print("<-" + cmd)
        self.__MaybeAddToLog("<-" + cmd)
        try:
            p = subprocess.Popen(cmd, shell = True,
                                 stdout = subprocess.PIPE,
                                 stderr = subprocess.STDOUT)
            while True:
                line = self.__CleanupCmdOutput(p.stdout.readline())
                if (not line) and (p.poll() != None):
                    break
                self.__MaybeAddToLog(line)
                self.__CallRunCallback(line)

            line = ""
            self.__MaybeAddToLog(line)
            self.__CallRunCallback(line)
        except KeyboardInterrupt:
            line = "   ---USER BREAK [CONTROL-C]---\n"
            self.__MaybeAddToLog(line)
            self.__CallRunCallback(line)
            os.chdir(orig_path)
            return (-1)

        os.chdir(orig_path)
        return (p.returncode)

    @staticmethod
    def __enqueue_output(out, queue):
        for line in iter(out.readline, b''):
            queue.put(line)
        out.close()

    def RunCmdCaptureOutput(self, cmd, workingDir = "", inputStr = None, echo_cmd = True):
        """
        Runs a command and sends the output to a log file (if one is open) and saves the
        output as a list of lines.  NOTE: Does not send output to any callbacks.

        Returns a tuple of the command result code and the captured output (list of lines).
        """
        orig_path = os.getcwd()
        if workingDir:
            os.chdir(workingDir)

        if echo_cmd:
            print("<-" + cmd)
            if inputStr:
                for line in inputStr.split('\n'):
                    print('  << ' + line)

        self.__MaybeAddToLog("<-" + cmd)
        if inputStr:
            for line in inputStr.split('\n'):
                self.__MaybeAddToLog('  << ' + line)

        try:
            p = subprocess.Popen(cmd, shell = True,
                                 stdin = subprocess.PIPE,
                                 stdout = subprocess.PIPE,
                                 stderr = subprocess.PIPE)
            Output = p.communicate(inputStr)
            StdOutput = self.__CleanupCmdOutput(Output[0]).split('\n')
            ErrOutput = self.__CleanupCmdOutput(Output[1]).split('\n')
            for line in StdOutput:
                line = self.__CleanupCmdOutput(line)
                self.__MaybeAddToLog(line)
            for line in ErrOutput:
                line = self.__CleanupCmdOutput(line)
                self.__MaybeAddToLog(line)
            if (len(StdOutput) == 1) and (StdOutput[0] == ''):
                StdOutput = None
            if (len(ErrOutput) == 1) and (ErrOutput[0] == ''):
                ErrOutput = None
        except KeyboardInterrupt:
            line = "   ---USER BREAK [CONTROL-C]---\n"
            self.__MaybeAddToLog(line)
            os.chdir(orig_path)
            return (-1)

        os.chdir(orig_path)
        return ((p.returncode, StdOutput, ErrOutput))

    @staticmethod
    def DeleteFilesInDir(dirPath, match_pattern = "*.*", ignore_pattern = ""):
        """
        Deletes all files in the passed directory that match the match_pattern
        and fail the ignore_pattern.
        Return an empty string if all files were able to be deleted otherwise returns the first
        File path that was unable to be removed.
        """

        existing_files = glob.glob(os.path.join(dirPath, match_pattern))
        if (ignore_pattern != ""):
            ignored_files = glob.glob(os.path.join(dirPath, ignore_pattern))
        else:
            ignored_files = []

        for File in existing_files:
            if File in ignored_files:
                continue
            try:
                os.remove(File)
            except:
                return(os.path.abspath(File))

        return("")

    @staticmethod
    def DeleteEveryThingInDir(dirPath):
        """
        Deletes all files and sub-directories in the passed directory.
        """
        print("cleaning " + dirPath)
        for root, dirs, files in os.walk(dirPath):
            for f in files:
                os.unlink(os.path.join(root, f))
            for d in dirs:
                shutil.rmtree(os.path.join(root, d))

    @staticmethod
    def copy_files_by_glob(globList = [], destPath = "", workingDir = ""):
        """
        Copies files matching the glob pattern list from source directories to the
        dest directory.  All directories are assumed to be either absolute paths or
        paths relative to the workingDir.
        Return True or False depending on if all the files could be copied or not.
        """

        # Sanity checks
        if not globList:
            return(True)

        if not destPath:
            raise ValueError("destPath path can't be empty")

        if not os.path.isabs(destPath):
            destPath = os.path.join(workingDir, destPath)

        # Get a list of all the net list files
        file_list = []
        for file_glob in globList:
            # If path is not absolute then prepend the relative path to the working directory
            # We assume that all relative paths are relative the the working directory.
            if not os.path.isabs(file_glob):
                file_glob = os.path.join(workingDir, file_glob)
            file_list.extend(glob.glob(os.path.abspath(file_glob)))

        # Copy each file in the file_list to the dest directory
        for File in file_list:
            if os.path.isfile(File):
                _head, tail = os.path.split(File)
                dest = os.path.join(destPath, tail)
                shutil.copyfile(File, dest)
            else:
                print("Could not find file '" + File + "'")
                return(False)

        return(True)

    @staticmethod
    def hex(value):
        """
        Same as standard hex function (converts int to hex string) but ensures that there is
        not trailing 'L' which python adds sometimes.
        """
        return(hex(value).strip('L'))


def __callback_test(text):
    print('*' + text)


if __name__ == '__main__':

    # Create a parser for the command line arguments.  Add any special options prior
    # to creating the shell_helper class instance.
    Parser = argparse.ArgumentParser()
    # Parse command line self.Args
    Parser.add_argument('-l', '--logfile', default = '',
                        help = 'Used to override the default log file.')
    Args = Parser.parse_args()

    SH = ShellHelper(Args.logfile)
    SH.RegisterRunCallback(__callback_test)
    r = SH.RunCmd('dir')
    print("Return Code={0}".format(r))

