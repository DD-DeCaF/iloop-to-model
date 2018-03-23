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

import requests

from iloop_to_model import iloop_client
from iloop_to_model.settings import Default
from iloop_to_model.iloop_to_model import ILOOP_SPECIES_TO_TAXON


class TestUM:
    def setup(self):
        self.api = 'http://localhost:7000'
        self.iloop = iloop_client(Default.ILOOP_API, Default.ILOOP_TOKEN)
        self.experiment = self.iloop.Experiment.instances(where={'type': 'fermentation'})[0]
        samples = self.experiment.read_samples()
        self.sample_ids = [s.id for s in samples]
        self.organism_code = samples[0].strain.organism.short_code
        self.taxon_code = ILOOP_SPECIES_TO_TAXON[self.organism_code]
        self.model = {'ECO': 'iJO1366', 'SCE': 'iMM904'}[self.organism_code]

    def test_request(self):
        payload = {
            'sampleIds': self.sample_ids,
            'phaseId': 1,
            'withFluxes': True,
            'method': 'pfba',
            'modelId': 'iJO1366',
            'objective': 'EX_etoh_e',
        }
        get_queries = {
            '/species',
            '/species/current',
            '/experiments',
            '/experiments/{}'.format(self.taxon_code),
            '/experiments/{}/samples'.format(self.experiment.id),
        }
        post_queries = {
            '/samples/phases': payload,
            '/samples/model-options': payload,
            '/samples/info': payload,
            '/data-adjusted/model': payload,
            '/data-adjusted/fluxes': payload,
            '/data-adjusted/maximum-yield': payload
        }
        for url in get_queries:
            r = requests.get(self.api + url)
            r.raise_for_status()
        for url, payload in post_queries.items():
            r = requests.post(self.api + url, json=payload)
            r.raise_for_status()
