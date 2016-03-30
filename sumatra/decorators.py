"""
Decorators to make it easier to use Sumatra in your own Python scripts.

Usage:

@capture
def main([parameters and other args...]):
    <body of main function>


:copyright: Copyright 2006-2015 by the Sumatra team, see doc/authors.txt
:license: BSD 2-clause, see LICENSE for details.
"""
from __future__ import unicode_literals

from builtins import str
import time
from sumatra.programs import PythonExecutable
from sumatra.parameters import ParameterSet, SimpleStringParameterSet
import sys
import os
import contextlib
from io import StringIO


class _ByteAndUnicodeStringIO(StringIO):
    """A StringIO subclass accepting `str` in Py2 and `str` in Py3.

    The io.StringIO implementation does not accept Py2 `str`.
    """
    def write(self, object):
        StringIO.write(self, str(object))

class _ByteAndUnicodeStringIOAndStdout(_ByteAndUnicodeStringIO):
    """ Also writes to STDOUT."""
    def write(self, object):
        sys.__stdout__.write(object)
        super(_ByteAndUnicodeStringIO, self).write(str(object))

@contextlib.contextmanager
def _grab_stdout_stderr():
    try:
        output = _ByteAndUnicodeStringIOAndStdout()
        sys.stdout, sys.stderr = output, output
        yield output
    finally:
        sys.stdout, sys.stderr = sys.__stdout__, sys.__stderr__
        output = output.getvalue()


def capture(main):
    """
    Decorator for a main() function, which will create a new record for this
    execution.

    The arguments of main can be recorded as parameters for this execution:
    * If the first (un-named) argument is a ParameterSet, or there is a named
      argument "parameters" containing a ParameterSet, then that is recorded.
    * Otherwise, all arguments to the function are packaged into a 
      SimpleStringParameterSet.    
    The first argument of main() must be a parameter set.
    """
    def wrapped_main(*args, **kwargs):

        if len(args) > 0 and isinstance(args[0], ParameterSet):
            # If the first argument is a ParameterSet
            parameters = args[0]
        elif len(kwargs) > 0 and "parameters" in kwargs \
                and isinstance(kwargs["parameters"], ParameterSet):
            # If there is a named "parameters" argument
            parameters = kwargs["parameters"]
        else:
            # Package all parameters into a SimpleStringParameterSet
            parameters = dict(zip(["arg%d" % x for x in range(len(args))], args))
            parameters.update(kwargs)
            parameters = SimpleStringParameterSet(parameters)

        import sumatra.projects
        project = sumatra.projects.load_project()
        main_file = sys.modules['__main__'].__file__
        executable = PythonExecutable(path=sys.executable)
        record = project.new_record(parameters=parameters,
                                    main_file=main_file,
                                    executable=executable)
        record.launch_mode.working_directory = os.getcwd()
        parameters.update({"sumatra_label": record.label})
        start_time = time.time()
        with _grab_stdout_stderr() as stdout_stderr:
            main_result = main(*args, **kwargs)
            record.stdout_stderr = stdout_stderr.getvalue()
        record.duration = time.time() - start_time
        record.output_data = record.datastore.find_new_data(record.timestamp)
        project.add_record(record)
        project.save()
        return main_result

    return wrapped_main
