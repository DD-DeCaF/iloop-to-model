from collections import namedtuple

import pytest

from iloop_to_model.iloop_to_model import (
    MEASUREMENTS, MEDIUM, extract_genotype_changes, message_for_adjust, phases_for_samples, scalars_by_phases
)
from iloop_to_model.app import name_groups

Sample = namedtuple('Sample',
                    ['id', 'strain', 'medium', 'feed_medium', 'read_scalars', 'name', 'read_xref_measurements'])
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
            'type': 'compound',
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
            'type': 'compound',
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

xrefs = dict(
    reaction=[
        {'accession': 'ENO', 'value': 14.1, 'mode': 'quantitative', 'type': 'reaction', 'db_name': 'bigg.reaction',
         'phase': phase},
        {'accession': 'DHAD1m', 'value': 0.166, 'mode': 'quantitative', 'type': 'reaction', 'db_name': 'bigg.reaction',
         'phase': phase},
        {'accession': 'NH4t', 'value': 1.02, 'mode': 'quantitative', 'type': 'reaction', 'db_name': 'bigg.reaction',
         'phase': phase},
        {'accession': 'SUCCtm', 'value': 0.2, 'mode': 'quantitative', 'type': 'reaction', 'db_name': 'bigg.reaction',
         'phase': phase},
    ],
    protein=[
        {'accession': 'P0AC38', 'value': 14.1, 'mode': 'quantitative', 'type': 'protein', 'db_name': 'uniprot',
         'phase': phase},
        {'accession': 'P0AE37', 'value': 0.2, 'mode': 'quantitative', 'type': 'protein', 'db_name': 'uniprot',
         'phase': phase}
    ])

s1 = Sample(1, strain, medium, medium, lambda: scalars, 'S1', lambda type: xrefs[type])
s2 = Sample(2, strain, medium, medium, lambda: scalars, 'S2', lambda type: xrefs[type])
s3 = Sample(3, strain, medium, medium, lambda: scalars, 'S3', lambda type: xrefs[type])
samples_args = [[s1], [s1, s2]]


@pytest.mark.parametrize('samples', samples_args)
def test_message_for_adjust(samples):
    message = message_for_adjust(samples)
    assert message[MEASUREMENTS] == []
    grouped_scalars_phase1 = scalars_by_phases(samples)[1]
    message = message_for_adjust(samples, grouped_scalars_phase1)
    assert len(message[MEASUREMENTS]) == 8
    assert len(message[MEDIUM]) == 4
    assert extract_genotype_changes(strain) == ['+pool_gene', '+Aac']


@pytest.mark.asyncio
@pytest.mark.parametrize('samples', samples_args)
async def test_phases_for_sample(samples):
    assert await phases_for_samples(samples) == [{'id': 1, 'name': 'phase1 (0 - 14 hours)'}]


def test_name_groups():
    sample_groups = [[s1], [s2], [s3]]
    unique_keys = [
        (1, 1, 1, 1),
        (2, 2, 2, 1),
        (3, 2, 2, 1),
    ]
    names = [
        ('A1', 'B1', 'C1', 'D'),
        ('A2', 'B2', 'C2', 'D'),
        ('A3', 'B2', 'C2', 'D'),
    ]
    result = name_groups(sample_groups, unique_keys, names)
    assert result[0].name == 'A1, B1, C1'
    assert result[1].name == 'A2, B2, C2'
    assert result[2].name == 'A3, B2, C2'

    sample_groups = [[s1, s2, s3]]
    unique_keys = [(1, 1, 1, 1)]
    names = [('A', 'B', 'C', 'D')]
    assert name_groups(sample_groups, unique_keys, names)[0].name == 'A, D'
