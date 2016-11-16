import json
from collections import defaultdict
from copy import deepcopy
import aiohttp
import asyncio
from iloop_to_model.settings import Default
from iloop_to_model import logger


def genotype_change(strain):
    return strain.genotype if strain.genotype else strain.pool.genotype


def extract_genotype_changes(strain):
    """Get list of strings containing information about Genotype changes in Gnomic definition language
    :param strain: iLoop strain object
    :return: list of strings
    """
    def inner(strain):
        lineage = [strain]
        while strain.parent_strain is not None:
            strain = strain.parent_strain
            lineage.insert(0, strain)
        return lineage

    return list(genotype_change(strain) for strain in inner(strain) if genotype_change(strain))


def extract_medium(medium):
    """
    Convert Medium to simplified dictionary

    :param medium: ILoop medium object
    :return: list of dictionaries of format
            {'id': <compound id (<database>:<id>, f.e. chebi:12345)>, 'concentration': <compound concentration (float)>}
    """
    return [{
                'id': 'chebi:' + str(compound['compound'].chebi_id),
                'concentration': compound['concentration']
            } for compound in medium.read_contents()]


def scalars_by_phases(sample):
    """Get scalars grouped by phases in the sample

    :param sample: ILoop sample object
    :return: dict
    """
    phases = defaultdict(lambda: [])
    for scalar in sample.read_scalars():
        phases[scalar['phase'].id].append(scalar)
    return phases


def phase_name(phase):
    return '{} ({} - {} hours)'.format(phase.title, phase.start, phase.end)


async def phases_for_sample(sample):
    return [dict(id=k, name=phase_name(v[0]['phase'])) for k, v in scalars_by_phases(sample).items()]


# TODO: make use of other types of scalars (yield, carbon yield, concentration, carbon balance, electron balance)
def extract_measurements_for_phase(scalars):
    """Convert scalars to simplified dictionary. Returns only uptake and production rates.

    :param sample: scalars dictionary
    :return: list of dictionaries of format
             {'id': <metabolite id (<database>:<id>, f.e. chebi:12345)>, 'measurement': <measurement (float)>}
    """
    scalars_yield = filter(
        lambda x: (x['test']['type'] in {'uptake-rate', 'production-rate'} and x['test']['numerator']['compounds']),
        scalars
    )
    result = []
    for scalar in scalars_yield:
        measurement = sum(scalar['measurements'])/len(scalar['measurements'])
        sign = -1 if scalar['test']['type'] == 'uptake-rate' else 1
        product = scalar['test']['numerator']['compounds'][0]
        result.append(dict(
            id='chebi:' + str(product.chebi_id),
            name=product.chebi_name,
            measurement=sign * measurement,
            unit=scalar['test']['numerator']['unit'],
        ))
    return result


GENOTYPE_CHANGES = 'genotype-changes'
MEDIUM = 'medium'
MEASUREMENTS = 'measurements'
REACTIONS = 'reactions-knockout'
MODEL = 'model'
FLUXES = 'fluxes'
TMY = 'tmy'
OBJECTIVES = 'objectives'


def sample_model_id(sample):
    return Default.ORGANISM_TO_MODEL[sample.strain.organism.short_code]


def message_for_adjust(sample, scalars=None):
    """Extract information about genotype changes, medium definitions and measurements if scalars are given
    If no phase is given, do not add measurements.

    :param sample: ILoop sample object
    :param scalars: scalars for particular phase
    :return: dict
    """
    genotype_changes = extract_genotype_changes(sample.strain)
    logger.info('Genotype changes for sample {} are ready'.format(sample.name))
    medium = extract_medium(sample.medium) + extract_medium(sample.feed_medium)
    logger.info('Medium for sample {} are ready'.format(sample.name))
    measurements = extract_measurements_for_phase(scalars) if scalars else []
    logger.info('Measurements for sample {} are ready'.format(sample.name))
    return {
        GENOTYPE_CHANGES: genotype_changes,
        MEDIUM: medium,
        MEASUREMENTS: measurements,
    }


