import re
import itertools
import hashlib
import asyncio
from typing import AsyncIterator
import aiohttp
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend


def create_deezer_client_session() -> aiohttp.ClientSession:
    return aiohttp.ClientSession(
        skip_auto_headers=['User-Agent'],
        headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.110 Safari/537.36',
            'Cache-Control': 'max-age=0',
            'Accept': '*/*',
            'Accept-Language': 'en-US,en;q=0.5',
        })


async def login_deezer_session(session: aiohttp.ClientSession, email: str, password_md5: bytes, client_id: str, client_secret: str):
    password_md5 = password_md5.hex()

    async with session.get(
            'https://api.deezer.com/auth/token',
            params={
                'app_id': client_id,
                'login': email,
                'password': password_md5,
                'hash': hashlib.md5(''.join([client_id, email, password_md5, client_secret]).encode()).hexdigest()
            }) as response:
        response.raise_for_status()
        response = await response.json()

    if 'error' in response:
        raise Exception(response)

    async with session.get(
            'https://api.deezer.com/platform/generic/track/3117931',
            headers={
                'Authorization': f'''Bearer {response['access_token']}'''
            }) as response:
        response.raise_for_status()


async def call_deezer_gateway(session: aiohttp.ClientSession, method: str, data: dict, api_token: str | None) -> dict:
    async with session.post(
            'https://www.deezer.com/ajax/gw-light.php',
            params={
                'api_version': '1.0',
                'api_token': 'null' if api_token is None else api_token,
                'input': 3,
                'method': method
            },
            json=data) as response:
        response.raise_for_status()
        response = await response.json()

    if response['error']:
        raise Exception(response)
    return response['results']


async def call_deezer_api(session: aiohttp.ClientSession, path: str) -> dict:
    async with session.get(f'https://api.deezer.com/2.0/{path}') as response:
        response.raise_for_status()
        response = await response.json()

    if 'error' in response:
        raise Exception(response)
    return response


async def get_deezer_track_file_url(session: aiohttp.ClientSession, track_token: str, format_: str, license_token: str) -> str:
    async with session.post(
            'https://media.deezer.com/v1/get_url',
            json={
                'license_token': license_token,
                'media': [
                    {
                        'type': 'FULL',
                        'formats': [
                            {'cipher': 'BF_CBC_STRIPE', 'format': format_}
                        ]
                    }
                ],
                'track_tokens': [track_token]
            }) as response:
        response.raise_for_status()
        response = await response.json()

    response = response['data'][0]
    if 'errors' in response:
        raise Exception(response)
    return response['media'][0]['sources'][0]['url']


async def decrypt_deezer_track_file_http_stream(track_id: str, stream: aiohttp.StreamReader, secret: bytes) -> AsyncIterator[bytes]:
    md5 = hashlib.md5(track_id.encode()).hexdigest().encode()
    key = bytes(t[0] ^ t[1] ^ t[2] for t in zip(secret, md5[:16], md5[16:]))
    iv = bytes(range(8))
    cipher = Cipher(algorithms.Blowfish(key), modes.CBC(iv), backend=default_backend())

    for i in itertools.count():
        try:
            chunk = await stream.readexactly(2048)
            if i % 3 == 0:
                decryptor = cipher.decryptor()
                chunk = decryptor.update(chunk) + decryptor.finalize()
            yield chunk
        except asyncio.IncompleteReadError as e:
            yield e.partial
            break


def create_deezer_image_url(type_: str, md5: bytes, size: tuple[int, int], background_color: tuple[int, int, int] | None, quality: int, fit: bool, format_: str) -> str:
    background_color = 'none' if background_color is None else bytes(background_color).hex()
    return f'https://e-cdns-images.dzcdn.net/images/{type_}/{md5.hex()}/{size[0]}x{size[1]}-{background_color}-{quality}-{int(fit)}-0.{format_}'
