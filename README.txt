The shell_helper module implements a class which helps when calling shell commands.  The main
benefit is that command output can be captured to a file at the same time it is being sent to
the std_out (console).  Additionally there are commands for deleting files and coping files.

To Install:
Linux: sudo easy_install dist/shell_helper-1.5-py2.7.egg
Windows: easy_install dist\shell_helper-1.5-py2.7.egg

To Build the installer EGG:
python setup.py bdist_egg
