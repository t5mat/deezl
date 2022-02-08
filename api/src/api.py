import datetime
from contextlib import AsyncExitStack
from io import BytesIO
import mutagen
from mutagen import flac, mp3, id3
from PIL import Image
from fastapi import FastAPI, Response
from pydantic import BaseSettings
from async_lru import alru_cache
from aiolimiter import AsyncLimiter
from .common import *
from .deezer import *


class DeezerClient:
    GATEWAY_LIMITS = dict(max_rate=5, time_period=1)
    API_LIMITS = dict(max_rate=5, time_period=1)
    TRACKS_LIMITS = dict(max_rate=1, time_period=2)
    IMAGES_LIMITS = dict(max_rate=1, time_period=2)
    IMAGES_COOLDOWN = dict(cooldown=10, attempts=3)

    def __init__(self, settings, session: aiohttp.ClientSession):
        self._settings = settings
        self._password_md5 = bytes.fromhex(self._settings.password_md5)
        self._track_decryption_secret = self._settings.track_decryption_secret.encode()

        self._session = session

        self._gateway_rate_limiter = AsyncLimiter(**self.GATEWAY_LIMITS)
        self._api_rate_limiter = AsyncLimiter(**self.API_LIMITS)
        self._tracks_rate_limiter = AsyncLimiter(**self.TRACKS_LIMITS)
        self._images_rate_limiter = AsyncLimiter(**self.IMAGES_LIMITS)

        self._last_login = None
        self._user = None

    async def _call_gateway(self, method: str, data: dict) -> dict:
        async with self._gateway_rate_limiter:
            logged_in = False
            while not logged_in:
                if self._last_login is None or (datetime.datetime.now() - self._last_login) > datetime.timedelta(minutes=30):
                    self._last_login = None

                    await login_deezer_session(self._session, self._settings.email, self._password_md5, self._settings.client_id, self._settings.client_secret)
                    self._user = await call_deezer_gateway(self._session, 'deezer.getUserData', {}, None)

                    self._last_login = datetime.datetime.now()
                    logged_in = True

                try:
                    return await call_deezer_gateway(self._session, method, data, self._user['checkForm'])
                except Exception:
                    self._last_login = None
                    if logged_in:
                        raise
                    continue

    async def get_gateway_track_page(self, id_: str) -> dict:
        page = await self._call_gateway('deezer.pageTrack', {'SNG_ID': id_})
        if (fallback := page['DATA'].get('FALLBACK')):
            page = await self._call_gateway('deezer.pageTrack', {'SNG_ID': fallback['SNG_ID']})
        return page

    async def get_gateway_album_page(self, id_: str) -> dict:
        return await self._call_gateway('deezer.pageAlbum', {'ALB_ID': id_, 'lang': 'en', 'header': True, 'tab': 0})

    async def get_gateway_playlist_page(self, id_: str) -> dict:
        return await self._call_gateway('deezer.pagePlaylist', {'PLAYLIST_ID': id_, 'lang': 'en', 'start': 0, 'nb': -1, 'tags': True})

    async def get_gateway_search_results(self, query: str, type_: str, index: int, limit: int) -> dict:
        return await self._call_gateway('search.music', {'query': query, 'output': type_, 'start': index, 'nb': limit, 'filter': 'ALL'})

    async def get_api_track(self, id_: str) -> dict:
        async with self._api_rate_limiter:
            return await call_deezer_api(self._session, f'track/{id_}')

    async def download_track(self, id_: str, track_token: str, format_: str) -> bytes:
        async with self._tracks_rate_limiter:
            url = await get_deezer_track_file_url(self._session, track_token, format_, self._user['USER']['OPTIONS']['license_token'])

            data = bytearray()
            async with self._session.get(url) as response:
                response.raise_for_status()
                async for chunk in decrypt_deezer_track_file_http_stream(id_, response.content, self._track_decryption_secret):
                    data += chunk
            return bytes(data)

    async def download_image(self, url: str) -> bytes:
        async with self._images_rate_limiter:
            i = 0
            while True:
                try:
                    async with self._session.get(url) as response:
                        response.raise_for_status()
                        return await response.read()
                except Exception:
                    if (i := i + 1) == self.IMAGES_COOLDOWN['attempts']:
                        raise
                    await asyncio.sleep(IMAGES_COOLDOWN['cooldown'])


