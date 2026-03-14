// src/composables/useApi.js
import { ref } from 'vue'

export function useApi() {
  async function api(url, opts = {}) {
    const token = localStorage.getItem('admin_token') || ''
    const headers = { 'Content-Type': 'application/json' }
    if (token) {
      headers['Authorization'] = `Bearer ${token}`
    }

    const res = await fetch(url, {
      headers,
      ...opts,
      body: opts.body ? JSON.stringify(opts.body) : undefined
    })

    if (res.status === 401) {
      localStorage.removeItem('admin_token')
      window.dispatchEvent(new CustomEvent('admin-auth-failed'))
    }

    const data = await res.json()
    if (!res.ok) throw new Error(data.error || 'Request failed')
    return data
  }

  async function apiVerifyKey(key) {
    // We send the key in the header to verify via the before_request hook
    const res = await fetch('/admin/verify', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${key}`
      }
    })
    if (!res.ok) throw new Error('Invalid key')
    const data = await res.json()
    if (data.success) {
      localStorage.setItem('admin_token', key)
    }
    return data
  }

  // Providers
  async function loadProviders(page = 1, pageSize = 20, { name = '' } = {}) {
    let url = `/admin/providers?page=${page}&page_size=${pageSize}`
    if (name) url += `&name=${encodeURIComponent(name)}`
    const data = await api(url)
    return {
      items: data.items.map(p => ({ ...p, _fetching: false })),
      page: data.page,
      total: data.total,
      total_pages: data.total_pages
    }
  }

  async function saveProvider(provider) {
    if (provider.id) {
      return api(`/admin/providers/${provider.id}`, {
        method: 'PUT',
        body: provider
      })
    } else {
      return api('/admin/providers', { method: 'POST', body: provider })
    }
  }

  async function deleteProvider(id) {
    return api(`/admin/providers/${id}`, { method: 'DELETE' })
  }

  async function getProviderQuota(id) {
    return api(`/admin/providers/${id}/quota`)
  }

  async function resetProviderHealth(id) {
    return api(`/admin/providers/${id}/reset-health`, { method: 'POST' })
  }

  async function fetchProviderModels(id) {
    return api(`/admin/providers/${id}/fetch-models`, { method: 'POST' })
  }

  async function fetchModelsFromApi(baseUrl, apiKey) {
    const url = baseUrl.replace(/\/+$/, '') + '/models'
    const res = await fetch(url, {
      headers: { 'Authorization': `Bearer ${apiKey}` }
    })
    if (!res.ok) throw new Error('上游拉取失败')
    const data = await res.json()
    return data.data.map(m => m.id)
  }

  // Groups
  async function loadGroups(page = 1, pageSize = 20, { name = '' } = {}) {
    let url = `/admin/groups?page=${page}&page_size=${pageSize}`
    if (name) url += `&name=${encodeURIComponent(name)}`
    const data = await api(url)
    return {
      items: data.items,
      page: data.page,
      total: data.total,
      total_pages: data.total_pages
    }
  }

  async function loadAllModels() {
    return api('/admin/models')
  }

  async function saveGroup(group) {
    if (group.id) {
      return api(`/admin/groups/${group.id}`, { method: 'PUT', body: group })
    } else {
      return api('/admin/groups', { method: 'POST', body: group })
    }
  }

  async function deleteGroup(id) {
    return api(`/admin/groups/${id}`, { method: 'DELETE' })
  }

  // Logs
  async function loadLogs(page = 1, pageSize = 20, { providerName = '', model = '', onlyErrors = false } = {}) {
    let url = `/admin/logs?page=${page}&page_size=${pageSize}`
    if (providerName) url += `&provider_name=${encodeURIComponent(providerName)}`
    if (model) url += `&model=${encodeURIComponent(model)}`
    if (onlyErrors) url += `&only_errors=1`
    const data = await api(url)
    return {
      items: data.items,
      page: data.page,
      total: data.total,
      total_pages: data.total_pages
    }
  }

  async function loadProviderStats() {
    return api('/admin/providers/stats')
  }

  return {
    api,
    loadProviders,
    loadProviderStats,
    saveProvider,
    deleteProvider,
    getProviderQuota,
    resetProviderHealth,
    fetchProviderModels,
    fetchModelsFromApi,
    loadGroups,
    loadAllModels,
    saveGroup,
    deleteGroup,
    loadLogs,
    apiVerifyKey
  }
}
