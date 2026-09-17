import pytest

from poc_d04.data_gen import build_dataset


@pytest.fixture(scope="session")
def dataset(tmp_path_factory):
    d = tmp_path_factory.mktemp("data")
    build_dataset(d)
    from poc_d04.data_gen import load_dataset
    return load_dataset(d)


@pytest.fixture
def demo_text():
    return "A현장, 품목 P-01 20개, 다음 주 필요."
