import os

from output_file import OutputFile

HTML_BODY = """
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN"
        "http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd">
<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="en" lang="en">
<head>
<meta http-equiv="Content-Type" content="text/html; charset=utf-8"/>
<title>%s</title>
</head>
<body>
"""
HTML_FOOTER = """
</body>
</html>
"""

class HtmlFile(OutputFile):
    def render(self, objects):
        self.write(HTML_BODY % self.filename)
        for obj in objects:
            obj['url'] = os.path.basename(obj['filename'])
            self.write('<figure><embed type="image/svg+xml" src="%s" width="50%%" height="50%%"/></figure>'
                    % obj['url'])
        self.write(HTML_FOOTER)
