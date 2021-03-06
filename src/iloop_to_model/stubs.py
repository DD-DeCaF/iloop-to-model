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

from venom.common.messages import JSONValue
from venom.fields import Bool, Float32, Int, MapField, String, map_, repeated
from venom.message import Message


class OrganismToTaxonMessage(Message):
    response = MapField(str, description='Mapping between an organism short code and taxon')


class CurrentOrganismsMessage(Message):
    response = MapField(str, description='Mapping between organism short code and '
                                         'full name of all strains in database')


class MeasurementMessage(Message):
    type = String(description='The subject of the measurement, e.g. "compound", "protein" or "reaction"')
    id = Int(description='identifier associated with the measured subject, e.g. metabolite identifier')
    name = String(description='In case of metabolite, human-readable name')
    db_name = String(description='In case of xref data, the miriam name of the database, e.g. uniprot')
    mode = String(description='Quantification mode, e.g. "relative" or "quantitative"')
    measurements = repeated(Float32(description='Measurements taken during the experiment'))
    units = MapField(str, description='Units in which measurements are taken')
    rate = String(description='Rate')


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
    objective = String(description='Reaction ID to be set as objective')


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
    growth_rate = Float32(description='Growth rate for this simulation')
    model: JSONValue


class ExperimentsMessage(Message):
    response = repeated(ExperimentMessage)


class ExperimentsRequestMessage(Message):
    taxon_code = String(descripton='Species five-letter mnemonic short_code that must be associated with at least one '
                                   'sample belonging to the  experiment')


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
