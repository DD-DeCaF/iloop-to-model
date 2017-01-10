import os


class Default(object):
    ORGANISM_TO_MODEL = {
        'ECO': 'iJO1366',
        'SCE': 'iMM904',
        'CHO': 'iMM1415',
        'COG': 'iNJ661',
    }

    ILOOP_API = os.environ['ILOOP_API']
    ILOOP_TOKEN = os.environ['ILOOP_TOKEN']

    ILOOP_BIOSUSTAIN = 'https://iloop.biosustain.dtu.dk/api'
