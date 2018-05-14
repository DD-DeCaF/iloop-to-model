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

import pytest

from iloop_to_model.iloop_to_model import fluxes, make_request, model_json, tmy


@pytest.mark.asyncio
async def test_make_request_to_model_service():
    keys = ['model', 'fluxes']
    r = await make_request('iJO1366', {'to-return': keys})
    assert set(r.keys()) == set(keys + ['model-id'])


@pytest.mark.asyncio
async def test_tmy():
    objectives = ['chebi:42758']
    result = await tmy('iJO1366', {}, objectives)
    assert set(result['tmy'].keys()) == set(objectives)


@pytest.mark.asyncio
async def test_fluxes():
    result = await fluxes('iMM1415', {})
    assert isinstance(result, dict)


@pytest.mark.asyncio
async def test_model_json():
    result = await model_json('iNJ661', {})
    assert isinstance(result, dict)
