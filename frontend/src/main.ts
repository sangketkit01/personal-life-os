import { createApp } from 'vue'
import { createPinia } from 'pinia'
import router from './router'
import { initI18n } from './i18n'
import { initTheme } from './theme'
import './style.css'
import App from './App.vue'

const app = createApp(App)
const pinia = createPinia()

app.use(pinia)
app.use(router)

app.mount('#app')

// Start the bilingual DOM translator + theme engine after the app renders
initI18n()
initTheme()
