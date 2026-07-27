import backoff

from helpers.misc import backoff_handler, dict_merge
from media.pvr import PVR
from misc.log import logger

log = logger.get_logger(__name__)


class Sonarr(PVR):
    def get_objects(self):
        return self._get_objects('api/v3/series')

    @backoff.on_predicate(backoff.expo, lambda x: x is None, max_tries=4, on_backoff=backoff_handler)
    def add_series(self, series_tvdb_id, series_title, series_title_slug, quality_profile_id, language_profile_id,
                   root_folder, season_folder=True, tag_ids=None, search_missing=False, series_type='standard'):
        payload = self._prepare_add_object_payload(series_title, series_title_slug, quality_profile_id, root_folder)

        payload = dict_merge(payload, {
            'tvdbId': series_tvdb_id,
            'tags': [] if not tag_ids or not isinstance(tag_ids, list) else tag_ids,
            'seasons': [],
            'seasonFolder': season_folder,
            'seriesType': series_type,
            'languageProfileId': language_profile_id,
            'addOptions': {
                'searchForMissingEpisodes': search_missing
            }
        })

        endpoint = 'api/v3/series'

        return self._add_object(endpoint, payload, identifier_field='tvdbId', identifier=series_tvdb_id)
