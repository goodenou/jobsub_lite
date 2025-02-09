import os
import sys
import tempfile
import time
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

import utils

from test_unit import TestUnit
from test_creds_unit import needs_credentials  # pylint: disable=unused-import
from test_creds_unit import clear_x509_user_proxy  # pylint: disable=unused-import


def fill_in(dir):
    open(f"{dir}/simple.sh", "w").close()
    open(f"{dir}/simple.cmd", "w").close()


@pytest.fixture
def test_job_dir():
    d = tempfile.mkdtemp()
    d = f"{d}/js_testdir"
    os.mkdir(d)
    fill_in(d)
    return d


@pytest.fixture
def test_old_dir(test_job_dir):
    d = f"{test_job_dir}/../js_newstuff"
    os.mkdir(d)
    fill_in(d)
    d = f"{test_job_dir}/../js_oldstuff"
    os.mkdir(d)
    fill_in(d)
    eightdaysago = time.time() - 691200
    os.utime(d, times=(eightdaysago, eightdaysago))
    return test_job_dir


class TestUtilsUnit:
    """
    Use with pytest... unit tests for ../lib/*.py
    """

    #
    # utils.py routines...
    #

    @pytest.mark.unit
    def test_fixquote_1(self):
        """check the fixquote routine"""
        assert utils.fixquote("test1") == "test1"
        assert utils.fixquote("test2=test3") == 'test2="test3"'
        assert utils.fixquote("test2=test3=test4") == 'test2="test3=test4"'

    @pytest.mark.unit
    def test_grep_n_1(self):
        """check the grep_n routine on us"""
        assert utils.grep_n(r"class (\w*):", 1, __file__) == "TestUtilsUnit"
        assert utils.grep_n(r"import (\w*)", 1, __file__) == "os"

    @pytest.mark.unit
    def test_fix_unit_1(self):
        """test fixing units on '64gb' memory"""
        args = TestUnit.test_vargs.copy()
        memtable = {"k": 1.0 / 1024, "m": 1, "g": 1024, "t": 1024 * 1024}
        utils.fix_unit(args, "memory", memtable, -1, "b", -2)
        assert args["memory"] == 64 * 1024

    @pytest.mark.unit
    def test_get_principal_1(self):
        """make sure get_principal returns a string starting with $USER"""
        # blatantly assumes you have a valid principal...
        res = utils.get_principal()
        assert res.split("@")[0] == os.environ["USER"]

    @pytest.mark.unit
    def test_set_extras_1(self, needs_credentials):
        """call set_extras_n_fix_units, verify one thing from environment
        and one unit conversion..."""
        proxy, token = needs_credentials
        args = TestUnit.test_vargs.copy()
        utils.set_extras_n_fix_units(args, TestUnit.test_schedd, proxy, token)
        assert args["user"] == os.environ["USER"]
        assert args["memory"] == 64 * 1024

    @pytest.mark.unit
    def test_get_client_dn_valid_proxy_provided(
        self, needs_credentials, clear_x509_user_proxy
    ):
        """Call get_client_dn with proxy specified"""
        _proxy, _ = needs_credentials
        clear_x509_user_proxy
        client_dn = utils.get_client_dn(proxy=_proxy)
        assert os.environ["USER"] in client_dn

    @pytest.mark.unit
    def test_get_client_dn_env_plus_proxy_provided(self, needs_credentials):
        """Call get_client_dn with proxy specified, env set.  Should grab
        proxy from passed-in arg"""
        _proxy, _ = needs_credentials
        old_x509_user_proxy_value = os.environ.pop("X509_USER_PROXY", None)
        os.environ[
            "X509_USER_PROXY"
        ] = "foobar"  # Break the environment so that this test won't accidentally pass
        client_dn = utils.get_client_dn(proxy=_proxy)
        assert os.environ["USER"] in client_dn
        os.environ["X509_USER_PROXY"] = old_x509_user_proxy_value

    @pytest.mark.unit
    def test_get_client_dn_no_proxy_provided(self, needs_credentials):
        """Call get_client_dn with no proxy specified.  Should grab proxy from
        env"""
        _proxy, _ = needs_credentials  # Sets $X509_USER_PROXY
        client_dn = utils.get_client_dn()
        assert os.environ["USER"] in client_dn

    @pytest.mark.unit
    def test_get_client_dn_no_proxy_provided_no_env(
        self, needs_credentials, clear_x509_user_proxy
    ):
        """Call get_client_dn with no proxy specified, environment not set.
        Should get proxy from standard grid location"""
        _proxy, _ = needs_credentials
        clear_x509_user_proxy
        client_dn = utils.get_client_dn()
        assert os.environ["USER"] in client_dn

    @pytest.mark.unit
    def test_get_client_dn_bad_proxy(self):
        """If we give a bad proxy file, or there's some other problem, we
        should get "" as the return value"""
        client_dn = utils.get_client_dn("bad_path")
        assert client_dn == ""

    @pytest.mark.unit
    def test_cleanup_simple(self, test_job_dir):
        assert os.path.exists(f"{test_job_dir}/simple.cmd")
        utils.cleanup({"submitdir": test_job_dir})
        assert not os.path.exists(f"{test_job_dir}/simple.cmd")
        assert not os.path.exists(test_job_dir)

    @pytest.mark.unit
    def test_cleanup_old(self, test_old_dir):
        oldd = f"{os.path.dirname(test_old_dir)}/js_oldstuff"
        newd = f"{os.path.dirname(test_old_dir)}/js_newstuff"
        assert os.path.exists(f"{test_old_dir}/simple.cmd")
        assert os.path.exists(f"{oldd}/simple.cmd")
        assert os.path.exists(f"{newd}/simple.cmd")
        utils.cleanup({"submitdir": test_old_dir})
        assert not os.path.exists(f"{test_old_dir}/simple.cmd")
        assert not os.path.exists(f"{oldd}/simple.cmd")
        assert os.path.exists(f"{newd}/simple.cmd")

    @pytest.mark.unit
    def test_resolve_site_and_usage_model(self):
        _should_work = [
            # no flags
            (
                "",
                "DEDICATED,OPPORTUNISTIC,OFFSITE",
                [],
                (
                    utils.SiteAndUsageModel("", "DEDICATED,OPPORTUNISTIC,OFFSITE"),
                    [],
                ),
            ),
            # --onsite
            (
                "",
                "DEDICATED,OPPORTUNISTIC",
                [],
                (
                    utils.SiteAndUsageModel(
                        utils.ONSITE_SITE_NAME, "DEDICATED,OPPORTUNISTIC"
                    ),
                    [],
                ),
            ),
            # --site Fermigrid
            (
                utils.ONSITE_SITE_NAME,
                "",
                [],
                (
                    utils.SiteAndUsageModel(
                        utils.ONSITE_SITE_NAME, "DEDICATED,OPPORTUNISTIC"
                    ),
                    [],
                ),
            ),
            # --site Random_Site
            (
                "Random_Site",
                "",
                [],
                (
                    utils.SiteAndUsageModel("Random_Site", "OFFSITE"),
                    [],
                ),
            ),
            # --offsite
            (
                "",
                "OFFSITE",
                [],
                (
                    utils.SiteAndUsageModel("", "OFFSITE"),
                    [],
                ),
            ),
            # --resource-provides=usage_model=DEDICATED,OFFSITE
            (
                "",
                "",
                ['usage_model="DEDICATED,OFFSITE"'],
                (
                    utils.SiteAndUsageModel("", ""),
                    ['usage_model="DEDICATED,OFFSITE"'],
                ),
            ),
            # --resource-provides=usage_model=DEDICATED,OFFSITE --site Fermigrid
            (
                utils.ONSITE_SITE_NAME,
                "",
                ['usage_model="DEDICATED,OFFSITE"'],
                (
                    utils.SiteAndUsageModel(
                        utils.ONSITE_SITE_NAME, "DEDICATED,OPPORTUNISTIC"
                    ),
                    [],
                ),
            ),
            # --resource-provides=usage_model=DEDICATED,OFFSITE --site Random_Site
            (
                "Random_Site",
                "",
                ['usage_model="DEDICATED,OFFSITE"'],
                (
                    utils.SiteAndUsageModel("Random_Site", "OFFSITE"),
                    [],
                ),
            ),
            # --site=Fermigrid,Random_Site --resource-provides=usage_model=DEDICATED,OFFSITE
            (
                f"{utils.ONSITE_SITE_NAME},Random_Site",
                "",
                ['usage_model="DEDICATED,OFFSITE"'],
                (
                    utils.SiteAndUsageModel(
                        f"{utils.ONSITE_SITE_NAME},Random_Site",
                        "DEDICATED,OPPORTUNISTIC,OFFSITE",
                    ),
                    [],
                ),
            ),
            # --site=Fermigrid,Random_Site
            (
                f"{utils.ONSITE_SITE_NAME},Random_Site",
                "",
                [],
                (
                    utils.SiteAndUsageModel(
                        f"{utils.ONSITE_SITE_NAME},Random_Site",
                        "DEDICATED,OPPORTUNISTIC,OFFSITE",
                    ),
                    [],
                ),
            ),
            # --site=Fermigrid,Random_Site --resource_provides=usage_model=DEDICATED,OFFSITE --resource-provides=IWANT=this_resource
            (
                f"{utils.ONSITE_SITE_NAME},Random_Site",
                "",
                ['usage_model="DEDICATED,OFFSITE"', 'IWANT="this_resource"'],
                (
                    utils.SiteAndUsageModel(
                        f"{utils.ONSITE_SITE_NAME},Random_Site",
                        "DEDICATED,OPPORTUNISTIC,OFFSITE",
                    ),
                    ['IWANT="this_resource"'],
                ),
            ),
            # --onsite --resource_provides=usage_model=DEDICATED,OFFSITE --resource-provides=IWANT=this_resource
            (
                "",
                "DEDICATED,OPPORTUNISTIC",
                ['usage_model="DEDICATED,OFFSITE"', 'IWANT="this_resource"'],
                (
                    utils.SiteAndUsageModel(
                        utils.ONSITE_SITE_NAME, "DEDICATED,OPPORTUNISTIC"
                    ),
                    ['IWANT="this_resource"'],
                ),
            ),
            # --onsite --resource_provides=usage_model=DEDICATED,OFFSITE
            (
                "",
                "DEDICATED,OPPORTUNISTIC",
                ['usage_model="DEDICATED,OFFSITE"'],
                (
                    utils.SiteAndUsageModel(
                        utils.ONSITE_SITE_NAME, "DEDICATED,OPPORTUNISTIC"
                    ),
                    [],
                ),
            ),
            # --resource_provides=usage_model=DEDICATED,OPPORTUNISTIC --site Random_Site
            (
                "Random_Site",
                "",
                ['usage_model="DEDICATED,OPPORTUNISTIC"'],
                (
                    utils.SiteAndUsageModel("Random_Site", "OFFSITE"),
                    [],
                ),
            ),
            # --resource-provides=usage_model=DEDICATED --site Random_Site
            (
                "Random_Site",
                "",
                ['usage_model="DEDICATED"'],
                (
                    utils.SiteAndUsageModel("Random_Site", "OFFSITE"),
                    [],
                ),
            ),
            # --resource-provides=usage_model=OFFSITE --site Fermigrid
            (
                utils.ONSITE_SITE_NAME,
                "",
                ['usage_model="OFFSITE"'],
                (
                    utils.SiteAndUsageModel(
                        utils.ONSITE_SITE_NAME, "DEDICATED,OPPORTUNISTIC"
                    ),
                    [],
                ),
            ),
            # --site=Random_Site_1,Random_Site_2 --resource-provides=usage_model=DEDICATED,OFFSITE
            (
                "Random_Site_1,Random_Site_2",
                "",
                ['usage_model="DEDICATED,OFFSITE"'],
                (
                    utils.SiteAndUsageModel("Random_Site_1,Random_Site_2", "OFFSITE"),
                    [],
                ),
            ),
            # --onsite --resource-provides=usage_model=DEDICATED,OFFSITE
            (
                "",
                "DEDICATED,OPPORTUNISTIC",
                ['usage_model="DEDICATED,OFFSITE"'],
                (
                    utils.SiteAndUsageModel(
                        utils.ONSITE_SITE_NAME, "DEDICATED,OPPORTUNISTIC"
                    ),
                    [],
                ),
            ),
            # --offsite --resource-provides=usage_model=DEDICATED
            (
                "",
                "OFFSITE",
                ['usage_model="DEDICATED"'],
                (
                    utils.SiteAndUsageModel("", "OFFSITE"),
                    [],
                ),
            ),
        ]

        for (sites, usage_model, resource_provides_quoted, expected) in _should_work:
            assert (
                utils.resolve_site_and_usage_model(
                    sites, usage_model, resource_provides_quoted
                )
                == expected
            )

        # I honestly can't think of any combos that don't work/won't get corrected before we get to validation,
        # but I'm leaving this here unless I missed something
        _should_not_work = []
        for (sites, usage_model, resource_provides_quoted) in _should_not_work:
            with pytest.raises(
                utils.SiteAndUsageModelConflictError, match="are in conflict"
            ):
                utils.resolve_site_and_usage_model(
                    sites, usage_model, resource_provides_quoted
                )
