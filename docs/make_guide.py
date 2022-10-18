import docutils.core


if __name__ == '__main__':
    docutils.core.publish_file(
        source_path ="guide.rst",
        destination_path ="guide.html",
        writer_name ="html",
        settings_overrides = {'stylesheet': 'guide.css', 'stylesheet_path':''}

    )