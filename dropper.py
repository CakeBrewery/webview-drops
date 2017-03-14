import os
from threading import Thread

import jinja2
import webview

from bottle import route, static_file, request, response
from bottle import run as run_bottle_server

TEMPLATE_PATH = 'static'
JINJA_ENVIRONMENT = jinja2.Environment(loader=jinja2.FileSystemLoader(TEMPLATE_PATH))

DEFAULT_PORT = 3000
DEFAULT_HOST = 'localhost'


def render(template, context):
    path, filename = os.path.split(template)

    return JINJA_ENVIRONMENT.get_template(filename).render(context)


# Static Handler
@route('/static/<path:path>')
def callback(path):
    return static_file(path, 'static')


@route('/')
def dashboard_handler():
    return render('index.html', context={})


def _show_window():
    webview.create_window("Open file dialog example", url="http://localhost:3000", width=500, height=500)


def _start_server(host=None, port=None):
    run_bottle_server(host=host or 'localhost', port=port or 3000, debug=True)


class Drop(object):
    READY = 'READY'
    FAILED = 'FAILED'
    SUCCESS = 'SUCCESS'
    ABORT = 'ABORT'

    def __init__(self, filename, filepath):
        self.name = filename

        if os.path.isfile(filepath):
            self.path = filepath
            self.status = self.READY
            self.extra = {}
            self.errors = []
        else:
            raise ValueError('Invalid path: {}'.format(filepath))

    def success(self):
        if self.status == self.SUCCESS:
            return True
        return False

    def failed(self):
        if self.status == self.FAILED:
            return True
        return False

    def fail(self, error):
        self.status = self.FAILED
        if error:
            self.errors.append(error)

    def to_dict(self):
        return {
            'name': self.name,
            'path': self.path,
            'status': self.status,
            'extra': self.extra,
            'success': self.success(),
            'failed': self.failed()
        }


class App(object):
    def __init__(self, directory=os.sep, for_each=lambda x: x, fail_condition=None):
        self.__init_routes()

        self.drops = {}
        self.__success_cache = []

        self.directory = directory

        # Callbacks called on each stage for every drop.
        # Each callback gets the current drop as a parameter.
        self.for_each = for_each  # Called on every single drop
        self.for_each_fail = None  # Called on each drop that fails
        self.for_each_success = None  # Called on each drop that succeeds
        self.for_each_done = None  # Called after each drop is done

        self.ready = None  # Called before processing each. Gets all ready drops as parameter.
        self.post_hook = None  # Called when ALL drops are done. Gets all drops as parameter.

        self.fail_condition = fail_condition

        self.port = DEFAULT_PORT
        self.host = DEFAULT_HOST

    def __init_routes(self):
        route('/files')(self.__files_handler)
        route('/file', method='POST')(self.__upload_handler)
        route('/process', method='POST')(self.__process_drop_handler)
        route('/clear', method='POST')(self.__clear_handler)

    def __files_handler(self):
        return {'drops': map(lambda x: x.to_dict(), self.drops.values())}

    def __upload_handler(self):
        file_ = request.files.get('file')

        filepath = os.path.join(self.directory, file_.filename)

        file_.save(filepath, overwrite=True)

        if os.path.isfile(filepath):
            self.add_drop(filepath)
            response.status = 201
            return

        response.status = 500

    def __clear_handler(self):
        self.drops, self.failed_files, self.done_files = 3 * [[]]

    def __process_drop_handler(self):
        filename = request.forms.get('drop')
        if filename in self.drops.keys():
            drop = self.drops[filename]
            if self.process_drop(drop):
                response.status = 200

    def process_drop(self, drop):
        result = self.for_each(drop)

        if self.fail_condition and self.fail_condition(result):
            drop.fail('Did not pass fail_condition check.')
            if self.for_each_fail:
                self.for_each_fail(drop)
        else:
            drop.status = Drop.SUCCESS
            if self.for_each_success:
                self.for_each_success(drop)
        if self.for_each_done:
            self.for_each_done(drop)

    def add_drop(self, filepath):
        if isinstance(filepath, (str, basestring)):
            filename = os.path.basename(filepath)
            drop = Drop(filename, filepath)
            self.drops[filename] = drop

    def successful_drops(self):
        # This is OK here because it's a small app and we use memory to store state.
        # On a larger scale app, a database would be ideal.
        return filter(lambda x: x.success(), self.drops.values())

    def failed_drops(self):
        # This is OK here because it's a small app and we use memory to store state.
        # On a larger scale app, a database would be ideal.
        return filter(lambda x: x.failed(), self.drops.values())

    def start(self):
        ts = Thread(target=_start_server)
        ts.daemon = True
        ts.start()

        _show_window()
