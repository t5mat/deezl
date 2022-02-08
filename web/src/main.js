import {createApp} from 'vue'
import {createRouter, createWebHistory, RouterView} from 'vue-router'
import {createHead} from '@vueuse/head'
import './index.css'
import App from './app.vue'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {path: '/:category?/:query?', component: App}
  ]
})

router.beforeEach((to, from) => {
  if (!['track', 'album', 'playlist'].includes(to.params.category)) {
    return '/track'
  }
})

const head = createHead()

const app = createApp(RouterView)
app.use(router)
app.use(head)
app.mount('#app')
