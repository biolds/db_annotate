import os

OUTPUT_DIR = 'db_annotate'


class OutputFile:
    def __init__(self, filename):
        self.fd = None
        self.filename = os.path.join(OUTPUT_DIR, filename)

    def write(self, buf):
        if self.fd is None:
            if not os.path.exists(OUTPUT_DIR):
                os.mkdir(OUTPUT_DIR)
            self.fd = open(self.filename, 'w')
        self.fd.write(buf)

    def exists(self):
        exists = os.path.exists(self.filename)
        if exists:
            print("Warning: file %s already exists. Remove it first to rebuild it." % self.filename)
        return exists
