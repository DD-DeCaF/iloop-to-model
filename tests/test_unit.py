from collections import namedtuple
from iloop_to_model.iloop_to_model import convert_mg_to_mmol, formula_weight, message_for_adjust, MEASUREMENTS, MEDIUM


def almost_equal(a, b):
    return abs(a - b) < 10e-6


def test_mg_to_mmol():
    assert almost_equal(convert_mg_to_mmol(34.5, 58.4), 0.59075342)
    assert almost_equal(convert_mg_to_mmol(18, 18), 1)


def test_formula_weight():
    assert almost_equal(formula_weight(16828), 204.22526)
    assert almost_equal(formula_weight(42758), 180.15588)


Sample = namedtuple('Sample', ['strain', 'medium', 'feed_medium', 'read_scalars', 'name'])
Strain = namedtuple('Strain', ['organism', 'parent_strain', 'genotype'])
Medium = namedtuple('Medium', ['read_contents'])
Product = namedtuple('Product', ['chebi_id', 'chebi_name'])
Phase = namedtuple('Phase', ['id', 'name'])

p1 = Product(16828, 'first')
p2 = Product(17895, 'second')
medium = Medium(lambda: [{'compound': p1, 'concentration': 0.01}, {'compound': p2, 'concentration': 0.02}])
phase = Phase(1, 'phase1')
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
