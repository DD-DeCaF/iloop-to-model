import os


class Default(object):
    ORGANISM_TO_MODEL = {
        'ECO': 'iJO1366',
        'SCE': 'iMM904',
        'CHO': 'iMM1415',
        'COG': 'iNJ661',
    }

    NOT_PUBLIC = {'NPC'}

    ILOOP_API = os.environ['ILOOP_API']
    ILOOP_TOKEN = os.environ['ILOOP_TOKEN']
