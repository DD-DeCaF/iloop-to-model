import asyncio
import aiohttp_cors
from aiohttp import web
from functools import wraps
from iloop_to_model import iloop_client, logger
from iloop_to_model.settings import Default
from iloop_to_model.iloop_to_model import gather_for_phases, scalars_by_phases, \
    fluxes_for_phase, model_for_phase, theoretical_maximum_yield_for_phase, phases_for_sample, info_for_sample


def call_iloop_with_token(f):
    @wraps(f)
    async def wrapper(request):
        api, token = Default.ILOOP_API, Default.ILOOP_TOKEN
        if 'Authorization' in request.headers:
            if 'Origin' in request.headers and 'cfb' in request.headers['Origin']:
                api = Default.ILOOP_BIOSUSTAIN
            token = request.headers['Authorization'].replace('Bearer ', '')
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
    return web.json_response([dict(
        id=sample.id,
        name=sample.name,
        organism=sample.strain.organism.short_code
    ) for sample in experiment.read_samples()])


@call_iloop_with_token
async def list_phases(request, iloop):
    sample = iloop.Sample(request.match_info['sample_id'])
    return web.json_response(await phases_for_sample(sample))


async def sample_in_phases(request, iloop, function_for_phase):
    sample = iloop.Sample(request.match_info['sample_id'])

    async def for_phase(s):
        scalars = scalars_by_phases(s)
        return await function_for_phase(s, scalars[int(request.GET['phase-id'])])

    async def for_sample(s):
        return await gather_for_phases(s, function_for_phase)

    if 'phase-id' in request.GET:
        return web.json_response(await for_phase(sample))
    return web.json_response(await for_sample(sample))


@call_iloop_with_token
async def sample_maximum_yields(request, iloop):
    return await sample_in_phases(request, iloop, theoretical_maximum_yield_for_phase)


@call_iloop_with_token
async def sample_model(request, iloop):
    with_fluxes = 'with-fluxes' in request.GET and request.GET['with-fluxes'] == '1'
    method = request.GET['method'] if 'method' in request.GET else None
    return await sample_in_phases(request, iloop, lambda x, y: model_for_phase(x, y, with_fluxes=with_fluxes, method=method))


@call_iloop_with_token
async def sample_fluxes(request, iloop):
    method = request.GET['method'] if 'method' in request.GET else None
    return await sample_in_phases(request, iloop, lambda x, y: fluxes_for_phase(x, y, method=method))


@call_iloop_with_token
async def sample_info(request, iloop):
    return await sample_in_phases(request, iloop, info_for_sample)


ROUTE_CONFIG = {
    '/species': list_species,
    '/experiments': list_experiments,
    '/experiments/{experiment_id}/samples': list_samples,
    '/samples/{sample_id}/phases': list_phases,
    '/samples/{sample_id}/maximum-yield': sample_maximum_yields,
    '/samples/{sample_id}/model': sample_model,
    '/samples/{sample_id}/fluxes': sample_fluxes,
    '/samples/{sample_id}/info': sample_info
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