def parse_track(gateway_track: dict, api_track: dict | None) -> dict:
    d = dict()

    d['title'] = gateway_track['SNG_TITLE'].strip() + (f' {version.strip()}' if (version := gateway_track.get('VERSION')) else '')

    artists = sorted(gateway_track['ARTISTS'], key=lambda a: (int(a.get('ROLE_ID', 0)), int(a.get('ARTISTS_SONGS_ORDER', 0))))
    d['artists'] = [{
            'name': a['ART_NAME'],
            'deezer': {
                'id': a['ART_ID']
            }
        } for a in artists]

    d['album'] = {
        'title': gateway_track['ALB_TITLE'],
        'deezer': {
            'id': gateway_track['ALB_ID'],
            'picture_md5': gateway_track['ALB_PICTURE']
        }
    }

    d['disk_number'] = int(gateway_track['DISK_NUMBER'])
    d['track_number'] = int(gateway_track['TRACK_NUMBER'])

    if (date := gateway_track.get('ORIGINAL_RELEASE_DATE') or gateway_track.get('PHYSICAL_RELEASE_DATE') or gateway_track.get('DIGITAL_RELEASE_DATE')) and date != '0000-00-00':
        d['date'] = datetime.datetime.strptime(date, '%Y-%m-%d')

    d['duration_seconds'] = int(gateway_track['DURATION'])

    if (contributors := gateway_track['SNG_CONTRIBUTORS']):
        if (composers := contributors.get('composer')):
            d['composers'] = composers

    if (copyright_ := gateway_track.get('COPYRIGHT')):
        d['copyright'] = copyright_

    if (isrc := gateway_track.get('ISRC')):
        d['isrc'] = isrc

    if (explicit := gateway_track.get('EXPLICIT_LYRICS')):
        d['explicit'] = bool(int(explicit))

    if api_track is not None:
        if (bpm := api_track['bpm']):
            d['bpm'] = float(bpm)

    d['deezer'] = {
        'id': gateway_track['SNG_ID'],
        'md5': gateway_track['MD5_ORIGIN'],
        'media_version': gateway_track['MEDIA_VERSION'],
        'formats': {format_: size for k, v in gateway_track.items() if (format_ := k.partition('FILESIZE_')[2]) and (size := int(v))},
        'preview_url': next((m['HREF'] for m in gateway_track['MEDIA'] if m['TYPE'] == 'preview'), None)
    }

    return d

def parse_album(gateway_album: dict, gateway_album_tracks: dict | None) -> dict:
    d = dict()

    d['title'] = gateway_album['ALB_TITLE']

    artists = sorted(gateway_album['ARTISTS'], key=lambda a: int(a.get('ARTISTS_ALBUMS_ORDER', 0)))
    d['artists'] = [
        {
            'name': a['ART_NAME'],
            'deezer': {
                'id': a['ART_ID']
            }
        } for a in artists]

    if gateway_album_tracks is not None:
        disk_numbers = {int(t['DISK_NUMBER']) for t in gateway_album_tracks}
        disk_count = max(disk_numbers)
        if disk_numbers != {*range(1, disk_count + 1)}:
            raise Exception(disk_numbers, disk_count)
        d['disk_count'] = disk_count

        track_numbers = {int(t['TRACK_NUMBER']) for t in gateway_album_tracks}
        track_count = max(track_numbers)
        if track_numbers != {*range(1, track_count + 1)}:
            raise Exception(track_numbers, track_count)
        d['track_count'] = track_count

        d['duration_seconds'] = sum(int(t['DURATION']) for t in gateway_album_tracks)

    if 'track_count' not in d and (track_count := gateway_album.get('NUMBER_TRACK')):
        d['track_count'] = int(track_count)

    if (date := gateway_album.get('ORIGINAL_RELEASE_DATE') or gateway_album.get('PHYSICAL_RELEASE_DATE') or gateway_album.get('DIGITAL_RELEASE_DATE')) and date != '0000-00-00':
        d['date'] = datetime.datetime.strptime(date, '%Y-%m-%d')

    if (contributors := gateway_album.get('ALB_CONTRIBUTORS')):
        if (composers := contributors.get('composer')):
            d['composers'] = composers

    if (publisher := gateway_album.get('LABEL_NAME')):
        d['publisher'] = publisher

    if (upc := gateway_album.get('UPC')):
        d['ean'] = '0' + upc


    if (upc := gateway_album.get('UPC')):
        d['ean'] = '0' + upc

    d['explicit'] = int(gateway_album.get('EXPLICIT_ALBUM_CONTENT', {}).get('EXPLICIT_LYRICS_STATUS', 0)) in (1, 4)

    d['deezer'] = {
        'id': gateway_album['ALB_ID'],
        'picture_md5': gateway_album['ALB_PICTURE']
    }

    return d

