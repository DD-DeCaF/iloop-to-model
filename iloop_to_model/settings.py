import os


class Default(object):
    ORGANISM_TO_MODEL = {
        'ECO': 'iJO1366',
        'SCE': 'iMM904',
        'CHO': 'iMM1415',
        'COG': 'iNJ661',
    }

    MODEL_TO_MAP = {
        'iJO1366': 'maps/iJO1366.Central metabolism.json',
        'iMM904': 'maps/iMM904.Central carbon metabolism.json',
    }

    ILOOP_API = os.environ['ILOOP_API']
    ILOOP_TOKEN = os.environ['ILOOP_TOKEN']

    REDIRECTS = {
        'cfb.dd-decaf.eu': 'https://iloop.biosustain.dtu.dk/api',
        'app.dd-decaf.eu': 'https://data.dd-decaf.eu/api',
        'cfb-p-web-3.win.dtu.dk': 'https://cfb-p-web-3.win.dtu.dk/api'
    }
