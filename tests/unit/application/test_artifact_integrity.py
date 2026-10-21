"""BI-015: a pickled model artifact is only loaded when it matches the checksum recorded at write time."""

import logging
import pickle

from src.application.services.model_service.artifact_integrity import load_verified_pickle, sha256_of


def write(tmp_path, obj):
    path = tmp_path / "model.pkl"
    path.write_bytes(pickle.dumps(obj))
    return str(path)


def test_a_matching_checksum_loads(tmp_path):
    path = write(tmp_path, {"w": [1, 2]})
    assert load_verified_pickle(path, sha256_of(path)) == {"w": [1, 2]}


def test_a_modified_file_is_refused(tmp_path, caplog):
    path = write(tmp_path, {"w": [1, 2]})
    recorded = sha256_of(path)
    with open(path, "wb") as f:
        f.write(pickle.dumps({"w": [6, 6, 6]}))              # replaced after it was recorded
    with caplog.at_level(logging.ERROR):
        assert load_verified_pickle(path, recorded) is None
    assert "differs from the recorded" in caplog.text


def test_an_artifact_without_a_checksum_loads_with_a_warning(tmp_path, caplog):
    path = write(tmp_path, 42)
    with caplog.at_level(logging.WARNING):
        assert load_verified_pickle(path, None) == 42
    assert "no checksum recorded" in caplog.text


def test_missing_or_unreadable_files_give_none(tmp_path):
    assert load_verified_pickle(str(tmp_path / "absent.pkl"), None) is None
    bad = tmp_path / "bad.pkl"
    bad.write_bytes(b"not a pickle")
    assert load_verified_pickle(str(bad), sha256_of(str(bad))) is None
