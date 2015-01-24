import shlex
import subprocess
import sys

from output_file import OutputFile

class DotFile(OutputFile):
    def render(self, gv_file):
        cmd = ['dot', '-Tcmapx', '-o' + self.filename + '.map', '-Tpng', '-o' + self.filename, gv_file]

        try:
            output = subprocess.check_output(cmd)
        except subprocess.CalledProcessError as e:
            print('Error: command exited while processing fie %s with status %i, displaying:\n%s' % (gv_file, e.returncode, e.output), file=sys.stderr)
