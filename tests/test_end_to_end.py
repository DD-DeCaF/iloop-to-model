import json

import requests

from iloop_to_model import iloop_client
from iloop_to_model.settings import Default


class TestUM:
    def setup(self):
        self.api = 'http://localhost:7000'
        self.iloop = iloop_client(Default.ILOOP_API, Default.ILOOP_TOKEN)
        self.experiment = self.iloop.Experiment.instances(where={'type': 'fermentation'})[0]
        samples = self.experiment.read_samples()
        self.sample_ids = [s.id for s in samples]
        self.model = {'ECO': 'iJO1366', 'SCE': 'iMM904'}[samples[0].strain.organism.short_code]

    def test_request(self):
        payload = {'sample-ids': json.dumps(self.sample_ids)}
        queries = {
            '/species': {},
            '/experiments': {},
            '/experiments/{}/samples'.format(self.experiment.id): {},
            '/samples/phases': payload,
            '/samples/model-options': payload,
            '/samples/info': payload,
            '/data-adjusted/model?phase-id=1&with-fluxes=1&method=room': payload,
            '/data-adjusted/model': payload,
            '/data-adjusted/fluxes': payload,
            '/data-adjusted/maximum-yield?model-id={}'.format(self.model): payload,
            '/data-adjusted/maximum-yield': payload
        }
        for url, payload in queries.items():
            r = requests.get(self.api + url, params=payload)
            r.raise_for_status()