def parse_playlist(gateway_playlist: dict) -> dict:
    d = dict()

    d['title'] = gateway_playlist['TITLE']

    d['user'] = {
        'name': gateway_playlist['PARENT_USERNAME'],
        'deezer': {
            'id': gateway_playlist['PARENT_USER_ID']
        }
    }

    if (track_count := gateway_playlist.get('NB_SONG')):
        d['track_count'] = int(track_count)

    if (duration := gateway_playlist.get('DURATION')):
        d['duration_seconds'] = int(duration)

    if (date := gateway_playlist.get('DATE_MOD')):
        d['date'] = datetime.datetime.strptime(date, '%Y-%m-%d %H:%M:%S')

    d['deezer'] = {
        'id': gateway_playlist['PLAYLIST_ID'],
        'picture_md5': gateway_playlist['PLAYLIST_PICTURE'],
        'picture_type': gateway_playlist['PICTURE_TYPE']
    }

    return d


def create_track_tags(track: dict) -> dict:
    tags = dict()

    if (k := 'title', v := track.get(k))[1] is not None:
        tags[k] = v
    if (k := 'artists', v := track.get(k))[1] is not None:
        tags[k] = [a['name'] for a in v]
    if (k := 'disk_number', v := track.get(k))[1] is not None:
        tags[k] = v
    if (k := 'track_number', v := track.get(k))[1] is not None:
        tags[k] = v
    if (k := 'composers', v := track.get(k))[1] is not None:
        tags[k] = v
    if (k := 'copyright', v := track.get(k))[1] is not None:
        tags[k] = v
    if (k := 'isrc', v := track.get(k))[1] is not None:
        tags[k] = v
    if (k := 'explicit', v := track.get(k))[1] is not None:
        tags[k] = v
    if (k := 'bpm', v := track.get(k))[1] is not None:
        tags[k] = v

    tags['deezer_track_id'] = track['deezer']['id']
    tags['deezer_track_md5'] = track['deezer']['md5']
    tags['deezer_track_media_version'] = track['deezer']['media_version']

    album = track['album']

    if (k := 'title', v := album.get(k))[1] is not None:
        tags[f'album_{k}'] = v
    if (k := 'artists', v := album.get(k))[1] is not None:
        tags[f'album_{k}'] = [a['name'] for a in v]
    if (k := 'disk_count', v := album.get(k))[1] is not None:
        tags[f'album_{k}'] = v
    if (k := 'track_count', v := album.get(k))[1] is not None:
        tags[f'album_{k}'] = v
    if (k := 'date', v := album.get(k))[1] is not None:
        tags[f'album_{k}'] = v
    if (k := 'publisher', v := album.get(k))[1] is not None:
        tags[f'album_{k}'] = v
    if (k := 'ean', v := album.get(k))[1] is not None:
        tags[f'album_{k}'] = v

    tags['deezer_album_id'] = album['deezer']['id']
    tags['deezer_album_picture_md5'] = album['deezer']['picture_md5']

    return tags


