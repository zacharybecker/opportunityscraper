export interface User {
  id: string
  username: string
  email: string
  display_name: string
  role: 'admin' | 'analyst' | 'viewer'
  is_superadmin: boolean
  ldap_groups: { dn: string; name: string }[]
  is_active: boolean
  last_login: string | null
  created_at: string
}

export interface CompanyProfile {
  id: string
  name: string
  uei_sam: string | null
  cage_code: string | null
  description: string | null
  capabilities: { name: string; description: string }[]
  small_business_types: string[]
  naics_codes: string[]
  certifications: {
    type: string
    number: string
    issued: string
    expiry: string
    details: string
  }[]
  past_performance: {
    name: string
    agency: string
    contract_num: string
    value: number
    start: string
    end: string
    description: string
    tags: string[]
  }[]
  future_goals: {
    id: string
    title: string
    description: string
    target_naics: string[]
    target_keywords: string[]
    priority: number
    active: boolean
  }[]
  relevancy_settings: RelevancySettings
  employee_count: number | null
  annual_revenue: number | null
  created_at: string
  updated_at: string
}

export interface RelevancySettings {
  min_relevancy_threshold: number
  keyword_weights: Record<string, number>
  naics_weight: number
  psc_weight: number
  set_aside_weight: number
  past_performance_weight: number
  future_goals_weight: number
  state_preferences: string[]
  excluded_agencies: string[]
  auto_pipeline: boolean
}

export interface ScraperConfig {
  id: string
  name: string
  scraper_type: 'sam_gov' | 'generic_web'
  is_enabled: boolean
  config: Record<string, any>
  schedule_cron: string | null
  last_run_at: string | null
  created_at: string
  updated_at: string
}

export interface ScrapeRun {
  id: string
  scraper_config_id: string
  status: 'pending' | 'running' | 'completed' | 'failed'
  trigger_type: 'scheduled' | 'manual'
  started_at: string | null
  completed_at: string | null
  stats: { found?: number; new?: number; updated?: number; errors?: number }
  error_message: string | null
  created_at: string
}

export interface Opportunity {
  id: string
  external_id: string
  source: string
  source_url: string | null
  title: string
  solicitation_number: string | null
  description: string | null
  notice_type: string | null
  posted_date: string | null
  response_deadline: string | null
  set_aside_type: string | null
  set_aside_description: string | null
  classification_code: string | null
  naics_code: string | null
  agency: string | null
  office: string | null
  place_of_performance_state: string | null
  place_of_performance_city: string | null
  contact_name: string | null
  contact_email: string | null
  contact_phone: string | null
  award_amount: number | null
  award_date: string | null
  awardee_name: string | null
  is_active: boolean
  documents: {
    filename: string
    url: string
    parsed_text: string | null
    parse_status: string
  }[]
  created_at: string
  updated_at: string
  analysis?: OpportunityAnalysis
  pipeline_entry?: PipelineEntry
}

export interface OpportunityAnalysis {
  id: string
  opportunity_id: string
  company_id: string
  relevancy_score: number
  relevancy_label: 'high' | 'medium' | 'low' | 'none'
  relevancy_explanation: string
  capability_matches: { capability: string; match_strength: string; explanation: string }[]
  requirements_met: { requirement: string; how_met: string; confidence: number }[]
  gaps: { description: string; severity: string; recommendation: string }[]
  implementation_needs: { need: string; effort_estimate: string; description: string }[]
  future_goal_matches: { goal_title: string; match_description: string; growth_opportunity: string }[]
  ai_model: string
  status: 'pending' | 'running' | 'completed' | 'failed'
  error_message: string | null
  tokens_used: number | null
  analyzed_at: string | null
  created_at: string
}

export interface PipelineEntry {
  id: string
  opportunity_id: string
  stage: 'found' | 'reviewing' | 'pursuing' | 'applied' | 'won' | 'lost' | 'archived'
  assigned_to: string | null
  notes: string | null
  priority: number
  history: { from: string; to: string; by: string; notes: string; at: string }[]
  created_at: string
  updated_at: string
  opportunity?: Opportunity
}

export interface NotificationRule {
  id: string
  user_id: string
  name: string
  is_enabled: boolean
  trigger_type: string
  conditions: Record<string, any>
  channels: string[]
  webhook_url: string | null
  email_override: string | null
  created_at: string
}

export interface NotificationLogEntry {
  id: string
  rule_id: string | null
  user_id: string
  channel: string
  subject: string
  body: string
  status: string
  opportunity_id: string | null
  created_at: string
}

export interface ChatSession {
  id: string
  user_id: string
  title: string | null
  messages: ChatMessage[]
  created_at: string
  updated_at: string
}

export interface ChatMessage {
  role: 'user' | 'assistant'
  content: string
  metadata?: Record<string, any>
  created_at: string
}

export interface NAICSCode {
  code: string
  title: string
  description: string | null
}

export interface PSCCode {
  code: string
  description: string
}

export interface PaginatedResponse<T> {
  items: T[]
  total: number
  page: number
  page_size: number
  pages: number
}

export interface DashboardData {
  active_opportunities: number
  high_relevancy_count: number
  approaching_deadlines: number
  pipeline_counts: Record<string, number>
  recent_high_relevancy: Opportunity[]
  upcoming_deadlines: Opportunity[]
  recent_scrape_runs: ScrapeRun[]
}

export interface LdapGroupRole {
  id: string
  group_dn: string
  group_name: string
  role: string
  created_at: string
}
