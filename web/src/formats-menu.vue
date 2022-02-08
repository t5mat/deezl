<template>

<menu_ v-slot="{open}">
  <prop-watcher :data="open" @change="openChanged"/>
  <menu-button ref="trigger">
    <i-fe:download class="text-lg"/>
  </menu-button>
  <div ref="container" class="z-30 px-2">
    <menu-items class="flex flex-col py-1.5 bg-zinc-700 rounded shadow-[0_0_7px_2px] shadow-zinc-900 outline-none divide-y divide-zinc-600 font-mono tracking-tight">
      <template v-if="tracks === undefined">
        <i-eos-icons:loading class="mx-4 my-2 text-lg"/>
      </template>
      <template v-else-if="tracks === null">
        <i-ci:error-outline class="mx-4 my-2 text-lg"/>
      </template>
      <template v-else-if="sortedTotals.length === 0">
        <div class="mx-4 my-2 text-sm">No avaliable formats</div>
      </template>
      <template v-else>
        <template v-for="[format, totals] of sortedTotals">
          <menu-item as="template" v-slot="{active}" v-if="totals[format] !== undefined">
            <button class="px-4 py-1.5 flex flex-col" :class="{['text-zinc-900 bg-zinc-300']: active}" @click="clickFormat(format)">
              <div class="flex items-center font-bold">
                <template v-if="singleTrack">
                  <i-mi:document-empty class="text-xs mr-2"/>
                </template>
                <template v-else>
                  <i-mi:archive class="text-xs mr-2"/>
                </template>
                <div>
                  {{ deezer.FORMATS_DISPLAY_NAMES[format] }}
                  <template v-if="totals[format][0] != tracksCount">
                    ({{ totals[format][0] }}/{{ tracksCount }})
                  </template>
                  ~{{ filesize(totals[format][1]) }}
                </div>
              </div>
              <template v-for="[f, [c, s]] of sortByFormat(totals)">
                <div class="ml-[1.4rem]" v-if="f != format">
                  + {{ deezer.FORMATS_DISPLAY_NAMES[f] }}
                  ({{ c }}/{{ tracksCount }})
                  ~{{ filesize(s) }}
                </div>
              </template>
            </button>
          </menu-item>
        </template>
      </template>
    </menu-items>
  </div>
</menu_>

</template>

<script setup>

import filesize from 'filesize'
import {computed, markRaw, onMounted, onUnmounted} from 'vue'
import {Menu as Menu_, MenuButton, MenuItems, MenuItem} from '@headlessui/vue'
import {usePopper} from './common'
import * as deezer from './deezer'
import PropWatcher from './prop-watcher.vue'

const props = defineProps(['singleTrack', 'tracks'])
const emit = defineEmits(['open', 'clickFormat'])

const [trigger, container, popper] = usePopper({
  placement: 'bottom',
  modifiers: [{
    name: 'offset', options: {offset: [0, 3]}
  }],
})

async function openChanged([value, oldValue]) {
  if (value) {
    emit('open')
  }
}

async function clickFormat(format) {
  emit('clickFormat', format)
}

function sortByFormat(formats) {
  return deezer.FORMATS.filter((f) => formats.hasOwnProperty(f)).map((f) => [f, formats[f]])
}

const tracksCount = computed(() => Object.keys(props.tracks).length)

const sortedTotals = computed(() => {
  let totals = {}

  for (const format of deezer.FORMATS) {
    totals[format] = {}

    let relevantFormats = deezer.FORMATS.slice(deezer.FORMATS.indexOf(format))

    for (const track of props.tracks) {
      for (const f of relevantFormats) {
        if (track.deezer.formats.hasOwnProperty(f)) {
          if (!totals[format].hasOwnProperty(f)) {
            totals[format][f] = [1, track.deezer.formats[f]]
          } else {
            ++totals[format][f][0]
            totals[format][f][1] += track.deezer.formats[f]
          }
          break
        }
      }
    }

    if (!totals[format]) {
      delete totals[format]
    }
  }

  return markRaw(sortByFormat(totals))
})

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
