<h1 align="center">deezl</h1>

<p align="center">
<a href="https://user-images.githubusercontent.com/16616463/153737858-1ce5e5dc-2e35-4f9b-8440-a7bb7d9ba10e.mp4">
<b>Video</b>
</a>
</p>

<p align="center">
<a href="https://user-images.githubusercontent.com/16616463/153737858-1ce5e5dc-2e35-4f9b-8440-a7bb7d9ba10e.mp4">
<img src="https://user-images.githubusercontent.com/16616463/153736389-5deb3fbe-3d94-429e-824d-c059dc5865a9.png">
</a>
</p>

> **⚠️ WARNING: THIS PROJECT IS NOT ACTIVELY MAINTAINED AND IS PROVIDED AS-IS**

- **Search music - tracks, albums, playlists**

- **Download FLAC/MP3 music files (depending on your account plan)**
	- Download tracks, albums, playlists
	- Downloaded files are fully tagged (+embedded cover art)
	- Multiple downloads can be queued

- **Preview tracks before downloading**

- **Responsive UI - designed for desktop & mobile**

## Installation/Usage

> **⚠️ WARNING: Use with caution if your data transfer/bandwidth is limited**

You need:

- A Deezer account (need HiFi for FLACs)
- A Deezer client ID, client secret
- The track decryption key. This is not included for legal reasons

Dockerfiles are provided for development & production. If you wish to run this without Docker, take a look inside either Dockerfile for usage & dependencies.

### Running in production

- `PUBLIC_BASE` (default `/`) - [base URL/path](https://vitejs.dev/config/#base) the server is publicly served on

```sh
DOCKER_BUILDKIT=1 docker build -f Dockerfile . -t deezl \
	--build-arg PUBLIC_BASE=/

docker run --rm -it --name deezl -p 1313:80 \
	-e DEEZL_TRACK_DECRYPTION_SECRET=<...> \
	-e DEEZL_CLIENT_ID=<...> \
	-e DEEZL_CLIENT_SECRET=<...> \
	-e DEEZL_EMAIL=<...> \
	-e DEEZL_PASSWORD_MD5=<...> \
	deezl
```

### Running in development

Both frontend & backend will auto-reload/restart when modified.

- `PUBLIC_PORT` - port the server is publicly served on
- `PUBLIC_BASE` (default `/`) - [base URL/path](https://vitejs.dev/config/#base) the server is publicly served on

```sh
DOCKER_BUILDKIT=1 docker build -f dev.Dockerfile . -t deezl-dev

(cd web/; npm i)

docker run --rm -it --name deezl-dev -p 1313:80 \
	-v $(pwd):/app:rw \
	-e PUBLIC_PORT=1313 \
	-e PUBLIC_BASE=/ \
	-e DEEZL_TRACK_DECRYPTION_SECRET=<...> \
	-e DEEZL_CLIENT_ID=<...> \
	-e DEEZL_CLIENT_SECRET=<...> \
	-e DEEZL_EMAIL=<...> \
	-e DEEZL_PASSWORD_MD5=<...> \
	deezl-dev
```

## Technical Overview

### Frontend

Built with [Vite](https://vitejs.dev/), [Vue 3](https://vuejs.org/) and [UnoCSS](https://github.com/unocss/unocss).

Track files are downloaded as blobs, then saved using [FileSaver](https://github.com/eligrey/FileSaver.js/). For albums/playlists, tracks are first downloaded, then zipped in the browser using [fflate](https://github.com/101arrowz/fflate). Zip files are downloaded in multiple parts if too big.

### Backend

The API server uses [FastAPI](https://github.com/tiangolo/fastapi).

Endpoints (summarized):
- **Search, track/album/playlist info** - these call Deezer APIs, parse the responses and return the parsed data. Adding `?full=1` will make responses also include the unparsed Deezer responses, useful sometimes
- **Download a single track** - downloads an encrypted track file → decrypts it → tags it, then returns it

#### Deezer client

`deezer.py` is a minimal standalone Deezer client (gateway, public API, track url fetching, track decryption). It is a bit low-level but provides access to all relevant APIs.

A more high-level (and rate limiting) client is implemented on top of it in `api.py`. It is used by the API server.
