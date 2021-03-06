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

import asyncio
from collections import namedtuple
from itertools import groupby

import aiohttp_cors
from aiohttp import web
from venom.rpc import Service, Venom
from venom.rpc.comms.aiohttp import create_app
from venom.rpc.method import http
from venom.rpc.reflect.service import ReflectService

from iloop_to_model import iloop_client, logger
from iloop_to_model.iloop_to_model import (
    ILOOP_SPECIES_TO_TAXON, fluxes_for_phase, gather_for_phases, info_for_samples, model_for_phase,
    model_options_for_samples, phases_for_samples, scalars_by_phases, theoretical_maximum_yield_for_phase)
from iloop_to_model.middleware import raven_middleware
from iloop_to_model.settings import Default
from iloop_to_model.stubs import (
    CurrentOrganismsMessage, ExperimentMessage, ExperimentsMessage, ExperimentsRequestMessage, JSONValue,
    MaximumYieldMessage, MaximumYieldsMessage, MeasurementMessage, MetaboliteMediumMessage, MetabolitePhasePlaneMessage,
    ModelMessage, ModelRequestMessage, ModelsMessage, OrganismToTaxonMessage, PhaseMessage, PhasePlaneMessage,
    PhasePlanesMessage, PhasesMessage, SampleInfoMessage, SampleMessage, SampleModelsMessage, SamplesInfoMessage,
    SamplesMessage, SamplesRequestMessage)


NamedSample = namedtuple('NamedSample', 'pool medium feed_medium operation')


def iloop_from_context(context):
    headers = context.request.headers
    api, token = Default.ILOOP_API, Default.ILOOP_TOKEN
    if 'Authorization' in headers:
        token = headers['Authorization'].replace('Bearer ', '')
    return iloop_client(api, token)


async def sample_in_phases_venom(request, iloop, function_for_phase):
    samples = [iloop.Sample(s) for s in request.sample_ids]

    async def for_phase(s):
        scalars = scalars_by_phases(s)
        return await function_for_phase(s, scalars[request.phase_id])

    async def for_samples(s):
        return await gather_for_phases(s, function_for_phase)

    if request.phase_id:
        return {request.phase_id: await for_phase(samples)}
    return await for_samples(samples)


class SpeciesService(Service):
    class Meta:
        name = 'iloop-to-model/species'

    @http.GET('.', description='Organism short codes to taxons')
    async def species(self) -> OrganismToTaxonMessage:
        return OrganismToTaxonMessage(ILOOP_SPECIES_TO_TAXON)

    @http.GET('./current', description='Get map of taxon mnemonic code to name for current strains')
    async def current_species(self) -> CurrentOrganismsMessage:
        iloop = iloop_from_context(self.context)
        return CurrentOrganismsMessage(
            dict((ILOOP_SPECIES_TO_TAXON[o.short_code], o.name)
                 for o in iloop.Organism.instances() if o.short_code in Default.ORGANISMS_WITH_MAPS))


def group_id(sample):
    """Unique identifier for the sample using its properties"""
    return NamedSample(
        pool=sample.strain.pool.id,
        medium=sample.medium.id,
        feed_medium=getattr(sample.feed_medium, 'id', 0),
        operation=sample.operation
    )


def name_groups(grouped_samples, unique_keys, names):
    """Generate a name for the group of samples, using the distinctive properties.

    Example: for samples with following property identifiers
    A, B, C
    A, B, D
    F, B, D
    resulting names would be
    A, C
    A, D
    F, D

    :param grouped_samples: iterables of samples
    :param unique_keys: a unique key for every group from grouped_samples
    :param names: corresponding names for ids from unique_keys
    :return:
    """
    result = []
    if not unique_keys:
        return result
    rs = [set() for _ in unique_keys[0]]
    for unique_key in unique_keys:
        for j, k in enumerate(unique_key):
            rs[j].add(k)
    indexes = [j for j, v in enumerate(rs) if len(v) != 1]
    if len(indexes) == 0:
        indexes = [0, 3]
    for i, group in enumerate(grouped_samples):
        result.append(SampleMessage(
            id=[s.id for s in group],
            name=', '.join([names[i][j] for j in indexes]),
            organism=group[0].strain.organism.short_code
        ))
    return result


class ExperimentsService(Service):
    class Meta:
        name = 'iloop-to-model/experiments'

    @http.GET('.', description='List of experiments')
    async def experiments(self) -> ExperimentsMessage:
        iloop = iloop_from_context(self.context)
        experiments = iloop.Experiment.instances(where=dict(type='fermentation'))
        return ExperimentsMessage([ExperimentMessage(id=experiment.id, name=experiment.identifier)
                                   for experiment in experiments])

    @http.GET('./{taxon_code}', description='List of experiments involving given species')
    async def experiments_for_species(self, request: ExperimentsRequestMessage) -> ExperimentsMessage:
        iloop = iloop_from_context(self.context)
        experiments = [e for e in iloop.Experiment.instances(where=dict(type='fermentation')) if
                       request.taxon_code in {ILOOP_SPECIES_TO_TAXON[s.strain.organism.short_code] for s in
                       e.read_samples()}]
        return ExperimentsMessage([ExperimentMessage(id=experiment.id, name=experiment.identifier)
                                   for experiment in experiments])

    @http.GET('./{experiment_id}/samples', description='List of samples for the given experiment')
    async def list_samples(self, request: SamplesRequestMessage) -> SamplesMessage:
        iloop = iloop_from_context(self.context)
        experiment = iloop.Experiment(request.experiment_id)
        samples = list(experiment.read_samples())
        operation = experiment.attributes['operation'] or {}
        for s in samples:
            s.operation = s.name
        for k, v in operation.items():
            for s in samples:
                if s.name == k:
                    s.operation = v
        grouped_samples = []
        unique_keys = []
        names = []
        data = sorted(experiment.read_samples(), key=group_id)
        for k, g in groupby(data, group_id):
            grouped_samples.append(list(g))
            unique_keys.append(k)
        for key in unique_keys:
            names.append((
                iloop.Pool(key.pool).identifier,
                iloop.Medium(key.medium).name,
                '' if key.feed_medium == 0 else iloop.Medium(key.feed_medium).name,
                key.operation,
            ))
        return SamplesMessage(name_groups(grouped_samples, unique_keys, names))


