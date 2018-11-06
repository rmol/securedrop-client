"""
Contains the MessageSync class, which runs in the background and loads new
 messages from the SecureDrop server.

Copyright (C) 2018  The Freedom of the Press Foundation.

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as published
by the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

import time
import logging
import os
import shutil
import subprocess
import tempfile
import sdclientapi.sdlocalobjects as sdkobjects

from PyQt5.QtCore import QObject
from securedrop_client import storage
from securedrop_client.models import make_engine

from sqlalchemy.orm import sessionmaker


logger = logging.getLogger(__name__)


class MessageSync(QObject):
    """
    Runs in the background, finding messages to download and downloading them.
    """

    def __init__(self, api, home):
        super().__init__()

        engine = make_engine(home)
        Session = sessionmaker(bind=engine)
        self.session = Session()  # Reference to the SqlAlchemy session.
        self.api = api
        self.home = home

    def run(self, loop=True):
        while True:
            submissions = storage.find_new_submissions(self.session)

            for m in submissions:
                try:

                    # api.download_submission wants an _api_ submission
                    # object, which is different from own submission
                    # object. so we coerce that here.
                    sdk_submission = sdkobjects.Submission(
                        uuid=m.uuid
                    )
                    sdk_submission.source_uuid = m.source.uuid
                    shasum, filepath = self.api.download_submission(
                        sdk_submission
                    )
                    out = tempfile.NamedTemporaryFile(suffix=".message")
                    err = tempfile.NamedTemporaryFile(suffix=".message-error",
                                                      delete=False)
                    cmd = ["qubes-gpg-client", "--decrypt", filepath]
                    res = subprocess.call(cmd, stdout=out, stderr=err)

                    os.unlink(filepath)  # original file

                    if res != 0:
                        out.close()
                        err.close()

                        with open(err.name) as e:
                            msg = e.read()
                            logger.error("GPG error: {}".format(msg))

                            os.unlink(err.name)
                    else:
                        fn_no_ext, _ = os.path.splitext(m.filename)
                        dest = os.path.join(self.home, "data", fn_no_ext)
                        shutil.copy(out.name, dest)
                        err.close()
                        storage.mark_file_as_downloaded(m.uuid, self.session)

                        logger.info("Stored message at {}".format(out.name))
                except Exception as e:
                    logger.critical(
                        "Exception while downloading submission! {}".format(e)
                    )

            if not loop:
                break
            else:
                time.sleep(5)  # pragma: no cover
