import { createRouter, createWebHistory } from 'vue-router'
import ChatContainer from '@/components/ChatContainer.vue'
import AboutPage from '@/pages/AboutPage.vue'
import FAQPage from '@/pages/FAQPage.vue'


const routes = [
  { path: '/', component: ChatContainer },
  { path: '/about', component: AboutPage },
  { path: '/faq', component: FAQPage },

]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

export default router 