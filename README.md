# traktarr (Jarsky's copy)

Adds new movies and shows to Radarr and Sonarr from Trakt's anticipated, popular, trending and box office lists, filtered by
language, country, year, genre, network, runtime and Rotten Tomatoes score.

This is a private, maintained copy of [l3uddz/traktarr](https://github.com/l3uddz/traktarr) (unmaintained since 2023),
built on [notlimahrelyt/traktarr](https://github.com/notlimahrelyt/traktarr), which ported it to current Python. Our changes are
listed [below](#changes-in-this-copy). Licensed GPL-3.0, like the original.

## Contents

- [Create a Trakt API key](#create-a-trakt-api-key)
- [Install with Docker Compose](#install-with-docker-compose)
- [Configure](#configure)
- [Filter examples](#filter-examples)
- [Keeping unwanted titles out](#keeping-unwanted-titles-out)
- [Commands](#commands)
- [Updating](#updating)
- [Changes in this copy](#changes-in-this-copy)

## Create a Trakt API key

Since mid-2026, Trakt only accepts API apps from verified developers, and it disabled many older apps, which then answer
every request with `403 Forbidden`. If traktarr logs `Aborting due to failure to validate Trakt API Key`, create a new app:

1. Sign in at [trakt.tv](https://trakt.tv) and open **Settings → Your API Apps** (the developer portal).
2. **Link your GitHub account** to your developer profile. This is currently the only verification needed to create an app,
   and from **1 January 2027** apps without a linked GitHub account become unapproved.
3. Create a new application:

   | Field | Value |
   |---|---|
   | Name | anything, e.g. `traktarr-mediabox` |
   | Redirect URI | `http://localhost/callback`. Development apps only allow localhost, and traktarr never uses it |
   | Allowed origins | leave empty. They only matter for apps running in a web browser |
   | Permissions (check-in, scrobble) | leave unticked |

4. Copy the **Client ID** into `trakt.client_id` in `config.json`. Development apps sign in with PKCE and get **no client
   secret**; leave `trakt.client_secret` empty.

The anticipated, popular, trending and box office lists only need the client ID. Watchlists and private lists also need
`traktarr trakt_authentication` (a device code you enter at trakt.tv/activate); a development app allows its owner and up to
50 invited users to sign in.

Check the key works:

```bash
curl -s -o /dev/null -w "%{http_code}\n" -H "trakt-api-version: 2" -H "trakt-api-key: YOUR_CLIENT_ID" \
  -A traktarr "https://api.trakt.tv/movies/anticipated?limit=1"     # 200 = good, 403 = app disabled or unapproved
```

## Install with Docker Compose

The source lives next to the compose file, so an update is one `docker compose up -d --build`:

```
/opt/appdata/traktarr/
├── docker-compose.yml
├── config/          config.json, cache.db, traktarr.log
└── src/             this repository
```

```yaml
services:
  traktarr:
    build:
      context: ./src
      dockerfile: Dockerfile.mediabox
    image: traktarr:local
    container_name: traktarr
    command: ["run", "--run-now"]        # check the lists now, then every automatic.*.interval hours
    networks:
      - mediabox                         # the network Radarr and Sonarr are on
    volumes:
      - ./config:/config
    restart: unless-stopped
networks:
  mediabox:
    external: true
```

```bash
git clone https://github.com/Jarsky/traktarr.git /opt/appdata/traktarr/src
cd /opt/appdata/traktarr
docker compose up -d --build && docker logs -f traktarr
```

On first start without a config, traktarr writes a default `config/config.json` and exits. Fill it in and start it again.

## Configure

The parts of `config.json` that matter most (the full file has more filters):

```jsonc
{
  "trakt":  { "client_id": "YOUR_CLIENT_ID", "client_secret": "" },
  "omdb":   { "api_key": "YOUR_OMDB_KEY" },          // only needed for the Rotten Tomatoes filter
  "radarr": {
    "url": "http://radarr:7878/",
    "api_key": "…",
    "quality": "1080pToUltraHD",                     // quality profile name (case doesn't matter)
    "root_folder": "/data/movies",                   // as Radarr sees it, not as traktarr does
    "minimum_availability": "released"
  },
  "sonarr": {
    "url": "http://sonarr:8989/",
    "api_key": "…",
    "quality": "1080pToUltraHD",
    "language": "Deprecated",                        // Sonarr v4+ has no language profiles; its API returns this one
    "root_folder": "/data/tv_shows",
    "tags": []
  }
}
```

## Filter examples

### How many get added

Each number in `automatic` is a **per-run limit for that list**, and a run happens every `interval` hours. The daily maximum
is the sum. Within each list traktarr picks the most-voted titles that pass every filter.

```jsonc
"automatic": {
  "movies": { "interval": 24, "anticipated": 1, "popular": 1, "boxoffice": 1, "trending": 0 },   // ≤ 3 movies a day
  "shows":  { "interval": 24, "anticipated": 0, "popular": 1, "trending": 0 }                     // ≤ 1 show a day
}
```

The original defaults (20 anticipated + 5 popular + 3 box office + 2 trending) add up to 30 movies a day.

### Movies: new, English, blockbuster genres, well reviewed

```jsonc
"filters": {
  "movies": {
    "allowed_languages": ["en"],
    "allowed_countries": ["us", "gb", "ca", "au", "nz"],
    "allowed_genres": ["action", "adventure", "comedy", "fantasy", "horror", "science-fiction", "superhero"],
    "blacklisted_genres": ["anime", "children", "documentary", "music", "musical", "reality", "short", "sports",
                           "holiday", "history", "special-interest"],
    "blacklisted_min_year": 0,          // this year…
    "blacklisted_max_year": "+1",       // …to next year, so it never needs updating
    "blacklisted_min_runtime": 80,
    "rotten_tomatoes": "75"             // popular/box office/trending; skipped for anticipated (no score before release)
  }
}
```

### Shows: new series only, no procedurals or reality TV

```jsonc
"filters": {
  "shows": {
    "allowed_languages": ["en"],
    "allowed_countries": ["us", "gb", "ca", "au", "nz"],
    "allowed_genres": ["action", "adventure", "comedy", "fantasy", "horror", "science-fiction", "superhero"],
    "blacklisted_genres": ["animation", "anime", "children", "documentary", "game-show", "home-and-garden", "news",
                           "reality", "soap", "special-interest", "talk-show", "sporting-event"],
    "blacklisted_networks": ["youtube", "twitch", "nickelodeon", "hallmark", "cartoon network"],
    "blacklisted_min_year": 0,          // first aired this year or later: new series, not new seasons
    "blacklisted_max_year": "+1",
    "blacklisted_min_runtime": 15
  }
}
```

### How the genre filters combine

- `allowed_genres`: a title needs **at least one** of these. A sci-fi drama passes; a pure drama such as a medical or crime
  procedural doesn't. Leave it out or empty to allow any genre.
- `blacklisted_genres`: a title with **any** of these is skipped, even if it also has an allowed genre.
- Genre names are Trakt's slugs:

  | | |
  |---|---|
  | Movies | action adventure animation anime comedy crime documentary donghua drama family fantasy history holiday horror music musical mystery romance science-fiction short sporting-event superhero suspense thriller war western |
  | Shows | the movie list plus biography children game-show home-and-garden mini-series news reality soap special-interest talk-show |

  Fetch the current lists with `curl -H "trakt-api-version: 2" -H "trakt-api-key: …" https://api.trakt.tv/genres/movies`
  (or `/genres/shows`).

### Years

`blacklisted_min_year` and `blacklisted_max_year` take a fixed year (`2026`) or one relative to the current year: `0` is this
year, `"+1"` next year, `"-2"` two years ago. For shows the year is the year the series first aired.

## Keeping unwanted titles out

- traktarr skips anything already in Radarr/Sonarr **and anything on their import exclusion lists**. When you delete
  something it added, tick **Add to import exclusion list** so it doesn't come back.
- Tag what traktarr adds: set `radarr.tags` / `sonarr.tags` to a list of tag names (e.g. `["traktarr"]`), then filter by
  the tag in Radarr/Sonarr to review everything it has added.
- Try filter changes with `--dry-run` first (see [Commands](#commands)).
- To block a single title, add its TMDb ID to `filters.movies.blacklisted_tmdb_ids` or its TVDB ID to
  `filters.shows.blacklisted_tvdb_ids`. Title words go in `blacklisted_title_keywords`.

## Commands

Run any of these as a one-off with `docker compose run --rm traktarr <command>`:

```bash
movies -t popular -l 5 --dry-run           # show what would be added from a list, without adding anything
movies -t popular -l 5                     # add up to 5 movies (lists: anticipated, trending, popular, boxoffice)
movies -t anticipated -l 5 -g "science-fiction,horror"    # only these genres, this time
shows  -t popular -l 1 --dry-run
movies -t https://trakt.tv/users/NAME/lists/LIST -l 10    # any public Trakt list
trakt_authentication                       # sign in, for watchlists and private lists
```

`--help` after any command lists all its options.

## Updating

```bash
cd /opt/appdata/traktarr/src && git pull
cd .. && docker compose up -d --build
```

## Changes in this copy

On top of notlimahrelyt's Python 3.10+ port:

- **Python 3.12 image** (`Dockerfile.mediabox`); `docker/Dockerfile` is still pinned to Python 3.7.
- **Anticipated list works with a Rotten Tomatoes minimum.** Unreleased movies have no score, so before this nothing from
  that list was ever added; the check is now skipped for it.
- **No more stalled runs.** Every title used to be checked by loading its themoviedb.org / thetvdb.com web page while
  pretending to be a browser, with no timeout; those requests got blocked and runs hung for hours. Now only the ID is
  checked, and Radarr/Sonarr look the title up themselves.
- **`allowed_genres`** for movies and shows.
- **Relative years keep working** across automatic runs, instead of freezing at the year the container started.
- **Honest user agent:** Trakt requests identify as `traktarr` rather than a browser.
- Regex escape warnings on Python 3.12 fixed.

## Credits

[l3uddz](https://github.com/l3uddz) and the original contributors wrote traktarr; [notlimahrelyt](https://github.com/notlimahrelyt)
ported it to current Python. GPL-3.0, see [LICENSE.md](LICENSE.md).
