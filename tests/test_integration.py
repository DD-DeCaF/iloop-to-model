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
