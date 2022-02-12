import '@unocss/reset/tailwind.css'
import 'uno.css'
import './main.css'

import {createApp} from 'vue'
import {createRouter, createWebHistory, RouterView} from 'vue-router'
import {createHead} from '@vueuse/head'
import App from './app.vue'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {path: '/:category?/:query?', component: App}
  ]
})

router.beforeEach((to, from) => {
  if (!['tracks', 'albums', 'playlists'].includes(to.params.category)) {
    return '/tracks'
  }
})

const head = createHead()

const app = createApp(RouterView)
app.use(router)
app.use(head)
app.mount('#app')
