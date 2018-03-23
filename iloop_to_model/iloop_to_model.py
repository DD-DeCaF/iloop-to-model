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
import json
from collections import defaultdict
from copy import deepcopy
from itertools import chain

import aiohttp

from iloop_to_model import logger
from iloop_to_model.settings import Default


def pool_lineage(pool):
    lineage = [pool]
    while pool.parent_pool is not None:
        pool = pool.parent_pool
        lineage.insert(0, pool)
    return lineage


def strain_lineage(strain):
    lineage = [strain]
    pool_lineage_for_strain = pool_lineage(strain.pool)
    while strain.parent_strain is not None:
        strain = strain.parent_strain
        lineage.insert(0, strain)
    return pool_lineage_for_strain + lineage


def extract_genotype_changes(strain):
    """Get list of strings containing information about Genotype changes in Gnomic definition language
    :param strain: iLoop strain object
    :return: list of strings
    """
    return list(strain.genotype for strain in strain_lineage(strain) if strain.genotype)


def extract_medium(medium):
    """
    Convert Medium to simplified dictionary

    :param medium: ILoop medium object
    :return: list of dictionaries of format
            {'id': <compound id (<database>:<id>, f.e. chebi:12345)>, 'concentration': <compound concentration (float)>}
    """
    if medium is None:
        return []
    else:
        return [{
            'id': 'chebi:' + str(compound['compound'].chebi_id),
            'name': compound['compound'].chebi_name,
            'concentration': compound['concentration']
        } for compound in medium.read_contents()]


def compound_ids_str(compounds):
    return '_'.join(sorted(str(c.chebi_id) for c in compounds))


def div_key(div):
    if div is None:
        return ''
    return '{}_{}_{}_{}'.format(div['compartment'], compound_ids_str(div['compounds']), div['quantity'], div['unit'])


def scalar_test_key(scalar):
    """Generate a string representation of the test conducted for a given scalar.

    :param scalar: a iloop scalar object
    :return: a string representation of the associated test, useful for grouping scalars based on the
             measurement.
    """
    test = scalar['test']
    return '{}_{}_{}_{}'.format(div_key(test['denominator']), div_key(test['numerator']), test['rate'], test['type'])


def scalars_by_phases(samples):
    """Get scalars grouped by phases among samples

    :param samples: list of ILoop sample objects that together make up a valid sample group (replicates)
    :return: a dictionary with phase identifiers as keys, and as values, dictionaries grouping all scalars from the
    same test across the different samples.
    """
    phases = defaultdict(lambda: defaultdict(list))
    for s in samples:
        for scalar in s.read_scalars():
            scalar['type'] = 'compound'
            phases[scalar['phase'].id][scalar_test_key(scalar)].append(scalar)
        if hasattr(s, 'read_xref_measurements'):
            for subject_type in {'protein', 'reaction'}:
                for xref in s.read_xref_measurements(type=subject_type):
                    xref['type'] = subject_type
                    phases[xref['phase'].id]['{}_{}'.format(subject_type, xref['accession'])].append(xref)
    return phases


def phase_name(phase):
    return '{} ({} - {} hours)'.format(phase.title, phase.start, phase.end)


async def phases_for_samples(samples):
    scalars = scalars_by_phases(samples)
    return [dict(id=k, name=phase_name(v[list(v)[0]][0]['phase'])) for k, v in scalars.items()]


# TODO: make use of other types of scalars (yield, carbon yield, concentration, carbon balance, electron balance)
def extract_measurements_for_phase(scalars_for_samples):
    """Convert scalars to simplified dictionary. Returns only uptake and production rates.

    :param scalars_for_samples: dictionary with lists of replicated scalars across samples
    :return: list of dictionaries of format
             {'id': <metabolite id (<database>:<id>, f.e. chebi:12345)>, 'measurement': <measurement (float)>}
    """
    result = []
    for _, scalars in scalars_for_samples.items():
        scalar_type = scalars[0]['type']
        if scalar_type == 'compound':
            test = scalars[0]['test']
            if test['type'] in {'uptake-rate', 'production-rate'} and test['numerator']['compounds']:
                measurements = list(chain(*[s['measurements'] for s in scalars]))
                sign = -1 if test['type'] == 'uptake-rate' else 1
                product = test['numerator']['compounds'][0]
                result.append(dict(
                    id='chebi:' + str(product.chebi_id),
                    name=product.chebi_name,
                    measurements=[m * sign for m in measurements],
                    units={
                        'numerator': test['numerator']['unit'],
                        'denominator': test['denominator']['unit'],
                    },
                    rate=test['rate'],
                    type=scalar_type
                ))
            elif test['type'] == 'growth-rate':
                result.append({
                    'name': 'growth rate',
                    'measurements': list(chain(*[s['measurements'] for s in scalars])),
                    'units': {
                        'numerator': test['numerator']['unit'] if test['numerator'] else None,
                        'denominator': test['denominator']['unit'] if test['denominator'] else None,
                    },
                    'rate': test['rate'],
                    'type': 'growth-rate',
                })
        elif scalar_type in {'protein', 'reaction'}:
            result.append(dict(
                type=scalar_type,
                id=scalars[0]['accession'],
                name=scalars[0]['accession'],
                db_name=scalars[0]['db_name'],
                mode=scalars[0]['mode'],
                measurements=[s['value'] for s in scalars],
                units={
                    'numerator': 'mmol',
                    'denominator': 'g',
                },
                rate='h'
            ))
    return result


