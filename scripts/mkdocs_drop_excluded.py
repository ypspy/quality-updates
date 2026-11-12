"""Keep exclude_docs files out of mkdocs serve as well as mkdocs build.

Serve otherwise renders project/ and superpowers/ for a local preview and logs every link inside them.
"""


def on_files(files, config, **kwargs):
    for file in list(files):
        if file.inclusion.is_excluded():
            files.remove(file)
    return files
