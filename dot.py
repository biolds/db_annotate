import shlex
import subprocess
import sys

from output_file import OutputFile

class DotFile(OutputFile):
    def render(self, gv_file):
        if self.exists():
            return
        cmd = ['dot', '-Tpng', '-o', self.filename, gv_file]

        try:
            output = subprocess.check_output(cmd)
        except subprocess.CalledProcessError as e:
            print('Error: command exited with status %i, displaying:\n%s' % (e.returncode, e.output), file=sys.stderr)