GENOTYPE_CHANGES = 'genotype-changes'
MEDIUM = 'medium'
MEASUREMENTS = 'measurements'
OBJECTIVE = 'objective'
REACTIONS = 'reactions-knockout'
MODEL = 'model'
GROWTH_RATE = 'growth-rate'
FLUXES = 'fluxes'
TMY = 'tmy'
OBJECTIVES = 'theoretical-objectives'


def sample_model_id(sample):
    return Default.ORGANISM_TO_MODEL[sample.strain.organism.short_code]


# TODO: clear definition of how to add oxygen to experimental conditions
def is_aerobic(sample):
    return 'oxygen' in sample.experiment.attributes.get('conditions', {}).get('gas', '')


def add_dioxygen_to_medium(medium):
    medium.append({'id': 'chebi:10745', 'name': 'dioxygen'})


def message_for_adjust(samples, scalars=None, objective=None):
    """Extract information about genotype changes, medium definitions and measurements if scalars are given
    If no phase is given, do not add measurements.

    :param samples: list of ILoop sample object that make up a group of replicates, of same genotype, same medium.
    :param scalars: scalars for particular phase
    :return: dict
    """
    sample = samples[0]
    genotype_changes = extract_genotype_changes(sample.strain)
    sample_names = ','.join(s.name for s in samples)
    logger.info('Genotype changes for sample {} are ready'.format(sample_names))
    medium = extract_medium(sample.medium) + extract_medium(sample.feed_medium)
    if is_aerobic(sample):
        add_dioxygen_to_medium(medium)
    logger.info('Medium for sample {} are ready'.format(sample_names))
    measurements = extract_measurements_for_phase(scalars) if scalars else []
    logger.info('Measurements for sample {} are ready'.format(sample_names))
    message = {
        GENOTYPE_CHANGES: genotype_changes,
        MEDIUM: medium,
        MEASUREMENTS: measurements,
    }
    if objective:
        message[OBJECTIVE] = objective
    return message


ILOOP_SPECIES_TO_TAXON = {
    'ECO': 'ECOLX',
    'SCE': 'YEAST',
    'CHO': 'CRIGR',
    'PPU': 'PSEPU',
    'COG': 'CORGT'
}


async def model_options_for_samples(sample):
    """Get the possible models for a given species.

    :param sample: ILoop sample object
    """
    species = ILOOP_SPECIES_TO_TAXON[sample.strain.organism.short_code]
    url = '{}/model-options/{}'.format(Default.MODEL_API, species)
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as r:
            assert r.status == 200, f'response status {r.status} from model service'
            return await r.json()


async def make_request(model_id, message):
    """Make asynchronous call to model service

    :param model_id: str
    :param message: dict
    :return: response for the service as dict
    """
    async with aiohttp.ClientSession(headers={'Content-Type': 'application/json'}) as session:
        async with session.post(
                '{}/models/{}'.format(Default.MODEL_API, model_id),
                data=json.dumps({'message': message})
        ) as r:
            assert r.status == 200, f'response status {r.status} from model service'
            return await r.json()


async def _call_with_return(model_id, adjust_message, return_message):
    """Helper function for calling model service

    :param model_id: str
    :param adjust_message: dict
    :param return_message: dict
    :return: dict
    """
    message = deepcopy(adjust_message)
    message.update(return_message)
    call_result = await make_request(model_id, message)
    result = {
        'model_id': call_result['model-id'],
    }
    for key in return_message['to-return']:
        result[key] = call_result[key]
    return result


