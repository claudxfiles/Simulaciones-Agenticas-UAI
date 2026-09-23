// Demo pública: sin gate de login. Si hay sesión Supabase, adjunta el
// access_token como Bearer a fetch('/api/...'); si no, pasa igual (el
// backend no exige el token, la demo funciona anónima).
import { createClient } from 'https://esm.sh/@supabase/supabase-js@2'
import { SUPABASE_URL, SUPABASE_ANON } from './supabase-config.js'

const supabase = createClient(SUPABASE_URL, SUPABASE_ANON)

async function init() {
  const originalFetch = window.fetch.bind(window)
  window.fetch = async (input, init = {}) => {
    const url = typeof input === 'string' ? input : input.url
    if (url.startsWith('/api/')) {
      const { data: { session: current } } = await supabase.auth.getSession()
      init.headers = { ...(init.headers || {}), Authorization: `Bearer ${current?.access_token ?? ''}` }
    }
    return originalFetch(input, init)
  }
  window.__logout = () => supabase.auth.signOut().then(() => (window.location.href = '/login.html'))

  await import('./main.js')
}

init()