def add_tags(f: mutagen.FileType, tags: dict):
    tags = tags.copy()

    match f:
        case flac.FLAC():
            if (v := tags.pop('title', None)) is not None:
                f['TITLE'] = v
            if (v := tags.pop('artists', None)) is not None:
                f['ARTIST'] = v
            if (v := tags.pop('album_title', None)) is not None:
                f['ALBUM'] = v
            if (v := tags.pop('album_artists', None)) is not None:
                f['ALBUMARTIST'] = f['ALBUM ARTIST'] = v
            if (v := tags.pop('album_disk_count', None)) is not None:
                f['DISCTOTAL'] = str(v)
            if (v := tags.pop('album_track_count', None)) is not None:
                f['TRACKTOTAL'] = str(v)
            if (v := tags.pop('disk_number', None)) is not None:
                f['DISCNUMBER'] = str(v)
            if (v := tags.pop('track_number', None)) is not None:
                f['TRACKNUMBER'] = str(v)
            if (v := tags.pop('album_date', None)) is not None:
                f['DATE'] = v.strftime('%Y-%m-%d')
            if (v := tags.pop('composers', None)) is not None:
                f['COMPOSER'] = v
            if (v := tags.pop('copyright', None)) is not None:
                f['COPYRIGHT'] = v
            if (v := tags.pop('album_publisher', None)) is not None:
                f['PUBLISHER'] = v
            if (v := tags.pop('isrc', None)) is not None:
                f['ISRC'] = v
            if (v := tags.pop('album_ean', None)) is not None:
                f['EAN'] = v
            if (v := tags.pop('explicit', None)) is not None:
                f['ITUNESADVISORY'] = str(int(v))
            if (v := tags.pop('bpm', None)) is not None:
                f['BPM'] = format(v, '.2f').rstrip('0').rstrip('.')
            for k, v in tags.items():
                f[k.upper()] = v
        case mp3.MP3():
            if (v := tags.pop('title', None)) is not None:
                f.tags.add(id3.TIT2(encoding=id3.Encoding.UTF8, text=v))
            if (v := tags.pop('artists', None)) is not None:
                f.tags.add(id3.TPE1(encoding=id3.Encoding.UTF8, text=v))
            if (v := tags.pop('album_title', None)) is not None:
                f.tags.add(id3.TALB(encoding=id3.Encoding.UTF8, text=v))
            if (v := tags.pop('album_artists', None)) is not None:
                f.tags.add(id3.TPE2(encoding=id3.Encoding.UTF8, text=v))
            if (v := tags.pop('disk_number', None)) is not None:
                f.tags.add(id3.TPOS(encoding=id3.Encoding.UTF8, text=str(v) + (f'/{total}' if (total := tags.pop('album_disk_count', None)) is not None else '')))
            if (v := tags.pop('track_number', None)) is not None:
                f.tags.add(id3.TRCK(encoding=id3.Encoding.UTF8, text=str(v) + (f'/{total}' if (total := tags.pop('album_track_count', None)) is not None else '')))
            if (v := tags.pop('album_date', None)) is not None:
                f.tags.add(id3.TDRC(encoding=id3.Encoding.UTF8, text=v.strftime('%Y-%m-%d')))
            if (v := tags.pop('composers', None)) is not None:
                f.tags.add(id3.TCOM(encoding=id3.Encoding.UTF8, text=v))
            if (v := tags.pop('copyright', None)) is not None:
                f.tags.add(id3.TCOP(encoding=id3.Encoding.UTF8, text=v))
            if (v := tags.pop('album_publisher', None)) is not None:
                f.tags.add(id3.TPUB(encoding=id3.Encoding.UTF8, text=v))
            if (v := tags.pop('isrc', None)) is not None:
                f.tags.add(id3.TSRC(encoding=id3.Encoding.UTF8, text=v))
            if (v := tags.pop('album_ean', None)) is not None:
                f.tags.add(id3.TXXX(encoding=id3.Encoding.UTF8, desc='EAN', text=v))
            if (v := tags.pop('explicit', None)) is not None:
                f.tags.add(id3.TXXX(encoding=id3.Encoding.UTF8, desc='ITUNESADVISORY', text=str(int(v))))
            if (v := tags.pop('bpm', None)) is not None:
                f.tags.add(id3.TBPM(encoding=id3.Encoding.UTF8, text=format(v, '.2f').rstrip('0').rstrip('.')))
            for k, v in tags.items():
                f.tags.add(id3.TXXX(encoding=id3.Encoding.UTF8, desc=k.upper(), text=str(v)))
        case _:
            raise NotImplementedError()

def add_tags_picture(f: mutagen.FileType, data: bytes, image: Image.Image, type_: id3.PictureType, description: str):
    match f:
        case flac.FLAC():
            picture = flac.Picture()
            picture.type = type_
            picture.mime = Image.MIME[image.format]
            picture.desc = description
            picture.width = image.size[0]
            picture.height = image.size[1]
            picture.depth = {'RGB': 24, 'RGBA': 32}[image.mode]
            picture.colors = 0
            picture.data = data
            f.add_picture(picture)
        case mp3.MP3():
            f.tags.add(id3.APIC(
                encoding=id3.Encoding.UTF8,
                mime=Image.MIME[image.format],
                type=type_,
                desc=description,
                data=data))
        case _:
            raise NotImplementedError()


class Settings(BaseSettings):
    track_decryption_secret: str
    client_id: str
    client_secret: str
    email: str
    password_md5: str

    class Config:
        env_prefix = 'deezl_'

settings = Settings()
app = FastAPI(title='deezl-api')
stack = AsyncExitStack()
deezer = None

@app.on_event('startup')
async def startup():
    session = create_deezer_client_session()
    await stack.enter_async_context(session)

    global deezer
    deezer = DeezerClient(settings, session)

@app.on_event('shutdown')
async def shutdown():
    await stack.aclose()

