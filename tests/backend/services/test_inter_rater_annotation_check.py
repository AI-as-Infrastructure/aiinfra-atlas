"""Pagination tests for the production annotation-shape checker."""

from utils.scripts.inter_rater_annotation_check import iter_annotations


class _Response:
    def __init__(self, body):
        self._body = body

    def raise_for_status(self):
        return None

    def json(self):
        return self._body


class _Http:
    def __init__(self):
        self.calls = []
        self.responses = [
            _Response({"data": [{"id": "first"}], "next_cursor": "page-2"}),
            _Response({"data": [{"id": "second"}]}),
        ]

    def get(self, url, params, headers):
        self.calls.append((url, params, headers))
        return self.responses.pop(0)


def test_iter_annotations_follows_next_cursor():
    http = _Http()

    annotations = list(
        iter_annotations(
            http,
            "https://phoenix.example/span_annotations",
            {"Authorization": "Bearer test"},
            ["span-1"],
        )
    )

    assert annotations == [{"id": "first"}, {"id": "second"}]
    assert ("cursor", "page-2") not in http.calls[0][1]
    assert ("cursor", "page-2") in http.calls[1][1]
