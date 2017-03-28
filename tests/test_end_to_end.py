import requests
from iloop_to_model import iloop_client
from iloop_to_model.settings import Default


class TestUM:
    def setup(self):
        self.api = 'http://localhost:7000'
        self.iloop = iloop_client(Default.ILOOP_API, Default.ILOOP_TOKEN)
        self.experiment = self.iloop.Experiment.instances(where={'type': 'fermentation'})[0]
        self.sample = self.experiment.read_samples()[0]
        self.model = {'ECO': 'iJO1366', 'SCE': 'iMM904'}[self.sample.strain.organism.short_code]

    def test_request(self):
        URLS = [
            '/samples/{}/maximum-yield?model-id={}'.format(self.sample.id, self.model),
            '/samples/{}/maximum-yield'.format(self.sample.id),
            '/samples/{}/model?phase-id=1&with-fluxes=1&method=room'.format(self.sample.id),
            '/samples/{}/fluxes'.format(self.sample.id),
            '/samples/{}/phases'.format(self.sample.id),
            '/samples/{}/model-options'.format(self.sample.id),
        ]
        for url in URLS:
            r = requests.get(self.api + url)
            r.raise_for_status()
