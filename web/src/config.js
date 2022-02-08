export const ITEMS_LOAD_SIZE = 20
export const ITEM_IMAGE_CONFIG = {size: [64, 64], quality: 100, format: 'jpg'}


export const DOWNLOAD_COVER_IMAGE_CONFIG = {size: [1000, 1000], quality: 100, format: 'png'}
export const DOWNLOAD_PART_SIZE_BYTES = 1024 * 1024 * 500

export function createTrackBasename(track) {
  return `${track.artists.map((a) => a.name).join(', ')} - ${track.title}`
}

export function createAlbumTrackBasename(album, track) {
  return (album.disk_count > 1 ? `CD${track.disk_number} - ` : '') + `${String(track.track_number).padStart(2, '0')} - ${track.title}`
}

export function createPlaylistTrackBasename(playlist, track) {
  return `${track.artists.map((a) => a.name).join(', ')} - ${track.title}`
}

export function createAlbumBasename(album) {
  return `${album.artists.map((a) => a.name).join(', ')} - ${album.title}`
}

export function createPlaylistBasename(playlist) {
  return `${playlist.title}`
}

export function createArchiveTrackBasename(basename, duplicate) {
  return (duplicate === 0 ? basename : `${basename}.${duplicate}`)
}

export function createArchiveFilename(basename, part) {
  return (part === 0 ? `${basename}.zip` : `${basename}.part${part}.zip`)
}


import axios from 'axios'

export const API = axios.create({baseURL: import.meta.env.BASE_URL + 'api'})
