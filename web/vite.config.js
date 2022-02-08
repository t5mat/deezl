import {defineConfig} from 'vite'
import {resolve} from 'path'
import Vue from '@vitejs/plugin-vue'
import Icons from 'unplugin-icons/vite'
import IconsResolver from 'unplugin-icons/resolver'
import Components from 'unplugin-vue-components/vite'

export default defineConfig({
  plugins: [
    Vue(),
    Icons(),
    Components({
      resolvers: [
        IconsResolver()
      ]
    })
  ],
  resolve: {
    alias: {'@': resolve(__dirname, 'src')},
  }
})
