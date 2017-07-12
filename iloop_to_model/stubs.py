from venom.fields import MapField, Int, String, repeated, map_, Float32, Bool
from venom.message import Message
from venom.common.messages import JSONValue


class OrganismToTaxonMessage(Message):
    response = MapField(str, description='Mapping between an organism short code and taxon')


class MeasurementMessage(Message):
    type = String(description='The subject of the measurement, e.g. "compound", "protein" or "reaction"')
    id = Int(description='identifier associated with the measured subject, e.g. metabolite identifier')
    name = String(description='In case of metabolite, human-readable name')
    db_name = String(description='In case of xref data, the name of the database, e.g. UniProtKB')
    mode = String(description='Quantification mode, e.g. "relative" or "quantitative"')
    measurements = repeated(Float32(description='Measurements taken during the experiment'))
    unit = String(description='Units in which measurements are taken')


class MetaboliteMediumMessage(Message):
    id = Int(description='Metabolite ID')
    name = String(description='Metabolite human-readable name')
    concentration = Float32(description='Concentration in medium')


class SampleInfoMessage(Message):
    genotype_changes = repeated(String(description='Gnomic strings for genotype changes'))
    measurements = repeated(MeasurementMessage)
    medium = repeated(MetaboliteMediumMessage)


class ExperimentMessage(Message):
    id = Int(description='Experiment ID')
    name = String(description='Experiment name')


class SampleMessage(Message):
    id = repeated(Int(description='Sample IDs'))
    name = String(description='Sample name')
    organism = String(description='Organism short code')


class PhaseMessage(Message):
    id = Int(description='Phase ID')
    name = String(description='Phase name')


class ModelRequestMessage(Message):
    sample_ids = repeated(Int(description='Sample IDs'))
    model_id = String(description='Model ID (f.e. iJO1366)')
    phase_id = Int(description='Phase ID')
    map = String(description='Name of map to show')
    method = String(description='Simulation method to run')
    with_fluxes = Bool(description='Add flux information to  the response')


class PhasePlaneMessage(Message):
    objective_upper_bound = repeated(Float32(description='Upper bound for theoretical yield objective'))
    objective_lower_bound = repeated(Float32(description='Lower bound for theoretical yield objective'))
    objective = repeated(Float32(description='Theoretical objective values'))
    objective_id = String(description='Objective reaction ID')


class PhasePlanesMessage(Message):
    wild: PhasePlaneMessage
    modified: PhasePlaneMessage


class MetabolitePhasePlaneMessage(Message):
    flux = repeated(Float32(description='Measurement for the metabolite collected from experiment'))
    phase_planes: PhasePlanesMessage


class MaximumYieldMessage(Message):
    growth_rate = repeated(Float32(description='Growth rates collected from the experiment'))
    metabolites = MapField(MetabolitePhasePlaneMessage,
                           description='Data for the metabolites collected from the experiment')


class ModelMessage(Message):
    model_id = String(description='The saved model ID which can be used for retrieving cached information')
    fluxes = map_(Float32())  # TODO: fix not implemented while trying to add description
    model: JSONValue


class ExperimentsMessage(Message):
    response = repeated(ExperimentMessage)


class ExperimentsRequestMessage(Message):
    organism_code = String(descripton='Organism short_code that must be asssociated with at least one sample belonging '
                                      'to the  experiment')


class SamplesRequestMessage(Message):
    experiment_id = Int(descripton='Experiment ID')


class SamplesMessage(Message):
    response = repeated(SampleMessage)


class PhasesMessage(Message):
    response = repeated(PhaseMessage)


class MaximumYieldsMessage(Message):
    response = map_(MaximumYieldMessage)


class SamplesInfoMessage(Message):
    response = map_(SampleInfoMessage)


class ModelsMessage(Message):
    response = map_(ModelMessage)


class SampleModelsMessage(Message):
    response = repeated(String(description='Possible models for the sample'))