async def make_request(model_id, message):
    """Make asynchronous call to model service

    :param model_id: str
    :param message: dict
    :return: response for the service as dict
    """
    async with aiohttp.ClientSession() as session:
        async with session.post(
                'http://api.dd-decaf.eu/models/{}'.format(model_id),
                data=json.dumps({'message': message})
        ) as r:
            return await r.json()


async def _call_with_return(model_id, adjust_message, return_message, key):
    """Helper function for calling model service

    :param model_id: str
    :param adjust_message: dict
    :param return_message: dict
    :param key: str
    :return: dict
    """
    message = deepcopy(adjust_message)
    message.update(return_message)
    result = await make_request(model_id, message)
    return result[key]


async def fluxes(model_id, adjust_message):
    """Get fluxes for given model id and adjustment message

    :param model_id: str
    :param adjust_message: dict
    :return: fluxes as dict
    """
    return_message = {
        'to-return': [FLUXES]
    }
    return await _call_with_return(model_id, adjust_message, return_message, FLUXES)


async def _gather_for_phases(sample, function):
    phase_items = list(scalars_by_phases(sample).items())
    result = await asyncio.gather(*[function(sample, scalars)
                                    for phase, scalars in phase_items])
    phases = [p for p, _ in phase_items]
    return dict(zip(phases, result))


async def fluxes_for_sample(sample):
    return await _gather_for_phases(sample, fluxes_for_phase)


async def fluxes_for_phase(sample, scalars):
    return await fluxes(sample_model_id(sample), message_for_adjust(sample, scalars))


async def tmy(model_id, adjust_message, objectives):
    """Get theoretical maximum yield for given model id and adjustment message

    :param model_id: str
    :param adjust_message: dict
    :param objectives: list of chebi id strings in format chebi:12345
    :return: theoretical maximum yield as dict
    """
    return_message = {
        'to-return': [TMY],
        OBJECTIVES: objectives,
    }
    return await _call_with_return(model_id, adjust_message, return_message, TMY)


async def theoretical_maximum_yields_for_sample(sample):
    """Get theoretical maximum yields for sample, with growth rates and measurements, both for modified and wild type

    :param sample: ILoop sample object
    :return: dict
    """
    return await _gather_for_phases(sample, theoretical_maximum_yield_for_phase)


async def theoretical_maximum_yield_for_phase(sample, scalars):
    """Get theoretical maximum yields for phase scalars, with growth rates and measurements, both for modified and wild type

    :param sample: ILoop sample object
    :param scalars: scalars from ILoop
    :return: dict
    """
    growth_rate = list(filter(lambda x: x['test']['type'] == 'growth-rate', scalars))[0]
    measurements = extract_measurements_for_phase(scalars)
    compound_ids = [m['id'] for m in measurements]
    model_id = sample_model_id(sample)
    tmy_modified, tmy_wild_type = await asyncio.gather(*[
        tmy(model_id, message_for_adjust(sample), compound_ids),
        tmy(model_id, {}, compound_ids)
    ])
    result = {
        'growth-rate': growth_rate['measurements'],
        'metabolites': {}
    }
    for compound in measurements:
        result['metabolites'][compound['name']] = {
            'flux': compound['measurement'],
            'phase-planes': {
                'modified': tmy_modified[compound['id']],
                'wild': tmy_wild_type[compound['id']],
            }
        }
    return result


async def model_json(model_id, adjust_message):
    """Get serialized model for given model id and adjustment message

    :param model_id: str
    :param adjust_message: dict
    :return: model as dict
    """
    return_message = {
        'to-return': [MODEL],
    }
    return await _call_with_return(model_id, adjust_message, return_message, MODEL)


async def model_for_sample(sample):
    return await model_json(sample_model_id(sample), message_for_adjust(sample))
