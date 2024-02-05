from notifier.formatter import convert_syntax


def test_that_formatting_does_what_i_expect() -> None:
    """Test various formatter quirks."""
    for pair in [
        ("//italic//", "<i>italic</i>"),
        ("[[ul]]text[[/ul]]", "<ul>text</ul>"),
        ("[[ul]][[li]]text[[/li]][[/ul]]", "<ul><li>text</li></ul>"),
        # Italic syntax shouldn't disrupt links
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
        # Links shouldn't break syntax that also uses square brackets
        ("[[li]][url text][[/li]]", """<li><a href="url">text</a></li>"""),
        (
            """[[ul style="list-style-type: ':open_mailbox_with_raised_flag: '"]]text[[/ul]]""",
            """<ul style="list-style-type: ':open_mailbox_with_raised_flag: '">text</ul>""",
        ),
        (
            """[[ul style="list-style-type: ':open_mailbox_with_raised_flag: '"]][https://www.example.com/path text][[/ul]]""",
            """<ul style="list-style-type: ':open_mailbox_with_raised_flag: '"><a href="https://www.example.com/path">text</a></ul>""",
        ),
    ]:
        assert convert_syntax(pair[0], "email") == pair[1]
