import os


class Default(object):
    ORGANISM_TO_MODEL = {
        'ECO': 'iJO1366',
        'SCE': 'iMM904',
        'CHO': 'iMM1415',
        'COG': 'iNJ661',
        'PPU': 'iJN746',
    }

    ORGANISMS_WITH_MAPS = {'ECO', 'SCE', 'PPU'}

    ILOOP_API = os.environ['ILOOP_API']
    ILOOP_TOKEN = os.environ['ILOOP_TOKEN']
    MODEL_API = os.environ['MODEL_API']

    REDIRECTS = {
        'iloop.biosustain.dtu.dk': 'https://iloop.biosustain.dtu.dk/api',
        'app.dd-decaf.eu': 'https://data.dd-decaf.eu/api',
        'cfb-p-web-3.win.dtu.dk': 'https://cfb-p-web-3.win.dtu.dk/api'
    }
