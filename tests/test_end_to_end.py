import requests
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
            '/samples/{}/maximum-yield'.format(mapping['sample'].id),
            '/samples/{}/model?phase-id=1&with-fluxes=1'.format(mapping['sample'].id),
            '/samples/{}/fluxes'.format(mapping['sample'].id),
            '/samples/{}/phases'.format(mapping['sample'].id),
        ]

    def test_request(self):
        for url in self.get_urls(self.public):
            r = requests.get(self.api + url, headers={
                'Authorization': 'Bearer {}'.format(Default.ILOOP_TOKEN)
            })
            r.raise_for_status()
