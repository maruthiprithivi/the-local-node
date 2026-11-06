from widgets.textutil import slugify
def test_collapses_and_trims():
    assert slugify("Hello,  World!") == "hello-world"
    assert slugify("  --Already--Slugged--  ") == "already-slugged"
    assert slugify("Café au lait") == "cafe-au-lait"
    assert slugify("a___b...c") == "a-b-c"
    assert slugify("!!!") == ""
