import os

os.environ["PYTEST_QT_API"] = "pyqt5"
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


def pytest_configure(config):
    config.addinivalue_line("markers", "qt_real: PyQt5 UI test that exercises real Qt widgets (no mocks)")
