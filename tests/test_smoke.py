from pathlib import Path


def test_readme_exists():
    assert Path('README.md').exists()


def test_env_example_exists():
    assert Path('.env.example').exists()


def test_surql_directory_exists():
    assert Path('surql').exists()
