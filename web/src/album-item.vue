<template>

<li class="flex flex-row items-center text-zinc-200">
  <div class="flex-shrink-0">
    <a :href="url" target="_blank">
      <img class="w-[50px] h-[50px]" :src="deezer.createImageUrl('cover', data.deezer.picture_md5, ITEM_IMAGE_CONFIG)"/>
    </a>
  </div>
  <div class="ml-3 basis-[100%] min-w-0 space-y-0.5 break-words">
    <div class="leading-snug">
      <a class="align-middle text-zinc-200 hover:underline" :class="{'mr-2': data.explicit}" :href="url" target="_blank">
        {{ data.title }}
      </a>
      <span class="pointer-events-none select-none inline-flex items-center -my-10 -mr-8 p-1 transform origin-left scale-[0.6] rounded align-middle font-bold text-zinc-800 bg-zinc-300" v-if="data.explicit">
        EXPLICIT
      </span>
    </div>
    <div class="text-sm text-zinc-200 text-opacity-60 leading-tight">
      <template v-for="(artist, i) in data.artists">
        <template v-if="i > 0">,&nbsp;</template>
        <a class="align-middle hover:underline" :href="deezer.createArtistUrl(artist.deezer.id)" target="_blank">{{ artist.name }}</a>
      </template>
    </div>
  </div>
  <div class="ml-4 basis-[6.75rem] flex-shrink-0 min-w-0 hidden md:flex items-center text-sm text-zinc-200 text-opacity-70 tabular-nums tracking-tight">
    <i-clarity:date-line class="flex-shrink-0 text-xs mr-1"/>
    {{ formatDate(data.date) }}
  </div>
  <div class="ml-4 basis-[8rem] flex-shrink-0 min-w-0 hidden sm:flex items-center justify-end text-sm text-zinc-200 text-opacity-70 tabular-nums tracking-tight">
    <i-clarity:number-list-line class="flex-shrink-0 text-xs mr-1"/>
    {{ data.track_count }} {{ data.track_count === 1 ? 'track' : 'tracks' }}
  </div>
  <div class="ml-4 basis-[5rem] flex-shrink-0 min-w-0 flex sm:hidden items-center justify-end text-sm text-zinc-200 text-opacity-70 tabular-nums tracking-tight">
    <i-clarity:number-list-line class="flex-shrink-0 text-xs mr-1"/>
    {{ data.track_count }}
  </div>
  <div class="ml-7 flex-shrink-0 flex">
    <formats-menu :singleTrack="false" :tracks="tracks" @open="formatsOpen" @clickFormat="formatsClick"/>
  </div>
</li>

</template>

<script setup>

import {formatDate} from './common'
import * as deezer from './deezer'
import {ITEM_IMAGE_CONFIG, API} from './config'
import FormatsMenu from './formats-menu.vue'

const props = defineProps(['data'])
const emit = defineEmits(['download'])

let album
const tracks = ref(undefined)

let formatsLoad = false

async function formatsOpen() {
  if (formatsLoad) {
    return
  }
  formatsLoad = true

  let result
  try {
    result = await API.get(`/album/${props.data.deezer.id}`)
  } catch (e) {
    return
  }

  album = result.data.album
  tracks.value = result.data.tracks
}

function formatsClick(format) {
  emit('download', {format, album, tracks: tracks.value})
}

const url = computed(() => deezer.createAlbumUrl(props.data.deezer.id))

const tracksCount = computed(() => Object.keys(tracks.value).length)

</script>
