import pytest
from iloop_to_model.iloop_to_model import make_request, tmy, fluxes, model_json, \
    map_reactions_list


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


@pytest.mark.asyncio
async def test_fva_reactions():
    result = await model_json('iJO1366', {}, method='fva')
    assert set(map_reactions_list('maps/iJO1366.Central metabolism.json')) - set(result['fluxes'].keys()) == \
           {'L__LACt2rpp', 'D__LACt2pp', 'L__LACD3', 'GLCtex', 'D__LACtex', 'L__LACtex', 'L__LACD2'}
