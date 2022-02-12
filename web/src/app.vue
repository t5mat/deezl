<template>

<div class="sticky top-0 inset-x-0 z-40 pointer-events-none">
  <div class="pointer-events-auto header-bg px-4 md:px-6">
    <div class="max-w-6xl mx-auto py-2 sm:py-2.5 sm:flex sm:items-center">
      <div class="flex-grow relative">
        <button class="absolute inset-y-0 left-0 ml-3 p-1 flex items-center" @click="search()">
          <div class="text-xs i-fa:search"></div>
        </button>
        <input class="rounded-md block w-full text-zinc-300 focus:text-zinc-100 bg-zinc-700 focus:bg-zinc-600 py-2 pl-10 pr-3 leading-5 placeholder-white focus:placeholder-white text-sm" id="search" placeholder="Search" type="search" name="search" v-model="query" v-on:keydown.enter="search()" autofocus/>
      </div>
      <nav class="flex space-x-1.5 sm:ml-2.5 mt-2 sm:mt-0 self-stretch flex items-center">
        <router-link class="py-2 sm:px-3 sm:py-0 h-full text-sm rounded-md flex-grow sm:flex-grow-0 flex items-center justify-center font-medium" :class="[route.params.category !== category ? 'text-zinc-400 hover:text-zinc-100' : 'bg-zinc-200 font-semibold text-zinc-800']" :to="{params: {category, query}}" v-for="category in ['track', 'album', 'playlist']">
          {{ {'track': 'Tracks', 'album': 'Albums', 'playlist': 'Playlists'}[category] }}
        </router-link>
      </nav>
    </div>
  </div>

  <div class="pointer-events-auto bg-amber-700 px-4 md:px-6" v-show="queue.length > 0">
    <div class="max-w-6xl mx-auto py-4 break-words">
      <div :class="{'mb-3': queue.length > 1}" v-for="download in queue.slice(0, 1)" :key="download.key">
        <div class="leading-snug">
          <div class="mr-1 inline-block align-middle i-eos-icons:loading"></div>
          <span class="align-middle font-bold">Downloading&nbsp;&nbsp;</span>
          <a class="align-middle mr-1 hover:underline" :href="download.url" target="_blank">{{ download.displayFilename }}</a>
          <button @click="cancelDownload(download)" class="align-middle"><div class="inline-block align-middle text-lg i-bi:x"></div></button>
        </div>
        <div class="mt-1.5 bg-gray-200 rounded h-2.5 dark:bg-gray-700 shadow-lg mb-0.5">
          <div class="bg-blue-500 h-2.5 rounded" :style="{'width': `${download.progress.value * 100}%`}"></div>
        </div>
      </div>
      <div class="text-sm mt-0.5" v-for="download in queue.slice(1)" :key="download.key">
        <div class="mr-1 inline-block align-middle i-ph:queue-light"></div>
        <span class="align-middle font-bold">Queued&nbsp;&nbsp;</span>
        <a class="align-middle mr-1 hover:underline" :href="download.url" target="_blank">{{ download.displayFilename }}</a>
        <button @click="cancelDownload(download)" class="align-middle"><div class="inline-block align-middle text-lg i-bi:x"></div></button>
      </div>
    </div>
  </div>

  <div class="pointer-events-auto bg-red-800 px-4 md:px-6" v-show="errors.length > 0">
    <div class="max-w-6xl mx-auto py-4 space-y-1 break-words">
      <div class="text-sm" v-for="error in errors.slice().reverse()" :key="error.key">
        <div class="mr-1 inline-block align-middle i-ci:error-outline"></div>
        <span class="align-middle font-bold">Error downloading&nbsp;&nbsp;</span>
        <a class="align-middle hover:underline" :href="error.url" target="_blank">{{ error.displayFilename }}</a>
        <span class="align-middle mr-1" v-if="error.trackFilename !== ''">- <a class="hover:underline" :href="error.trackUrl" target="_blank">{{ error.trackFilename }}</a></span>
        <button @click="dismissError(error)" class="align-middle"><div class="inline-block align-middle text-lg i-bi:x"></div></button>
      </div>
    </div>
  </div>

  <div class="bg-gradient-to-b from-zinc-900 opacity-70 h-5 -mb-5"></div>
