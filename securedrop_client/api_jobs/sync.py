import logging
from typing import Any

from sdclientapi import API
from sqlalchemy.orm.session import Session

from securedrop_client.api_jobs.base import ApiJob
from securedrop_client.storage import create_or_update_user, get_remote_data, update_local_storage

logger = logging.getLogger(__name__)


class MetadataSyncJob(ApiJob):
    """
    Update source metadata such that new download jobs can be added to the queue.
    """

    NUMBER_OF_TIMES_TO_RETRY_AN_API_CALL = 2

    def __init__(self, data_dir: str) -> None:
        super().__init__(remaining_attempts=self.NUMBER_OF_TIMES_TO_RETRY_AN_API_CALL)
        self.data_dir = data_dir

    def call_api(self, api_client: API, session: Session) -> Any:
        """
        Override ApiJob.

        Download new metadata, update the local database, import new keys, and
        then the success signal will let the controller know to add any new download
        jobs.
        """

        # TODO: Once https://github.com/freedomofpress/securedrop-client/issues/648, we will want to
        # pass the default request timeout to api calls instead of setting it on the api object
        # directly.
        #
        # This timeout is used for 3 different requests: `get_sources`, `get_all_submissions`, and
        # `get_all_replies`
        api_client.default_request_timeout = 60
        sources, submissions, replies = get_remote_data(api_client)

        update_local_storage(session, sources, submissions, replies, self.data_dir)
        user = api_client.get_current_user()
        if "uuid" in user and "username" in user and "first_name" in user and "last_name" in user:
            create_or_update_user(
                user["uuid"], user["username"], user["first_name"], user["last_name"], session
            )
