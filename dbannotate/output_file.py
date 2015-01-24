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

import os

OUTPUT_DIR = 'db_annotate'


class OutputFile:
    def __init__(self, filename):
        self.fd = None
        self.basename = filename
        self.filename = os.path.join(OUTPUT_DIR, filename)

    @staticmethod
    def create_outputdir():
        if not os.path.exists(OUTPUT_DIR):
            os.mkdir(OUTPUT_DIR)

    def close(self):
        if self.fd is not None:
            self.fd.close()

    def write(self, buf):
        if self.fd is None:
            self.fd = open(self.filename, 'w')
        if '\n' not in buf:
            buf += '\n'
        self.fd.write(buf)
