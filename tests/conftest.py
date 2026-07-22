import sys
import asyncio
import pytest

if sys.platform == "win32":
    try:
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    except Exception:
        pass


def pytest_configure(config):
    if sys.platform == "win32":
        try:
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        except Exception:
            pass


@pytest.fixture(scope="session", autouse=True)
def set_windows_event_loop_policy():
    if sys.platform == "win32":
        try:
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        except Exception:
            pass


@pytest.fixture(scope="session", autouse=True)
def patch_uc_del_winerror():
    if sys.platform == "win32":
        try:
            import undetected_chromedriver as uc
            orig_del = uc.Chrome.__del__

            def safe_del(self):
                try:
                    orig_del(self)
                except OSError as e:
                    if getattr(e, "winerror", None) == 6 or "WinError 6" in str(e):
                        pass
                    else:
                        raise

            uc.Chrome.__del__ = safe_del
        except ImportError:
            pass

