import os
import sys
import pytest

#
# we assume everwhere our current directory is in the package
# test area, so go ahead and cd there
#
os.chdir(os.path.dirname(__file__))


#
# import modules we need to test, since we chdir()ed, can use relative path
# unless we're testing installed, then use /opt/jobsub_lite/...
#
if os.environ.get("JOBSUB_TEST_INSTALLED", "0") == "1":
    sys.path.append("/opt/jobsub_lite/lib")
else:
    sys.path.append("../lib")

import fake_ifdh


@pytest.mark.unit
def test_getTmp():
    if os.environ.get("TMPDIR", None):
        del os.environ["TMPDIR"]
    res = fake_ifdh.getTmp()
    assert res == "/tmp"


@pytest.mark.unit
def test_getTmp_override():
    os.environ["TMPDIR"] = "/var/tmp"
    res = fake_ifdh.getTmp()
    assert res == "/var/tmp"


@pytest.mark.unit
def test_getExp_GROUP():
    os.environ["GROUP"] = "samdev"
    res = fake_ifdh.getExp()
    assert res == "samdev"


@pytest.mark.unit
def test_getRole():
    res = fake_ifdh.getRole()
    assert res == fake_ifdh.DEFAULT_ROLE


@pytest.mark.unit
def test_getRole_override():
    override_role = "Hamburgler"
    res = fake_ifdh.getRole(override_role)
    assert res == override_role


@pytest.fixture
def clear_token():
    if os.environ.get("BEARER_TOKEN_FILE", None):
        del os.environ["BEARER_TOKEN_FILE"]


@pytest.fixture
def fermilab_token(clear_token):
    os.environ["GROUP"] = "fermilab"
    return fake_ifdh.getToken("Analysis")


@pytest.mark.unit
def test_checkToken_fail():
    tokenfile = "/dev/null"
    with pytest.raises(ValueError):
        res = fake_ifdh.checkToken(tokenfile)


@pytest.mark.unit
def test_checkToken_success(fermilab_token):
    res = fake_ifdh.checkToken(fermilab_token)
    assert res


@pytest.mark.unit
def test_getToken_good(clear_token, fermilab_token):
    assert os.path.exists(fermilab_token)


@pytest.mark.unit
def test_getToken_fail(clear_token):
    with pytest.raises(PermissionError):
        os.environ["GROUP"] = "bozo"
        fake_ifdh.getToken("Analysis")


@pytest.mark.unit
def test_getProxy_good(clear_token):
    os.environ["GROUP"] = "fermilab"
    proxy = fake_ifdh.getProxy("Analysis")
    assert os.path.exists(proxy)


@pytest.mark.unit
def test_getProxy_override(clear_token, tmp_path):
    fake_path = tmp_path / "test_proxy"
    old_x509_user_proxy = os.environ.get("X509_USER_PROXY")
    os.environ["X509_USER_PROXY"] = str(fake_path)
    os.environ["GROUP"] = "fermilab"
    proxy = fake_ifdh.getProxy("Analysis")
    try:
        assert proxy == str(fake_path)
    except AssertionError:
        raise
    finally:
        if old_x509_user_proxy is not None:
            os.environ["X509_USER_PROXY"] = old_x509_user_proxy


@pytest.mark.unit
def test_getProxy_fail(clear_token, tmp_path):
    fake_path = tmp_path / "test_proxy"
    if os.path.exists(fake_path):
        os.unlink(fake_path)
    old_x509_user_proxy = os.environ.get("X509_USER_PROXY")
    os.environ["X509_USER_PROXY"] = str(fake_path)
    os.environ["GROUP"] = "bozo"
    try:
        proxy = fake_ifdh.getProxy("Analysis")
        print(f"got proxy: {proxy}")
    except PermissionError:
        assert True
    else:
        assert False
    finally:
        if old_x509_user_proxy is not None:
            os.environ["X509_USER_PROXY"] = old_x509_user_proxy


@pytest.mark.unit
def test_cp():
    dest = __file__ + ".copy"
    fake_ifdh.cp(__file__, dest)
    assert os.path.exists(dest)
    os.unlink(dest)
