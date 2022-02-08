<template>

<li class="flex flex-row items-center text-zinc-200">
  <div class="flex-shrink-0">
    <a :href="url" target="_blank">
      <img class="w-[50px] h-[50px]" :src="deezer.createImageUrl('cover', data.album.deezer.picture_md5, ITEM_IMAGE_CONFIG)"/>
    </a>
  </div>
  <div class="ml-3 basis-[100%] sm:basis-[90%] md:basis-[55%] min-w-0 space-y-0.5 break-words">
    <div class="leading-snug">
      <a class="align-middle text-zinc-200 hover:underline" :class="{'mr-2': data.explicit}" :href="url" target="_blank">
        {{ data.title }}
      </a>
      <span v-if="data.explicit" class="pointer-events-none inline-flex items-center -my-10 -mr-8 p-1 transform origin-left scale-[0.6] rounded align-middle font-bold text-zinc-800 bg-zinc-300">
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
  <div class="ml-4 basis-[45%] hidden min-w-0 md:block text-sm text-zinc-200 text-opacity-70">
    <a class="hover:underline" :href="deezer.createAlbumUrl(data.album.deezer.id)" target="_blank">
      {{ data.album.title }}
    </a>
  </div>
  <div class="ml-4 basis-[10%] hidden min-w-0 sm:flex items-center justify-end text-sm text-zinc-200 text-opacity-70 tabular-nums tracking-tight">
    <i-bx:bx-time class="flex-shrink-0 text-xs mr-1"/>
    {{ formatSecondsDuration(data.duration_seconds) }}
  </div>
  <div class="ml-7 flex-shrink-0 flex" v-if="data.deezer.preview_url !== null">
    <popover as="template">
      <popover-button ref="trigger">
        <i-fontisto:preview class="text-sm"/>
      </popover-button>
      <div ref="container" class="z-30 px-2 w-[25rem] max-w-[80%]">
        <popover-panel class="flex p-3 bg-zinc-700 rounded shadow-[0_0_7px_2px] shadow-zinc-900 outline-none">
          <audio :src="data.deezer.preview_url" controls class="w-full outline-none"/>
        </popover-panel>
      </div>
    </popover>
  </div>
  <div class="ml-4 flex-shrink-0 flex">
    <formats-menu :singleTrack="true" :tracks="[data]" @clickFormat="formatsClick"/>
  </div>
</li>

</template>

<script setup>

import {computed, onMounted, onUnmounted} from 'vue'
import {Popover, PopoverButton, PopoverPanel} from '@headlessui/vue'
import * as deezer from './deezer'
import {formatDate, formatSecondsDuration, usePopper} from './common'
import {ITEM_IMAGE_CONFIG} from './config'
import FormatsMenu from './formats-menu.vue'

const props = defineProps(['data'])
const emit = defineEmits(['download'])

const [trigger, container, popper] = usePopper({
  placement: 'bottom',
  modifiers: [{
    name: 'offset', options: {offset: [0, 3]}
  }],
})

function formatsClick(format) {
  emit('download', {format, track: props.data})
}

const url = computed(() => deezer.createTrackUrl(props.data.deezer.id))

const observer = new ResizeObserver(async ([entry]) => {
  popper.value.update()
})

onMounted(() => {
  observer.observe(container.value)
})

onUnmounted(() => {
  observer.disconnect()
})

</script>
