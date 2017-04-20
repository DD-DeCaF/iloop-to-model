from collections import namedtuple

import pytest

from iloop_to_model.iloop_to_model import (
    MEASUREMENTS, MEDIUM, extract_genotype_changes, message_for_adjust, phases_for_samples, scalars_by_phases)

Sample = namedtuple('Sample', ['strain', 'medium', 'feed_medium', 'read_scalars', 'name'])
Strain = namedtuple('Strain', ['organism', 'parent_strain', 'pool', 'parent_pool', 'genotype'])
Medium = namedtuple('Medium', ['read_contents'])
Product = namedtuple('Product', ['chebi_id', 'chebi_name'])
Phase = namedtuple('Phase', ['id', 'title', 'start', 'end'])
Organism = namedtuple('Organism', ['short_code'])
Pool = namedtuple('Pool', ['parent_pool', 'genotype'])

organism = Organism('ECO')
p1 = Product(16828, 'first')
p2 = Product(17895, 'second')
medium = Medium(lambda: [{'compound': p1, 'concentration': 0.01}, {'compound': p2, 'concentration': 0.02}])
phase = Phase(1, 'phase1', 0, 14)
pool = Pool(None, '+pool_gene')
strain = Strain(organism, None, pool, None, '+Aac')
scalars = [{'measurements': [0.0, 0.0],
            'phase': phase,
            'test': {'denominator': {'compartment': None,
                                     'compounds': [],
                                     'quantity': 'CDW',
                                     'unit': 'g'},
                     'numerator': {'compartment': None,
                                   'compounds': [p1],
                                   'quantity': 'amount',
                                   'unit': 'mmol'},
                     'rate': 'h',
                     'type': 'production-rate'}},
           {'measurements': [5.0, 2.8],
            'phase': phase,
            'test': {'denominator': {'compartment': None,
                                     'compounds': [],
                                     'quantity': 'CDW',
                                     'unit': 'g'},
                     'numerator': {'compartment': None,
                                   'compounds': [p2],
                                   'quantity': 'amount',
                                   'unit': 'mg'},
                     'rate': 'h',
                     'type': 'uptake-rate'}}]

s1 = Sample(strain, medium, medium, lambda: scalars, 'S1')
s2 = Sample(strain, medium, medium, lambda: scalars, 'S2')
samples_args = [[s1], [s1, s2]]


@pytest.mark.parametrize('samples', samples_args)
def test_message_for_adjust(samples):
    message = message_for_adjust(samples)
    assert message[MEASUREMENTS] == []
    grouped_scalars_phase1 = scalars_by_phases(samples)[1]
    message = message_for_adjust(samples, grouped_scalars_phase1)
    assert len(message[MEASUREMENTS]) == 2
    assert len(message[MEDIUM]) == 4
    assert extract_genotype_changes(strain) == ['+pool_gene', '+Aac']


@pytest.mark.asyncio
@pytest.mark.parametrize('samples', samples_args)
async def test_phases_for_sample(samples):
    assert await phases_for_samples(samples) == [{'id': 1, 'name': 'phase1 (0 - 14 hours)'}]
