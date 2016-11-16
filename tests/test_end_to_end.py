import requests
import pytest
from iloop_to_model import iloop_client
from iloop_to_model.settings import Default


class TestUM:
    def setup(self):
        self.api = 'http://localhost:7000'
        self.iloop = iloop_client(Default.ILOOP_API, Default.ILOOP_TOKEN)
        self.public = dict(experiment=None)
        self.not_public = dict(experiment=None)
        for experiment in self.iloop.Experiment.instances(where={'type': 'fermentation'}):
            if experiment.project.code in Default.NOT_PUBLIC:
                self.not_public['experiment'] = experiment
            else:
                self.public['experiment'] = experiment
            if self.public['experiment'] and self.not_public['experiment']:
                break
        for p in [self.public, self.not_public]:
            p['sample'] = p['experiment'].read_samples()[0]

    def get_urls(self, mapping):
        return [
            '/experiments/{}/maximum-yield'.format(mapping['experiment'].id),
            '/samples/{}/maximum-yield'.format(mapping['sample'].id),
            '/samples/{}/model'.format(mapping['sample'].id),
            '/samples/{}/model/fluxes'.format(mapping['sample'].id),
            '/samples/{}/phases'.format(mapping['sample'].id),
        ]

    def test_public(self):
        for url in self.get_urls(self.public):
            r = requests.get(self.api + url)
            r.raise_for_status()

    def test_not_public(self):
        for url in self.get_urls(self.not_public):
            r = requests.get(self.api + url)
            assert r.status_code == 403
            with pytest.raises(requests.exceptions.HTTPError):
                r.raise_for_status()
