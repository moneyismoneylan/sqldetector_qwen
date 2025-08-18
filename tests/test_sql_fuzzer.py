from sqldetector.fuzzer.sql_fuzzer import SQLFuzzer


def test_sql_fuzzer_dedup_and_dialect():
    fuzzer = SQLFuzzer()
    payloads = list(fuzzer.generate('mysql', 'SELECT 1'))
    assert any('OR 1=1' in p for p in payloads)
    # ensure dedup works
    again = list(fuzzer.generate('mysql', 'SELECT 1'))
    assert again == []