def merge_duplicated_metabolites(medium):
    result = []
    added = set()
    for m in medium:
        if m['id'] not in added:
            result.append(m)
            added.add(m['id'])
    return result


class SamplesService(Service):
    class Meta:
        name = 'iloop-to-model/samples'

    @http.POST('./phases', description='Phases for the given list of samples')
    async def list_phases(self, request: ModelRequestMessage) -> PhasesMessage:
        iloop = iloop_from_context(self.context)
        samples = [iloop.Sample(s) for s in request.sample_ids]
        return PhasesMessage([PhaseMessage(**d) for d in await phases_for_samples(samples)])

    @http.POST('./info',
               description='Information about measurements, medium and genotype changes for the given list of samples')
    async def sample_info(self, request: ModelRequestMessage) -> SamplesInfoMessage:
        iloop = iloop_from_context(self.context)
        result = await sample_in_phases_venom(request, iloop, info_for_samples)
        return SamplesInfoMessage(response={k: SampleInfoMessage(
            genotype_changes=v['genotype-changes'],
            measurements=[MeasurementMessage(**i) for i in v['measurements']],
            medium=[MetaboliteMediumMessage(**i) for i in merge_duplicated_metabolites(v['medium'])],
        ) for k, v in result.items()})

    @http.POST('./model-options',
               description='Information about measurements, medium and genotype changes for the given list of samples')
    async def sample_model_options(self, request: ModelRequestMessage) -> SampleModelsMessage:
        iloop = iloop_from_context(self.context)
        sample = iloop.Sample(request.sample_ids[0])
        result = await model_options_for_samples(sample)
        return SampleModelsMessage(response=result)


class DataAdjustedService(Service):
    class Meta:
        name = 'iloop-to-model/data-adjusted'

    @http.POST('./maximum-yield', description='Calculate maximum yield for given model and sample list')
    async def sample_maximum_yields(self, request: ModelRequestMessage) -> MaximumYieldsMessage:
        iloop = iloop_from_context(self.context)
        model_id = request.model_id or None
        result = await sample_in_phases_venom(request, iloop,
                                              lambda samples, scalars: theoretical_maximum_yield_for_phase(
                                                  samples, scalars,
                                                  model_id))
        return MaximumYieldsMessage(
            response={k: MaximumYieldMessage(
                growth_rate=v['growth-rate'],
                metabolites={i: MetabolitePhasePlaneMessage(
                    flux=j['flux'],
                    phase_planes=PhasePlanesMessage(
                        wild=PhasePlaneMessage(**j['phase-planes']['wild']),
                        modified=PhasePlaneMessage(**j['phase-planes']['modified']),
                    )
                ) for i, j in v['metabolites'].items()}
            ) for k, v in result.items()}
        )

    @http.POST('./fluxes', description='Calculate fluxes for given model, sample list, simulation method and map')
    async def sample_fluxes(self, request: ModelRequestMessage) -> ModelsMessage:
        iloop = iloop_from_context(self.context)
        result = await sample_in_phases_venom(
            request, iloop,
            lambda samples, scalars: fluxes_for_phase(
                samples, scalars,
                method=request.method,
                map=request.map,
                model_id=request.model_id,
                objective=request.objective
            )
        )
        return ModelsMessage(response={k: ModelMessage(**v) for k, v in result.items()})

    @http.POST('./model', description='Return adjusted models for given model, '
                                      'sample list, simulation method and map. '
                                      'Fluxes information can be added')
    async def sample_model(self, request: ModelRequestMessage) -> ModelsMessage:
        iloop = iloop_from_context(self.context)
        result = await sample_in_phases_venom(request, iloop,
                                              lambda samples, scalars: model_for_phase(
                                                  samples, scalars,
                                                  with_fluxes=request.with_fluxes,
                                                  method=request.method, map=request.map,
                                                  model_id=request.model_id, objective=request.objective))
        return ModelsMessage(response={k: ModelMessage(
            model=JSONValue(v['model']),
            model_id=v['model_id'],
            growth_rate=v['growth-rate'],
            fluxes=v.get('fluxes')
        ) for k, v in result.items()})


def get_app():
    venom = Venom(version='0.1.0', title='ILoop To Model')
    venom.add(SpeciesService)
    venom.add(ExperimentsService)
    venom.add(SamplesService)
    venom.add(DataAdjustedService)
    venom.add(ReflectService)
    app = create_app(venom, web.Application(middlewares=[raven_middleware]))
    # Configure default CORS settings.
    cors = aiohttp_cors.setup(app, defaults={
        "*": aiohttp_cors.ResourceOptions(
            expose_headers="*",
            allow_headers="*",
            allow_credentials=True,
        )
    })

    # Configure CORS on all routes.
    for route in list(app.router.routes()):
        cors.add(route)
    return app


async def start(loop):
    app = get_app()
    await loop.create_server(app.make_handler(), '0.0.0.0', 7000)
    logger.info('Web server is up')


if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(start(loop))
    try:
        loop.run_forever()
    except KeyboardInterrupt:
        pass
