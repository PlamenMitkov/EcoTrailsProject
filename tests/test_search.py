import pytest
from query import search_trails

def test_search_synonyms():
    results = search_trails("балкан")
    assert len(results) > 0
    assert any(t['location']['region'].lower() == 'стара планина' for t in results)

def test_normalization():
    cyrillic_results = search_trails("Рила")
    latin_results = search_trails("Rila")
    assert len(cyrillic_results) == len(latin_results)

def test_empty_result():
    assert len(search_trails("invalid123")) == 0
