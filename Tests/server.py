# Creates a server to test against

import flask


class TestServer():

    def __init__(self):
        self.app = flask.Flask(__name__, static_folder='Resources')
        self.setup()

    def setup(self):
        @self.app.route("/")
        def index():
            return "<p>Podcast Fetcher Test Server</p>"

        @self.app.route("/resource/<path:name>")
        def get_resource(name):
            return flask.send_from_directory(
                self.app.static_folder, name, as_attachment=False
            )

    def start(self):
        self.app.run()


def main():
    pass


if __name__ == "__main__":
    main()
