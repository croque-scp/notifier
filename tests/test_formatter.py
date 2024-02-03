from notifier.formatter import convert_syntax


def test_italic_links() -> None:
    """Test that italic syntax doesn't disrupt links."""
    for pair in [
        ("//italic//", "<i>italic</i>"),
        (
            "[[user Username]]",
            """<a href="https://www.wikidot.com/user:info/Username">Username</a>""",
        ),
        ("[url text]", """<a href="url">text</a>"""),
        ("[url long text]", """<a href="url">long text</a>"""),
        ("//[url text]//", """<i><a href="url">text</a></i>"""),
        (
            "//[https://url text]//",
            """<i><a href="https://url">text</a></i>""",
        ),
        (
            "[https://url text] [https://url text]",
            """<a href="https://url">text</a> <a href="https://url">text</a>""",
        ),
    ]:
        assert convert_syntax(pair[0], "email") == pair[1]
