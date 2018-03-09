# Copyright 2018 Novo Nordisk Foundation Center for Biosustainability, DTU.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
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
    SENTRY_DSN = os.environ.get('SENTRY_DSN', '')

    REDIRECTS = {
        'iloop.biosustain.dtu.dk': 'https://iloop.biosustain.dtu.dk/api',
        'app.dd-decaf.eu': 'https://data.dd-decaf.eu/api',
        'cfb-p-web-3.win.dtu.dk': 'https://cfb-p-web-3.win.dtu.dk/api'
    }
