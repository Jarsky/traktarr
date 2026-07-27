import collections.abc
from copy import copy

from misc.log import logger

log = logger.get_logger(__name__)


def get_response_dict(response, key_field=None, key_value=None):
    found_response = None
    try:
        if isinstance(response, list):
            if not key_field or not key_value:
                found_response = response[0]
            else:
                for result in response:
                    if isinstance(result, dict) and key_field in result and result[key_field] == key_value:
                        found_response = result
                        break

                if not found_response:
                    log.error("Unable to find a result with key %s where the value is %s", key_field, key_value)

        elif isinstance(response, dict):
            found_response = response
        else:
            log.error("Unexpected response instance type of %s for %s", type(response).__name__, response)

    except Exception:
        log.exception("Exception determining response for %s: ", response)
    return found_response


def backoff_handler(details):
    log.warning("Backing off {wait:0.1f} seconds afters {tries} tries "
                "calling function {target} with args {args} and kwargs "
                "{kwargs}".format(**details))


def dict_merge(dct, merge_dct):
    for k, v in merge_dct.items():
        if k in dct and isinstance(dct[k], dict) and isinstance(merge_dct[k], collections.abc.Mapping):
            dict_merge(dct[k], merge_dct[k])
        else:
            dct[k] = merge_dct[k]

    return dct


def tag_ids_list_builder(profile_tags, config_tags):
    try:
        tag_ids = []
        for tag_name in config_tags:
            if tag_name.lower() in profile_tags:
                log.debug("Validated Tag: %s", tag_name)
                tag_ids.append(profile_tags[tag_name.lower()])
        if tag_ids:
            return tag_ids
    except Exception:
        log.exception("Exception building Tags IDs list")
    return None


def tag_names_list_builder(profile_tag_ids, chosen_tag_ids):
    try:
        if not chosen_tag_ids:
            return None

        tags = []
        for tag_name, tag_id in profile_tag_ids.items():
            if tag_id in chosen_tag_ids:
                tags.append(tag_name)
        if tags:
            return tags
    except Exception:
        log.exception("Exception building Tag Names list from Tag IDs %s: ", chosen_tag_ids)
    return None


def unblacklist_genres(genres, blacklisted_genres):
    for allow_genre in genres:
        if allow_genre in blacklisted_genres:
            blacklisted_genres.remove(allow_genre)
    return


def allowed_genres(genres, object_type, trakt_object):
    allowed_object = False

    if len(genres) == 1 and genres[0].lower() == 'ignore':
        allowed_object = True
    else:
        for item in genres:
            if item.lower() in trakt_object[object_type]['genres']:
                allowed_object = True
                break
    return allowed_object


def sorted_list(original_list, list_type, sort_key, reverse=True):
    prepared_list = copy(original_list)
    for item in prepared_list:
        if not item[list_type][sort_key]:
            if sort_key == 'released' or sort_key == 'first_aired':
                item[list_type][sort_key] = ""
            else:
                item[list_type][sort_key] = 0

    return sorted(prepared_list, key=lambda k: k[list_type][sort_key], reverse=reverse)


# reference: https://stackoverflow.com/a/16712886
def substring_after(s, delim):
    return s.partition(delim)[2]
