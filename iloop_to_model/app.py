import asyncio
import json
from collections import defaultdict
from functools import wraps

import aiohttp_cors
from aiohttp import web

from iloop_to_model import iloop_client, logger
from iloop_to_model.iloop_to_model import (
    fluxes_for_phase, gather_for_phases, info_for_samples, model_for_phase, model_options_for_samples,
    phases_for_samples, scalars_by_phases, theoretical_maximum_yield_for_phase)
from iloop_to_model.settings import Default


def call_iloop_with_token(f):
    @wraps(f)
    async def wrapper(request):
        api, token = Default.ILOOP_API, Default.ILOOP_TOKEN
        if 'Authorization' in request.headers:
            token = request.headers['Authorization'].replace('Bearer ', '')
            if 'Origin' in request.headers:
                for origin, redirect_api in Default.REDIRECTS.items():
                    if origin in request.headers['Origin']:
                        api = redirect_api
        iloop = iloop_client(api, token)
        return await f(request, iloop)

    return wrapper


@call_iloop_with_token
async def list_species(request, iloop):
    return web.json_response(Default.ORGANISM_TO_MODEL)


@call_iloop_with_token
async def list_experiments(request, iloop):
    experiments = iloop.Experiment.instances(where=dict(type='fermentation'))
    return web.json_response([dict(id=experiment.id, name=experiment.identifier) for experiment in experiments])


@call_iloop_with_token
async def list_samples(request, iloop):
    experiment = iloop.Experiment(request.match_info['experiment_id'])
    operation = experiment.attributes['operation']
    samples = experiment.read_samples()

    sample_groups = []
    added = set()
    if operation is not None:
        replicate_groups = defaultdict(list)
        for k, v in operation.items():
            replicate_groups[v].append(k)
        for name, group in replicate_groups.items():
            sample_ids_in_group = [s.id for s in samples if s.name in group]
            added |= set(sample_ids_in_group)
            sample_groups.append(
                dict(id=sample_ids_in_group, name=name, organism=samples[0].strain.organism.short_code))
    # add all samples that were not part of any group to their own lonely group
    for s in samples:
        if s.id not in added:
            sample_groups.append(dict(id=[s.id], name=s.name, organism=s.strain.organism.short_code))

    return web.json_response(sample_groups)


@call_iloop_with_token
async def list_phases(request, iloop):
    samples = [iloop.Sample(s) for s in json.loads(request.GET['sample-ids'])]
    return web.json_response(await phases_for_samples(samples))


async def sample_in_phases(request, iloop, function_for_phase):
    samples = [iloop.Sample(s) for s in json.loads(request.GET['sample-ids'])]

    async def for_phase(s):
        scalars = scalars_by_phases(s)
        return await function_for_phase(s, scalars[int(request.GET['phase-id'])])

    async def for_samples(s):
        return await gather_for_phases(s, function_for_phase)

    if 'phase-id' in request.GET:
        return web.json_response(await for_phase(samples))
    return web.json_response(await for_samples(samples))


@call_iloop_with_token
async def sample_maximum_yields(request, iloop):
    model_id = request.GET['model-id'] if 'model-id' in request.GET else None
    return await sample_in_phases(request, iloop,
                                  lambda samples, scalars: theoretical_maximum_yield_for_phase(samples, scalars,
                                                                                               model_id))


@call_iloop_with_token
async def sample_model(request, iloop):
    model_id = request.GET['model-id'] if 'model-id' in request.GET else None
    with_fluxes = 'with-fluxes' in request.GET and request.GET['with-fluxes'] == '1'
    method = request.GET['method'] if 'method' in request.GET else None
    map = request.GET['map'] if 'map' in request.GET else None
    return await sample_in_phases(request, iloop,
                                  lambda samples, scalars: model_for_phase(samples, scalars, with_fluxes=with_fluxes,
                                                                           method=method, map=map,
                                                                           model_id=model_id))


@call_iloop_with_token
async def sample_model_options(request, iloop):
    sample_ids = json.loads(request.GET['sample-ids'])
    sample = iloop.Sample(sample_ids[0])
    return web.json_response(await model_options_for_samples(sample))


@call_iloop_with_token
async def sample_fluxes(request, iloop):
    model_id = request.GET['model-id'] if 'model-id' in request.GET else None
    method = request.GET['method'] if 'method' in request.GET else None
    map = request.GET['map'] if 'map' in request.GET else None
    return await sample_in_phases(request, iloop,
                                  lambda samples, scalars: fluxes_for_phase(samples, scalars, method=method, map=map,
                                                                            model_id=model_id))


@call_iloop_with_token
async def sample_info(request, iloop):
    return await sample_in_phases(request, iloop, info_for_samples)


ROUTE_CONFIG = {
    '/species': list_species,
    '/experiments': list_experiments,
    '/experiments/{experiment_id}/samples': list_samples,
    '/samples/phases': list_phases,
    '/samples/model-options': sample_model_options,
    '/samples/info': sample_info,
    '/data-adjusted/model': sample_model,
    '/data-adjusted/fluxes': sample_fluxes,
    '/data-adjusted/maximum-yield': sample_maximum_yields
}

app = web.Application()
# Configure default CORS settings.
cors = aiohttp_cors.setup(app, defaults={
    "*": aiohttp_cors.ResourceOptions(
        expose_headers="*",
        allow_headers="*",
        allow_credentials=True,
    )
})

for path, handler in ROUTE_CONFIG.items():
    resource = app.router.add_resource(path)
    cors.add(resource)
    cors.add(resource.add_route("GET", handler))


async def start(loop):
    await loop.create_server(app.make_handler(), '0.0.0.0', 7000)
    logger.info('Web server is up')


if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(start(loop))
    try:
        loop.run_forever()
    except KeyboardInterrupt:
        pass
