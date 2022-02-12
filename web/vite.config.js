import {defineConfig} from 'vite'
import {resolve} from 'path'
import UnoCss from 'unocss/vite'
import presetWind from '@unocss/preset-wind'
import {presetIcons} from 'unocss'
import Vue from '@vitejs/plugin-vue'
import AutoImport from 'unplugin-auto-import/vite'
import Components from 'unplugin-vue-components/vite'
import {HeadlessUiResolver} from 'unplugin-vue-components/resolvers'

export default defineConfig({
  plugins: [
    UnoCss({
      theme: {
        fontFamily: {
          sans: 'Inter',
          mono: 'Fira Code'
        },
      },
      presets: [
        presetWind(),
        presetIcons()
      ]
    }),
    Vue(),
    AutoImport({
      imports: [
        'vue',
        'vue-router',
        '@vueuse/core',
        '@vueuse/head'
      ]
    }),
    Components({
      resolvers: [
        HeadlessUiResolver({prefix: 'Headless'})
      ]
    })
  ],
  resolve: {
    alias: {'@': resolve(__dirname, 'src')},
  }
})
