from app.core.metrics import normalize_metrics_path


def test_normalize_metrics_path_replaces_uuid():
    path = "/api/v1/documents/123e4567-e89b-12d3-a456-426614174000/url"
    normalized = normalize_metrics_path(path)
    assert normalized == "/api/v1/documents/:id/url"


def test_normalize_metrics_path_replaces_integers():
    path = "/api/v1/items/123/comments/9"
    normalized = normalize_metrics_path(path)
    assert normalized == "/api/v1/items/:int/comments/:int"
