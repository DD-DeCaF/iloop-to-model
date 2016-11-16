from collections import namedtuple
import pytest
from iloop_to_model.iloop_to_model import message_for_adjust, MEASUREMENTS, MEDIUM, phases_for_sample


Sample = namedtuple('Sample', ['strain', 'medium', 'feed_medium', 'read_scalars', 'name'])
Strain = namedtuple('Strain', ['organism', 'parent_strain', 'genotype'])
Medium = namedtuple('Medium', ['read_contents'])
Product = namedtuple('Product', ['chebi_id', 'chebi_name'])
Phase = namedtuple('Phase', ['id', 'title', 'start', 'end'])

p1 = Product(16828, 'first')
p2 = Product(17895, 'second')
medium = Medium(lambda: [{'compound': p1, 'concentration': 0.01}, {'compound': p2, 'concentration': 0.02}])
phase = Phase(1, 'phase1', 0, 14)
strain = Strain('ECO', None, '+Aac')
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
                     'type': 'uptake-rate'}},
           {'measurements': [0.15, 0.05],
            'phase': phase,
            'test': {'denominator': None,
                     'numerator': None,
                     'rate': 'h',
                     'type': 'growth-rate'}}]
sample = Sample(strain, medium, medium, lambda: scalars, 'S1')


def test_message_for_adjust():
    message = message_for_adjust(sample)
    assert message[MEASUREMENTS] == []
    message = message_for_adjust(sample, scalars)
    assert len(message[MEASUREMENTS]) == 2
    assert len(message[MEDIUM]) == 4


@pytest.mark.asyncio
async def test_phases_for_sample():
    assert await phases_for_sample(sample) == [{'id': 1, 'name': 'phase1 (0 - 14 hours)'}]
