import sanitizeFilename from 'sanitize-filename'
import FileSaver from 'file-saver'
import axios from 'axios'
import * as deezer from './deezer'
import {zip} from './common'
import {API, DOWNLOAD_COVER_IMAGE_CONFIG} from './config'
import * as config from './config'

export function useDownloader() {
  let queueKey = 0
  const queue = shallowReactive([])

  let errorsKey = 0
  const errors = shallowReactive([])

  let running = false

  function cancelDownload(download) {
    const i = queue.findIndex((d) => d.key === download.key)
    if (i != -1) {
      queue[i].abort.abort()
      queue.splice(i, 1)
    }
  }

  function dismissError(error) {
    const i = errors.findIndex((d) => d.key === error.key)
    if (i != -1) {
      errors.splice(i, 1)
    }
  }

  function downloadTrack({format, track}) {
    const url = deezer.createTrackUrl(track.deezer.id)
    const trackBasename = sanitizeFilename(config.createTrackBasename(track))
    const files = [[track, format, trackBasename]]
    const displayFilename = `${trackBasename}.${deezer.FORMATS_EXTENSIONS[format]}`

    queue.push({key: ++queueKey, abort: new AbortController(), progress: ref(0), archive: false, url, files, displayFilename})
    if (!running) {
      run()
    }
  }

  function downloadAlbum({format, album, tracks}) {
    const url = deezer.createAlbumUrl(album.deezer.id)
    const basename = sanitizeFilename(config.createAlbumBasename(album))

    const relevantFormats = deezer.FORMATS.slice(deezer.FORMATS.indexOf(format))
    const files = tracks.reduce((files, track) => {
      for (const trackFormat of relevantFormats) {
        if (track.deezer.formats.hasOwnProperty(trackFormat)) {
          const trackBasename = sanitizeFilename(config.createAlbumTrackBasename(album, track))
          files.push([track, trackFormat, trackBasename])
          return files
        }
      }
      return files
    }, [])

    const displayFilename = config.createArchiveFilename(basename, 0)

    queue.push({key: ++queueKey, abort: new AbortController(), progress: ref(0), archive: true, url, basename, files, displayFilename})
    if (!running) {
      run()
    }
  }

  function downloadPlaylist({format, playlist, tracks}) {
    const url = deezer.createPlaylistUrl(playlist.deezer.id)
    const basename = sanitizeFilename(config.createPlaylistBasename(playlist))

    const relevantFormats = deezer.FORMATS.slice(deezer.FORMATS.indexOf(format))
    const files = tracks.reduce((files, track) => {
      for (const trackFormat of relevantFormats) {
        if (track.deezer.formats.hasOwnProperty(trackFormat)) {
          const trackBasename = sanitizeFilename(config.createPlaylistTrackBasename(playlist, track))
          files.push([track, trackFormat, trackBasename])
          return files
        }
      }
      return files
    }, [])

    const displayFilename = config.createArchiveFilename(basename, 0)

    queue.push({key: ++queueKey, abort: new AbortController(), progress: ref(0), archive: true, url, basename, files, displayFilename})
    if (!running) {
      run()
    }
  }

  async function run() {
    running = true
    while (queue.length > 0) {
      const download = queue[0]

      let files = {}
      let part = 0

      for (const [i, [track, trackFormat, trackBasename]] of download.files.entries()) {
        let trackData

        try {
          ;({data: trackData} = await API.get(`/track/${track.deezer.id}/download`, {signal: download.abort.signal, params: {cover_format: DOWNLOAD_COVER_IMAGE_CONFIG.format, cover_size: DOWNLOAD_COVER_IMAGE_CONFIG.size.join('x'), format: trackFormat}, responseType: 'arraybuffer', onDownloadProgress: (e) => {
            download.progress.value = (i + (e.loaded / e.total)) / download.files.length
          }}))
        } catch (e) {
          if (axios.isCancel(e)) {
            files = null
            break
          }

          errors.push({
            key: ++errorsKey,
            url: download.url,
            trackUrl: deezer.createTrackUrl(track.deezer.id),
            trackFilename: `${trackBasename}.${deezer.FORMATS_EXTENSIONS[trackFormat]}`,
            displayFilename: download.displayFilename
          })

          continue
        }

        trackData = new Uint8Array(trackData)

        if (!download.archive) {
          files[`${trackBasename}.${deezer.FORMATS_EXTENSIONS[trackFormat]}`] = trackData
          break
        }

        let trackFilename
        let duplicate = 0
        do {
          trackFilename = `${config.createArchiveTrackBasename(trackBasename, duplicate++)}.${deezer.FORMATS_EXTENSIONS[trackFormat]}`
        } while (trackBasename !== '' && files.hasOwnProperty(trackFilename))

        files[trackFilename] = trackData

        if (i < download.files.length - 1 && Object.values(files).reduce((sum, file) => sum + file.length, 0) > config.DOWNLOAD_PART_SIZE_BYTES) {
          FileSaver.saveAs(new Blob([await zip(files)]), config.createArchiveFilename(download.basename, ++part))
          files = {}
        }
      }

      if (files) {
        if (!download.archive) {
          FileSaver.saveAs(new Blob([Object.values(files)[0]]), Object.keys(files)[0])
        } else if (Object.keys(files).length > 0) {
          FileSaver.saveAs(new Blob([await zip(files)]), config.createArchiveFilename(download.basename, part))
        }
      }

      const i = queue.findIndex((d) => d.key === download.key)
      if (i != -1) {
        queue.splice(i, 1)
      }
    }
    running = false
  }

  return {queue, errors, cancelDownload, dismissError, downloadTrack, downloadAlbum, downloadPlaylist}
}
