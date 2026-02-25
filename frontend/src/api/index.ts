import apiClient from './client'
import type {
  CompanyProfile,
  RelevancySettings,
  ScraperConfig,
  ScrapeRun,
  Opportunity,
  PipelineEntry,
  ChatSession,
  NotificationRule,
  NotificationLogEntry,
  DashboardData,
  LdapGroupRole,
  User,
  PaginatedResponse,
  NAICSCode,
  PSCCode,
} from '../types'

// Auth
export const login = (username: string, password: string) =>
  apiClient.post('/auth/login', { username, password }).then((r) => r.data)

export const refreshToken = (refresh_token: string) =>
  apiClient.post('/auth/refresh', { refresh_token }).then((r) => r.data)

export const getMe = () => apiClient.get<User>('/auth/me').then((r) => r.data)

// Company
export const getCompany = () =>
  apiClient.get<CompanyProfile>('/company').then((r) => r.data)

export const updateCompany = (data: Partial<CompanyProfile>) =>
  apiClient.put<CompanyProfile>('/company', data).then((r) => r.data)

export const getGoals = () =>
  apiClient.get<CompanyProfile['future_goals']>('/company/goals').then((r) => r.data)

export const updateGoals = (goals: CompanyProfile['future_goals']) =>
  apiClient.put('/company/goals', goals).then((r) => r.data)

export const getRelevancySettings = () =>
  apiClient.get<RelevancySettings>('/company/relevancy-settings').then((r) => r.data)

export const updateRelevancySettings = (data: RelevancySettings) =>
  apiClient.put('/company/relevancy-settings', data).then((r) => r.data)

// Scrapers
export const getScrapers = () =>
  apiClient.get<ScraperConfig[]>('/scrapers').then((r) => r.data)

export const createScraper = (data: Partial<ScraperConfig>) =>
  apiClient.post<ScraperConfig>('/scrapers', data).then((r) => r.data)

export const updateScraper = (id: string, data: Partial<ScraperConfig>) =>
  apiClient.put<ScraperConfig>(`/scrapers/${id}`, data).then((r) => r.data)

export const deleteScraper = (id: string) =>
  apiClient.delete(`/scrapers/${id}`).then((r) => r.data)

export const runScraper = (id: string) =>
  apiClient.post<ScrapeRun>(`/scrapers/${id}/run`).then((r) => r.data)

export const getScraperRuns = (id: string) =>
  apiClient.get<ScrapeRun[]>(`/scrapers/${id}/runs`).then((r) => r.data)

export const runAllScrapers = () =>
  apiClient.post('/scrapers/run-all').then((r) => r.data)

// Opportunities
export const getOpportunities = (params: Record<string, any>) =>
  apiClient.get<PaginatedResponse<Opportunity>>('/opportunities', { params }).then((r) => r.data)

export const getOpportunity = (id: string) =>
  apiClient.get<Opportunity>(`/opportunities/${id}`).then((r) => r.data)

export const analyzeOpportunity = (id: string) =>
  apiClient.post(`/opportunities/${id}/analyze`).then((r) => r.data)

export const parseDocuments = (id: string) =>
  apiClient.post(`/opportunities/${id}/parse-documents`).then((r) => r.data)

// Pipeline
export const getPipeline = () =>
  apiClient.get<Record<string, PipelineEntry[]>>('/pipeline').then((r) => r.data)

export const addToPipeline = (data: { opportunity_id: string; stage?: string; notes?: string }) =>
  apiClient.post<PipelineEntry>('/pipeline', data).then((r) => r.data)

export const updatePipelineEntry = (id: string, data: Partial<PipelineEntry>) =>
  apiClient.put<PipelineEntry>(`/pipeline/${id}`, data).then((r) => r.data)

export const deletePipelineEntry = (id: string) =>
  apiClient.delete(`/pipeline/${id}`).then((r) => r.data)

export const getPipelineStats = () =>
  apiClient.get('/pipeline/stats').then((r) => r.data)

// Chat
export const getChatSessions = () =>
  apiClient.get<ChatSession[]>('/chat/sessions').then((r) => r.data)

export const createChatSession = () =>
  apiClient.post<ChatSession>('/chat/sessions').then((r) => r.data)

export const deleteChatSession = (id: string) =>
  apiClient.delete(`/chat/sessions/${id}`).then((r) => r.data)

// Chat message is SSE - handled separately in components

// Notifications
export const getNotificationRules = () =>
  apiClient.get<NotificationRule[]>('/notifications/rules').then((r) => r.data)

export const createNotificationRule = (data: Partial<NotificationRule>) =>
  apiClient.post<NotificationRule>('/notifications/rules', data).then((r) => r.data)

export const updateNotificationRule = (id: string, data: Partial<NotificationRule>) =>
  apiClient.put<NotificationRule>(`/notifications/rules/${id}`, data).then((r) => r.data)

export const deleteNotificationRule = (id: string) =>
  apiClient.delete(`/notifications/rules/${id}`).then((r) => r.data)

export const getNotificationLog = () =>
  apiClient.get<NotificationLogEntry[]>('/notifications/log').then((r) => r.data)

// Analytics
export const getDashboard = () =>
  apiClient.get<DashboardData>('/analytics/dashboard').then((r) => r.data)

export const getCharts = (params?: Record<string, any>) =>
  apiClient.get('/analytics/charts', { params }).then((r) => r.data)

// Admin
export const getLdapGroups = () =>
  apiClient.get<LdapGroupRole[]>('/admin/ldap-groups').then((r) => r.data)

export const createLdapGroup = (data: Partial<LdapGroupRole>) =>
  apiClient.post<LdapGroupRole>('/admin/ldap-groups', data).then((r) => r.data)

export const updateLdapGroup = (id: string, data: Partial<LdapGroupRole>) =>
  apiClient.put<LdapGroupRole>(`/admin/ldap-groups/${id}`, data).then((r) => r.data)

export const deleteLdapGroup = (id: string) =>
  apiClient.delete(`/admin/ldap-groups/${id}`).then((r) => r.data)

export const getUsers = () =>
  apiClient.get<User[]>('/admin/users').then((r) => r.data)

export const updateUser = (id: string, data: Partial<User>) =>
  apiClient.put<User>(`/admin/users/${id}`, data).then((r) => r.data)

export const getAiConfig = () =>
  apiClient.get('/admin/ai-config').then((r) => r.data)

export const updateAiConfig = (data: Record<string, any>) =>
  apiClient.put('/admin/ai-config', data).then((r) => r.data)

export const getHealth = () =>
  apiClient.get('/admin/health').then((r) => r.data)

// Codes
export const searchNaics = (search: string) =>
  apiClient.get<NAICSCode[]>('/codes/naics', { params: { search } }).then((r) => r.data)

export const searchPsc = (search: string) =>
  apiClient.get<PSCCode[]>('/codes/psc', { params: { search } }).then((r) => r.data)

export const importCodes = (file: File) => {
  const formData = new FormData()
  formData.append('file', file)
  return apiClient.post('/codes/import', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  }).then((r) => r.data)
}