@app.get('/track/{id}')
async def track(id: str, full: bool = False):
    id_ = id

    gateway_track_page = await deezer.get_gateway_track_page(id_)
    gateway_track = gateway_track_page['DATA']

    gateway_album_page, api_track = await gather_cancel(
        deezer.get_gateway_album_page(gateway_track['ALB_ID']),
        deezer.get_api_track(gateway_track['SNG_ID'])
    )

    gateway_album = gateway_album_page['DATA']
    gateway_album_tracks = gateway_album_page['SONGS']['data']

    response = dict(
        track=parse_track(gateway_track, api_track),
        album=parse_album(gateway_album, gateway_album_tracks))

    if full:
        response.update(
            gateway_track=gateway_track,
            gateway_album=gateway_album,
            gateway_album_tracks=gateway_album_tracks,
            api_track=api_track)

    return response

@app.get('/album/{id}')
async def album(id: str, full: bool = False):
    id_ = id

    gateway_album_page = await deezer.get_gateway_album_page(id_)
    gateway_album = gateway_album_page['DATA']
    gateway_album_tracks = gateway_album_page['SONGS']['data']

    response = dict(
        album=parse_album(gateway_album, gateway_album_tracks),
        tracks=[parse_track(t, None) for t in gateway_album_tracks])

    if full:
        response.update(
            gateway_album=gateway_album,
            gateway_album_tracks=gateway_album_tracks)

    return response

@app.get('/playlist/{id}')
async def playlist(id: str, full: bool = False):
    id_ = id

    gateway_playlist_page = await deezer.get_gateway_playlist_page(id_)
    gateway_playlist = gateway_playlist_page['DATA']
    gateway_playlist_tracks = gateway_playlist_page['SONGS']['data']

    response = dict(
        playlist=parse_playlist(gateway_playlist),
        tracks=[parse_track(t, None) for t in gateway_playlist_tracks])

    if full:
        response.update(
            gateway_playlist=gateway_playlist,
            gateway_playlist_tracks=gateway_playlist_tracks)

    return response

@app.get('/search')
async def search(query: str, type: str, index: int, limit: int, full: bool = False):
    type_ = type

    gateway_results = await deezer.get_gateway_search_results(query, type_.upper(), index, limit)

    match type_:
        case 'track':
            data = [parse_track(d, None) for d in gateway_results['data']]
        case 'album':
            data = [parse_album(d, None) for d in gateway_results['data']]
        case 'playlist':
            data = [parse_playlist(d) for d in gateway_results['data']]
        case _:
            raise NotImplementedError()

    response = dict(
        results=dict(
            total=gateway_results['total'],
            next=gateway_results.get('next', 0),
            data=data))

    if full:
        response.update(
            gateway_results=gateway_results)

    return response

@alru_cache(maxsize=32)
async def download_gateway_track_album_cover(md5: bytes, size: tuple[int, int], format_: str) -> bytes:
    url = create_deezer_image_url('cover', md5, size, None, 100, False, format_)
    return await deezer.download_image(url)

@app.get('/track/{id}/download')
async def download(id: str, format: str, cover_format: str, cover_size: str):
    id_ = id
    format_ = format

    gateway_track_page = await deezer.get_gateway_track_page(id_)
    gateway_track = gateway_track_page['DATA']

    gateway_album_page, api_track, track_data, cover_data = await gather_cancel(
        deezer.get_gateway_album_page(gateway_track['ALB_ID']),
        deezer.get_api_track(gateway_track['SNG_ID']),
        deezer.download_track(gateway_track['SNG_ID'], gateway_track['TRACK_TOKEN'], format_),
        download_gateway_track_album_cover(bytes.fromhex(gateway_track['ALB_PICTURE']), tuple(map(int, cover_size.split('x', 1))), cover_format)
    )

    gateway_album = gateway_album_page['DATA']
    gateway_album_tracks = gateway_album_page['SONGS']['data']

    tags = create_track_tags({**parse_track(gateway_track, api_track), 'album': parse_album(gateway_album, gateway_album_tracks)})

    cover_image = Image.open(BytesIO(cover_data))
    if cover_image.mode == 'RGBA' and (255, 255) == cover_image.getchannel('A').getextrema():
        cover_image = cover_image.convert('RGB')
        output = BytesIO()
        cover_image.save(output, cover_format)
        cover_data = output.getvalue()
    cover_image.format = cover_format.replace('jpg', 'jpeg').upper()

    match format_.partition('_')[0]:
        case 'FLAC':
            f = flac.FLAC(BytesIO(track_data))
            f.clear()
            f.clear_pictures()
        case 'MP3':
            f = mp3.MP3(BytesIO(track_data))
            f.clear()
        case _:
            raise NotImplementedError()

    if f.tags is None:
        f.add_tags()
    add_tags(f, tags)
    add_tags_picture(f, cover_data, cover_image, id3.PictureType.COVER_FRONT, '')

    output = BytesIO(track_data)
    f.save(output)
    track_data = output.getvalue()

    return Response(content=track_data)
