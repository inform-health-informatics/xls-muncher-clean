
def pytest_addoption(parser):
    """Add a --regen option to pytest."""
    parser.addoption("--regen", action="store_true",
                     default=False, help="regenerate reference data")
