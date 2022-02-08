import {defineConfig} from 'vite'
import {resolve} from 'path'
import Vue from '@vitejs/plugin-vue'
import Icons from 'unplugin-icons/vite'
import IconsResolver from 'unplugin-icons/resolver'
import Components from 'unplugin-vue-components/vite'
import {HeadlessUiResolver} from 'unplugin-vue-components/resolvers'

export default defineConfig({
  plugins: [
    Vue(),
    Icons(),
    Components({
      resolvers: [
        HeadlessUiResolver({prefix: 'Headless'}),
        IconsResolver()
      ]
    })
  ],
  resolve: {
    alias: {'@': resolve(__dirname, 'src')},
  }
})
