from widgets.csvio import read_rows
def test_quoted_fields_and_bom():
    text = '\ufeffname,note,qty\n"Smith, John","said ""hi""",3\nplain,x,1\n'
    assert read_rows(text) == [{"name": "Smith, John", "note": 'said "hi"', "qty": "3"},
                               {"name": "plain", "note": "x", "qty": "1"}]
def test_blank_lines_skipped():
    assert read_rows("a,b\n\n1,2\n\n") == [{"a": "1", "b": "2"}]
