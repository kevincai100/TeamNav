from app.services.bookmarks import BookmarkCodec


def test_nested_bookmark_folders_keep_their_direct_links_and_paths() -> None:
    bookmarks = """<!DOCTYPE NETSCAPE-Bookmark-file-1>
<DL><p>
  <DT><H3>Parent</H3>
  <DL><p>
    <DT><A HREF="https://before.example.com">Before child</A>
    <DT><H3>Child</H3>
    <DL><p>
      <DT><A HREF="https://child.example.com">Inside child</A>
    </DL><p>
    <DT><A HREF="https://after.example.com">After child</A>
  </DL><p>
  <DT><H3>Sibling</H3>
  <DL><p>
    <DT><A HREF="https://sibling.example.com">Inside sibling</A>
  </DL><p>
</DL><p>"""

    categories = BookmarkCodec.parse(bookmarks)

    assert [category.name for category in categories] == [
        "Parent",
        "Parent / Child",
        "Sibling",
    ]
    assert [[link.name for link in category.links] for category in categories] == [
        ["Before child", "After child"],
        ["Inside child"],
        ["Inside sibling"],
    ]


def test_invalid_http_urls_are_reported_without_aborting_the_import() -> None:
    bookmarks = """<!DOCTYPE NETSCAPE-Bookmark-file-1>
<DL><p>
  <DT><H3>Mixed</H3>
  <DL><p>
    <DT><A HREF="http://example.com:bad">Invalid port</A>
    <DT><A HREF="http://[invalid">Invalid IPv6</A>
    <DT><A HREF="https://example.com/valid">Valid</A>
  </DL><p>
</DL><p>"""

    inspection = BookmarkCodec.inspect(bookmarks)

    assert inspection.source_links == 3
    assert inspection.unsupported_links == 2
    assert [link.name for link in inspection.categories[0].links] == ["Valid"]