async def fluxes(model_id, adjust_message, method=None, map=None):
    """Get fluxes for given model id and adjustment message

    :param model_id: str
    :param adjust_message: dict
    :param method: the simulation method to use, e.g fba
    :param map: the pathway map to extract fluxes for (limit the reactions)
    :return: fluxes as dict
    """
    return_message = {
        'to-return': [FLUXES]
    }
    if method:
        return_message['simulation-method'] = method
    if map:
        return_message['map'] = map
    return await _call_with_return(model_id, adjust_message, return_message)


async def gather_for_phases(samples, function):
    phase_items = list(scalars_by_phases(samples).items())
    result = await asyncio.gather(*[function(samples, scalars)
                                    for phase, scalars in phase_items])
    phases = [p for p, _ in phase_items]
    return dict(zip(phases, result))


async def fluxes_for_phase(samples, scalars, method=None, map=None, model_id=None, objective=None):
    if model_id is None:
        model_id = sample_model_id(samples[0])
    return await fluxes(model_id, message_for_adjust(samples, scalars, objective), method=method, map=map)


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
    return await _call_with_return(model_id, adjust_message, return_message)


def tmy_to_dict(data):
    # TODO: replace with compatible message from the model service
    if not data:
        return data
    u, l = 'objective_upper_bound', 'objective_lower_bound'
    o = list(set(data.keys()) - {u, l})[0]
    return dict(
        objective_upper_bound=data[u],
        objective_lower_bound=data[l],
        objective=data[o],
        objective_id=o,
    )


async def theoretical_maximum_yield_for_phase(samples, scalars, model_id=None):
    """Get theoretical maximum yields for phase scalars, with growth rates and measurements, both for modified and wild type

    :param samples: list of ILoop sample objects that make up a valid sample group (replicates)
    :param scalars: scalars from ILoop
    :param model_id: The model to use, e.g. iJO1366
    :return: dict
    """
    if model_id is None:
        model_id = sample_model_id(samples[0])
    growth_rate_scalars = [sc for _, sc in scalars.items() if sc[0].get('test', {}).get('type', '') == 'growth-rate']
    # should get no growth rate or one list of measurements
    if len(growth_rate_scalars) == 1:
        growth_rate = dict(measurements=list(chain(*[s['measurements'] for s in growth_rate_scalars[0]])))
    elif len(growth_rate_scalars) == 0:
        growth_rate = dict(measurements=[0])
    else:
        raise RuntimeError('unexpected number of measured growth rates for sample group')
    measurements = extract_measurements_for_phase(scalars)
    compound_measurements = [m for m in measurements if m['type'] == 'compound']
    compound_ids = [m['id'] for m in compound_measurements]
    tmy_modified, tmy_wild_type = await asyncio.gather(*[
        tmy(model_id, message_for_adjust(samples, scalars), compound_ids),
        tmy(model_id, {}, compound_ids)
    ])
    result = {
        'growth-rate': growth_rate['measurements'],
        'metabolites': {}
    }
    for compound in compound_measurements:
        result['metabolites'][compound['name']] = {
            'flux': compound['measurements'],
            'phase-planes': {
                'modified': tmy_to_dict(tmy_modified['tmy'][compound['id']]),
                'wild': tmy_to_dict(tmy_wild_type['tmy'][compound['id']]),
            }
        }
    return result


async def model_json(model_id, adjust_message, with_fluxes=True, method=None, map=None):
    """Get serialized model for given model id and adjustment message. Also returns fluxes by default

    :param model_id: str
    :param adjust_message: dict
    :param with_fluxes: bool
    :param method: string indicating the flux balance analysis simulation method, e.g. pfba or fba
    :return: model as dict
    """
    return_message = {
        'to-return': [MODEL, FLUXES, GROWTH_RATE] if with_fluxes else [MODEL, GROWTH_RATE],
    }
    if method:
        return_message['simulation-method'] = method
    if map:
        return_message['map'] = map
    return await _call_with_return(model_id, adjust_message, return_message)


async def model_for_phase(samples, scalars, with_fluxes=True, method=None, map=None, model_id=None, objective=None):
    if model_id is None:
        model_id = sample_model_id(samples[0])
    return await model_json(model_id, message_for_adjust(samples, scalars, objective), with_fluxes=with_fluxes, method=method,
                            map=map)


async def info_for_samples(samples, scalars):
    return message_for_adjust(samples, scalars)
