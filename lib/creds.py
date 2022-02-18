#
# COPYRIGHT 2021 FERMI NATIONAL ACCELERATOR LABORATORY
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
#
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
import os
import subprocess


def get_creds(args={}):
    """get credentials -- Note this does not currently push to
    myproxy, nor does it yet deal with tokens, but those should
    be done here as needed.
    """
    f = Popen("fake_ifdh getProxy", stdout=PIPE) 
    p = f.read().strip()
    f.close()
    f = Popen("fake_ifdh getToken", stdout=PIPE) 
    t = f.read().strip()
    f.close
    os.environ["X509_USER_PROXY"] = p
    os.environ["BEARER_TOKEN_FILE"] = t
    return p, t
