import {createApp} from 'vue'
import {createRouter, createWebHistory, RouterView} from 'vue-router'
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

router.afterEach((to) => {
  if (to.params.query.trim().length === 0) {
    window.document.title = 'deezl'
  } else {
    window.document.title = `${to.params.query} - deezl`
  }
})

const app = createApp(RouterView)
app.use(router)
app.mount('#app')
