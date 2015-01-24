#
# Copyright(C) 2015 Romain Bignon, Laurent Defert
#
# db_annotate is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# db_annotate is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import shlex
import subprocess
import sys

from .output_file import OutputFile

class DotFile(OutputFile):
    def render(self, gv_file):
        cmd = ['dot', '-Tcmapx', '-o' + self.filename + '.map', '-Tpng', '-o' + self.filename, gv_file]

        try:
            output = subprocess.check_output(cmd)
        except subprocess.CalledProcessError as e:
            print('Error: command exited while processing fie %s with status %i, displaying:\n%s' % (gv_file, e.returncode, e.output), file=sys.stderr)
