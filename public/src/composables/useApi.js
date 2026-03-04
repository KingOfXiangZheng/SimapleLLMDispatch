// src/composables/useApi.js
import { ref } from 'vue'

export function useApi() {
  async function api(url, opts = {}) {
    const res = await fetch(url, {
      headers: { 'Content-Type': 'application/json' },
      ...opts,
      body: opts.body ? JSON.stringify(opts.body) : undefined
    })
    const data = await res.json()
    if (!res.ok) throw new Error(data.error || 'Request failed')
    return data
  }

  // Providers
  async function loadProviders(page = 1, pageSize = 20) {
    const data = await api(`/admin/providers?page=${page}&page_size=${pageSize}`)
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
  async function loadGroups() {
    return api('/admin/groups')
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
  async function loadLogs(page = 1, pageSize = 50) {
    const data = await api(`/admin/logs?page=${page}&page_size=${pageSize}`)
    return {
      items: data.items,
      page: data.page,
      total: data.total,
      total_pages: data.total_pages
    }
  }

  return {
    api,
    loadProviders,
    saveProvider,
    deleteProvider,
    getProviderQuota,
    fetchProviderModels,
    fetchModelsFromApi,
    loadGroups,
    loadAllModels,
    saveGroup,
    deleteGroup,
    loadLogs
  }
}
