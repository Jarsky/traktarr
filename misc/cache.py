import os
import sqlite3
from hashlib import md5
from pickle import dumps, loads
from time import time

from misc.log import logger

log = logger.get_logger(__name__)

# Sentinel telling a cache miss apart from a cached falsey value
_MISS = object()

_CREATE_SQL = 'CREATE TABLE IF NOT EXISTS bucket (key TEXT PRIMARY KEY, val BLOB, exp FLOAT)'
_GET_SQL = 'SELECT val, exp FROM bucket WHERE key = ?'
_DEL_SQL = 'DELETE FROM bucket WHERE key = ?'
_SET_SQL = 'INSERT OR REPLACE INTO bucket (key, val, exp) VALUES (?, ?, ?)'
_COUNT_SQL = 'SELECT COUNT(*) FROM bucket'
_OLDEST_SQL = 'SELECT key FROM bucket ORDER BY exp ASC LIMIT 1'


class Cache:
    """
    Minimal SQLite backed key/value store with per-entry expiry and a maximum
    number of entries.

    Replaces the abandoned 'cashier' package, which fails to import on
    Python 3.9+ because it depends on the removed '_dummy_thread' module.
    """

    def __init__(self, file_name='.cache', default_timeout=86400, default_length=10000):
        self.path = os.path.abspath(file_name)
        self.default_timeout = default_timeout
        self.default_length = default_length

    def _connect(self):
        conn = sqlite3.connect(self.path, timeout=60)
        with conn:
            conn.execute(_CREATE_SQL)
        return conn

    def get(self, key):
        """Return the value for key, or _MISS when absent or expired."""
        with self._connect() as conn:
            row = conn.execute(_GET_SQL, (key,)).fetchone()

            if row is None:
                return _MISS

            value, expires = row
            if expires <= time():
                conn.execute(_DEL_SQL, (key,))
                return _MISS

            return loads(value)

    def set(self, key, value):
        """Store value under key, evicting the oldest entry when full."""
        with self._connect() as conn:
            count = conn.execute(_COUNT_SQL).fetchone()[0]
            if count >= self.default_length:
                oldest = conn.execute(_OLDEST_SQL).fetchone()
                if oldest:
                    conn.execute(_DEL_SQL, (oldest[0],))

            conn.execute(_SET_SQL, (key, dumps(value, 2), time() + self.default_timeout))

    def clear(self):
        if os.path.exists(self.path):
            os.unlink(self.path)


def _build_key(fn, args, kwargs):
    # Pickle rather than repr the arguments: repr of an object instance embeds
    # its memory address, which would change the key on every run.
    payload = dumps((fn.__qualname__, args, sorted(kwargs.items())), 2)
    return md5(payload).hexdigest()


def cache(cache_file='.cache', cache_time=86400, cache_length=10000, retry_if_blank=False):
    """
    Cache a function's return value in a local SQLite file.

    :param cache_file: SQLite file the cached data is written to
    :param cache_time: how long the data should be cached for, in seconds
    :param cache_length: how many distinct calls to cache before evicting the oldest
    :param retry_if_blank: when True, a cached falsey result is refreshed instead of returned
    """

    def decorator(fn):
        def wrapped(*args, **kwargs):
            # Unlike cashier, kwargs are part of the key. Every call site passes
            # its filters as keyword arguments, so excluding them made unrelated
            # calls collide on a single cache entry.
            key = _build_key(fn, args, kwargs)
            store = Cache(cache_file, cache_time, cache_length)

            try:
                cached = store.get(key)
            except Exception:
                log.exception("Exception reading from cache %r, calling %s directly: ", cache_file, fn.__qualname__)
                return fn(*args, **kwargs)

            if cached is not _MISS and (cached or not retry_if_blank):
                return cached

            result = fn(*args, **kwargs)

            try:
                store.set(key, result)
            except Exception:
                log.exception("Exception writing to cache %r for %s: ", cache_file, fn.__qualname__)

            return result

        # Preserve the wrapped function's identity for logging and tracebacks
        wrapped.__name__ = fn.__name__
        wrapped.__qualname__ = fn.__qualname__
        wrapped.__doc__ = fn.__doc__
        return wrapped

    return decorator
