import json
import asyncio
import aiohttp_cors
from aiohttp import web
from iloop_to_model import iloop_client, logger
from iloop_to_model.settings import Default
from iloop_to_model.iloop_to_model import gather_for_phases, scalars_by_phases, \
    fluxes_for_phase, model_for_phase, theoretical_maximum_yield_for_phase, phases_for_sample, info_for_sample


iloop = iloop_client(Default.ILOOP_API, Default.ILOOP_TOKEN)


def is_public(entity):
    if isinstance(entity, iloop.Sample):
        entity = entity.experiment
    return entity.project.code not in Default.NOT_PUBLIC


def entity_or_none(entity):
    return entity if is_public(entity) else None


async def response_or_forbidden(entity, get_result, dumps=json.dumps):
    if entity:
        return web.json_response(await get_result(entity), dumps=dumps)
    else:
        return web.HTTPForbidden()


async def list_experiments(request):
    experiments = iloop.Experiment.instances(where=dict(type='fermentation'))
    return web.json_response([dict(id=experiment.id, name=experiment.identifier) for experiment in experiments
                              if is_public(experiment)])


async def list_samples(request):
    experiment = entity_or_none(iloop.Experiment(request.match_info['experiment_id']))
    if experiment:
        return web.json_response([dict(id=sample.id, name=sample.name) for sample in experiment.read_samples()])
    else:
        return web.HTTPForbidden()


async def list_phases(request):
    sample = entity_or_none(iloop.Sample(request.match_info['sample_id']))
    return await response_or_forbidden(sample, phases_for_sample)


async def sample_in_phases(request, function_for_phase):
    sample = entity_or_none(iloop.Sample(request.match_info['sample_id']))

    async def for_phase(s):
        scalars = scalars_by_phases(s)
        return await function_for_phase(s, scalars[int(request.GET['phase-id'])])

    async def for_sample(s):
        return await gather_for_phases(s, function_for_phase)

    if 'phase-id' in request.GET:
        return await response_or_forbidden(sample, for_phase)
    return await response_or_forbidden(sample, for_sample)


async def sample_maximum_yields(request):
    return await sample_in_phases(request, theoretical_maximum_yield_for_phase)


async def sample_model(request):
    with_fluxes = 'with-fluxes' in request.GET and request.GET['with-fluxes'] == '1'
    return await sample_in_phases(request, lambda x, y: model_for_phase(x, y, with_fluxes=with_fluxes))


async def sample_fluxes(request):
    return await sample_in_phases(request, fluxes_for_phase)


async def sample_info(request):
    return await sample_in_phases(request, info_for_sample)


app = web.Application()
# List entities
app.router.add_route('GET', '/experiments', list_experiments)
app.router.add_route('GET', '/experiments/{experiment_id}/samples', list_samples)
app.router.add_route('GET', '/samples/{sample_id}/phases', list_phases)
# Make calculations
app.router.add_route('GET', '/samples/{sample_id}/maximum-yield', sample_maximum_yields)
app.router.add_route('GET', '/samples/{sample_id}/model', sample_model)
app.router.add_route('GET', '/samples/{sample_id}/fluxes', sample_fluxes)
app.router.add_route('GET', '/samples/{sample_id}/info', sample_info)


# Configure default CORS settings.
cors = aiohttp_cors.setup(app, defaults={
    "*": aiohttp_cors.ResourceOptions(
        allow_credentials=True,
        expose_headers="*",
        allow_headers="*",
    )
})

# Configure CORS on all routes.
for route in list(app.router.routes()):
    cors.add(route)


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
