import logging

def get_logger(name):
    log = logging.getLogger(name=name)
    log.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(levelname).05s:%(name)s:%(message)s')

    handler_stream = logging.StreamHandler()
    handler_stream.setFormatter(formatter)
    handler_stream.setLevel(logging.WARNING)

    handler_file = logging.FileHandler('main.log')
    handler_file.setFormatter(formatter)

    log.addHandler(handler_stream)
    log.addHandler(handler_file)

    return log


