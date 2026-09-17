from ocarina_nexus.extraction.sources import game_text

SAMPLE_WIKITEXT = """\
== Overview ==

Some intro text.

== Table ==

=== 00xx Items / Great Fairies ===
{|class="wikitable"
!Text Id || Message
|-
|0001||[Item Icon 2D]You borrowed a Pocket Egg!
|-
|0002||[Item Icon 2F]You returned the Pocket Cucco!
|}

=== 10xx Kokiri Forest ===
{|class="wikitable"
!Text Id || Message
|-
|1000||Hello there!
|}
"""


def test_parse_wikitable_extracts_id_section_and_message():
    rows = game_text._parse_wikitable(SAMPLE_WIKITEXT, page_title="Text Ids (0000-1000)")

    assert len(rows) == 3
    assert rows[0]["text_id"] == "0001"
    assert rows[0]["section"] == "00xx Items / Great Fairies"
    assert rows[0]["message"] == "[Item Icon 2D]You borrowed a Pocket Egg!"
    assert rows[0]["lang"] == "en"
    assert rows[0]["source_page"] == "Text Ids (0000-1000)"

    assert rows[2]["text_id"] == "1000"
    assert rows[2]["section"] == "10xx Kokiri Forest"


def test_parse_wikitable_handles_no_matching_rows():
    rows = game_text._parse_wikitable("== Just a heading ==\nNo table here.", page_title="X")
    assert rows == []
