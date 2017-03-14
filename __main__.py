import contextlib
import shutil
import tempfile

import dropper


@contextlib.contextmanager
def tempdir():
    """
    Create a temporary directory context manager.
    :return:
    """
    temp_dir = tempfile.mkdtemp()
    try:
        yield temp_dir
    finally:
        shutil.rmtree(temp_dir)


def for_each_cb(drop):
    """ To be called on each file upon pressing the "process" button.
    :param file_: Current file to process
    :return: Something meaninful to pass to fail_condition_cb
    """
    file_ = drop.path
    print "CALLBACK HAPPENING!! processing: {}".format(file_)
    return file_


def fail_condition_cb(result):
    """ Checks the result of for_each_cb and decides whether the file
    failed or not.
    :param result: result from for_each_cb
    :return: True if condition triggers, else False.
    """
    if not result:
        return True


if __name__ == '__main__':
    with tempdir() as directory:
        app = dropper.App(directory=directory, for_each=for_each_cb, fail_condition=fail_condition_cb)
        app.start()
