import os

OUTPUT_DIR = 'db_annotate'


class OutputFile:
    def __init__(self, filename):
        self.fd = None
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

    def exists(self, filename=None):
        filename = filename or self.filename
        exists = os.path.exists(filename)
        if exists:
            print("Warning: file %s already exists. Remove it first to rebuild it." % filename)
        return exists
