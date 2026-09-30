from src.spreader import spread_company
from src.validation import validate_spread
from src.excel_builder import build_workbook
from tests.test_tag_mapping import _facts, _instant_fact, _duration_fact


def fixture():
    data = _facts({
        'Assets': [_instant_fact('2023-12-31', 10000000, 2023, '2024-02-01')],
        'StockholdersEquity': [_instant_fact('2023-12-31', 4000000, 2023, '2024-02-01')],
        'Revenues': [_duration_fact('2023-01-01', '2023-12-31', 9000000, 2023, '2024-02-01')],
        'GeneralAndAdministrativeExpense': [_duration_fact('2023-01-01', '2023-12-31', 1000000, 2023, '2024-02-01')],
        'CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents': [_instant_fact('2023-12-31', 3000000, 2023, '2024-02-01')],
    })
    data['cik'] = 320193
    data['facts']['us-gaap']['Revenues']['units']['USD'][0]['accn'] = '0000320193-24-000001'
    return data


def test_derived_balance_is_not_independent_validation():
    spread = spread_company(fixture(), 1)
    assert validate_spread(spread)[2023]['balance_sheet_ties']['ok'] is None
    wb = build_workbook({'TEST': {'entity_name':'Test', 'spread':spread, 'validation':validate_spread(spread)}})
    assert wb['TEST']['B27'].value == 'Derived—not independently verified'


def test_workbook_missing_inputs_and_provenance(tmp_path):
    from openpyxl import load_workbook
    spread = spread_company(fixture(), 1)
    wb = build_workbook({'TEST': {'entity_name':'Test', 'spread':spread, 'validation':validate_spread(spread), 'retrieved_at':'2026-09-30'}})
    target = tmp_path / 'spread.xlsx'
    wb.save(target)
    wb = load_workbook(target)
    assert wb['TEST']['B5'].value is None
    assert wb['TEST']['B6'].value == '=IF(COUNT(B4,B5)=2,B4-B5,"N/A")'
    assert 'COUNT(B30:B32)=3' in wb['TEST']['B33'].value
    assert 'COUNT(B14,B4)=2' in wb['TEST']['B15'].value
    rows = list(wb['Sources'].values)
    revenue = next(r for r in rows if r[2] == 'revenue')
    assert revenue[6:10] == ('2023-01-01','2023-12-31','2024-02-01','0000320193-24-000001')
    assert '/320193/000032019324000001/' in revenue[10]
    assert revenue[11] == '2026-09-30'


def test_partial_concepts_are_not_substituted():
    year = spread_company(fixture(), 1)[2023]
    assert year['sga']['value'] is None
    assert year['cash']['value'] is None


def test_refresh_bypasses_cache_and_records_time(tmp_path, monkeypatch):
    import src.edgar_client as client
    monkeypatch.setattr(client, 'CACHE_DIR', str(tmp_path))
    monkeypatch.setattr(client.time, 'sleep', lambda _: None)
    client._write_cache('companyfacts_123.json', {'old': True})
    class Response:
        def raise_for_status(self): pass
        def json(self): return {'new': True}
    calls = []
    def get(*args, **kwargs):
        calls.append(args)
        return Response()
    monkeypatch.setattr(client._session, 'get', get)
    assert client.get_company_facts('123') == {'old': True}
    assert not calls
    fresh = client.get_company_facts('123', refresh=True)
    assert fresh['new'] and fresh['_retrieved_at']
    assert len(calls) == 1
    assert client.get_company_facts('123') == fresh