</div>

<div class="px-4 md:px-6">
  <div class="my-6 max-w-6xl mx-auto">
    <template v-if="total !== undefined">
      <div class="text-xl font-bold text-zinc-300">
        {{ total }} {{ {'track': ['track', 'tracks'], 'album': ['album', 'albums'], 'playlist': ['playlist', 'playlists']}[route.params.category][+(total !== 1)] }} found.
      </div>
      <ul class="divide-y items-divider mt-4 -my-1.5">
        <template v-if="route.params.category === 'track'">
          <track-item class="py-1.5" v-for="item in items" :key="item.deezer.id" :data="item" @download="downloadTrack"></track-item>
        </template>
        <template v-else-if="route.params.category === 'album'">
          <album-item class="py-1.5" v-for="item in items" :key="item.deezer.id" :data="item" @download="downloadAlbum"></album-item>
        </template>
        <template v-else-if="route.params.category === 'playlist'">
          <playlist-item class="py-1.5" v-for="item in items" :key="item.deezer.id" :data="item" @download="downloadPlaylist"></playlist-item>
        </template>
      </ul>
    </template>
    <div class="relative">
      <div ref="intersect" class="absolute w-full -top-10 h-10 pointer-events-none"></div>
    </div>
    <template v-if="loading">
      <div class="mx-auto mt-6 w-6 h-6 i-eos-icons:loading" :class="{'mt-8': total === undefined}"></div>
    </template>
    <template v-else-if="error">
      <div class="mx-auto mt-6 w-6 h-6 i-ci:error-outline" :class="{'mt-8': total === undefined}"></div>
    </template>
  </div>
</div>

</template>

<style>

.header-bg {
  background: radial-gradient(at center, var(--color-zinc-900), var(--color-zinc-800));
  background-size: 150% 150%;
}

.items-divider > * {
  border-image: linear-gradient(to right, transparent, var(--color-zinc-800) 25% 75%, transparent);
  border-image-slice: 1;
}

</style>

<script setup>

import axios from 'axios'
import {API, ITEMS_LOAD_SIZE} from './config'
import {useDownloader} from './downloader'
import TrackItem from './track-item.vue'
import AlbumItem from './album-item.vue'
import PlaylistItem from './playlist-item.vue'

const router = useRouter()
const route = useRoute()

useHead({
  title: computed(() => {
    if (route.params.query.trim().length === 0) {
      return 'deezl'
    } else {
      return `${route.params.query} - deezl`
    }
  })
})


const {errors, queue, dismissError, cancelDownload, downloadTrack, downloadAlbum, downloadPlaylist} = useDownloader()

const items = shallowReactive([])
const total = ref(undefined)
const error = ref(false)
const loading = ref(false)
const intersect = ref(null)
let abort = new AbortController()
let next = -1

const observer = new IntersectionObserver(async ([entry]) => {
  if (next === -1 || !entry.isIntersecting) {
    return
  }

  observer.disconnect()
  loading.value = true

  if (route.params.query.trim().length === 0) {
    next = -1
  } else {
    try {
      const params = {
        query: route.params.query,
        type: route.params.category,
        index: next,
        limit: ITEMS_LOAD_SIZE
      }
      const {data} = await API.get('/search', {signal: abort.signal, params})

      next = (data.results.data.length < params.limit) ? -1 : data.results.next
      total.value = data.results.total
      items.push(...data.results.data)
    } catch (e) {
      if (axios.isCancel(e)) {
        return
      }
      next = -1
      error.value = true
    }
  }

  loading.value = false
  observer.observe(intersect.value)
}, {})

const query = ref(route.params.query)

function search() {
  router.push({params: {query: query.value}})
}

onMounted(() => {
  watch(
    [() => route.params.category, () => route.params.query],
    ([c, q]) => {
      observer.disconnect()

      abort.abort()
      abort = new AbortController()

      query.value = q

      items.splice(0)
      total.value = undefined
      error.value = false
      loading.value = false
      next = 0

      observer.observe(intersect.value)
    },
    {immediate: true}
  )
})

onBeforeUnmount(() => {
  observer.disconnect()
})

</script>
