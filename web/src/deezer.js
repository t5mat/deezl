export const FORMATS = [
  'FLAC',
  'MP3_320',
  'MP3_256',
  'MP3_128',
  'MP3_64'
]

export const FORMATS_DISPLAY_NAMES = {
  'FLAC': 'FLAC',
  'MP3_320': 'MP3 320kbps',
  'MP3_256': 'MP3 256kbps',
  'MP3_128': 'MP3 128kbps',
  'MP3_64': 'MP3 64kbps'
}

export const FORMATS_EXTENSIONS = {
  'FLAC': 'flac',
  'MP3_320': 'mp3',
  'MP3_256': 'mp3',
  'MP3_128': 'mp3',
  'MP3_64': 'mp3'
}

export function createTrackUrl(id) {
  return `https://www.deezer.com/track/${id}`
}

export function createArtistUrl(id) {
  return `https://www.deezer.com/artist/${id}`
}

export function createAlbumUrl(id) {
  return `https://www.deezer.com/album/${id}`
}

export function createPlaylistUrl(id) {
  return `https://www.deezer.com/playlist/${id}`
}

export function createProfileUrl(id) {
  return `https://www.deezer.com/profile/${id}`
}

export function createImageUrl(type, md5, {size, format, quality=100}) {
  return `https://e-cdns-images.dzcdn.net/images/${type}/${md5}/${size.join('x')}-none-${quality}-0-0.${format}`
}
