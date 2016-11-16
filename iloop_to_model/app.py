import json
import asyncio
import aiohttp_cors
from aiohttp import web
from iloop_to_model import iloop_client, logger
from iloop_to_model.settings import Default
from iloop_to_model.iloop_to_model import theoretical_maximum_yields_for_sample, fluxes_for_sample, model_for_sample, phases_for_sample


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


async def sample_maximum_yields(request):
    sample = entity_or_none(iloop.Sample(request.match_info['sample_id']))
    return await response_or_forbidden(sample, theoretical_maximum_yields_for_sample)


async def experiment_maximum_yields(request):
    experiment = entity_or_none(iloop.Experiment(request.match_info['experiment_id']))

    async def samples_for_experiment(e):
        keys = [s.id for s in e.read_samples()]
        values = await asyncio.gather(*[theoretical_maximum_yields_for_sample(sample) for sample in e.read_samples()])
        return dict(zip(keys, values))

    return await response_or_forbidden(experiment, samples_for_experiment)


async def sample_model(request):
    strain = entity_or_none(iloop.Sample(request.match_info['sample_id']))
    return await response_or_forbidden(strain, model_for_sample)


async def sample_fluxes(request):
    strain = entity_or_none(iloop.Sample(request.match_info['sample_id']))
    return await response_or_forbidden(strain, fluxes_for_sample)


app = web.Application()
app.router.add_route('GET', '/experiments', list_experiments)
app.router.add_route('GET', '/experiments/{experiment_id}/samples', list_samples)
app.router.add_route('GET', '/experiments/{experiment_id}/strains', list_samples)  # TODO: deprecate
app.router.add_route('GET', '/samples/{sample_id}/phases', list_phases)
app.router.add_route('GET', '/samples/{sample_id}/maximum-yield', sample_maximum_yields)
app.router.add_route('GET', '/experiments/{experiment_id}/maximum-yield', experiment_maximum_yields)
app.router.add_route('GET', '/samples/{sample_id}/model', sample_model)
app.router.add_route('GET', '/strains/{sample_id}/model', sample_model)  # TODO: deprecate
app.router.add_route('GET', '/samples/{sample_id}/model/fluxes', sample_fluxes)
app.router.add_route('GET', '/strains/{sample_id}/model/fluxes', sample_fluxes)  # TODO: deprecate


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
