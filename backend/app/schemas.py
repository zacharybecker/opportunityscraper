from pydantic import BaseModel, Field
from typing import Optional, Any
from datetime import datetime
from uuid import UUID


# Auth
class LoginRequest(BaseModel):
    username: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: "UserResponse"

class RefreshRequest(BaseModel):
    refresh_token: str

# User
class UserResponse(BaseModel):
    id: UUID
    username: str
    email: Optional[str] = None
    display_name: Optional[str] = None
    role: str
    is_superadmin: bool
    ldap_groups: list[dict] = []
    is_active: bool
    last_login: Optional[datetime] = None
    created_at: datetime

    model_config = {"from_attributes": True}

class UserUpdate(BaseModel):
    is_active: Optional[bool] = None
    role: Optional[str] = None

# Company
class CompanyProfileResponse(BaseModel):
    id: UUID
    name: str
    uei_sam: Optional[str] = None
    cage_code: Optional[str] = None
    description: Optional[str] = None
    capabilities: list[dict] = []
    small_business_types: list[str] = []
    naics_codes: list[str] = []
    certifications: list[dict] = []
    past_performance: list[dict] = []
    future_goals: list[dict] = []
    relevancy_settings: dict = {}
    employee_count: Optional[int] = None
    annual_revenue: Optional[float] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}

class CompanyProfileUpdate(BaseModel):
    name: Optional[str] = None
    uei_sam: Optional[str] = None
    cage_code: Optional[str] = None
    description: Optional[str] = None
    capabilities: Optional[list[dict]] = None
    small_business_types: Optional[list[str]] = None
    naics_codes: Optional[list[str]] = None
    certifications: Optional[list[dict]] = None
    past_performance: Optional[list[dict]] = None
    employee_count: Optional[int] = None
    annual_revenue: Optional[float] = None

class RelevancySettingsResponse(BaseModel):
    min_relevancy_threshold: int = 30
    keyword_weights: dict[str, float] = {}
    naics_weight: float = 1.0
    psc_weight: float = 1.0
    set_aside_weight: float = 1.5
    past_performance_weight: float = 1.2
    future_goals_weight: float = 0.8
    state_preferences: list[str] = []
    excluded_agencies: list[str] = []
    auto_pipeline: bool = True

class RelevancySettingsUpdate(BaseModel):
    min_relevancy_threshold: Optional[int] = None
    keyword_weights: Optional[dict[str, float]] = None
    naics_weight: Optional[float] = None
    psc_weight: Optional[float] = None
    set_aside_weight: Optional[float] = None
    past_performance_weight: Optional[float] = None
    future_goals_weight: Optional[float] = None
    state_preferences: Optional[list[str]] = None
    excluded_agencies: Optional[list[str]] = None
    auto_pipeline: Optional[bool] = None

# Scraper
class ScraperConfigCreate(BaseModel):
    name: str
    scraper_type: str
    is_enabled: bool = True
    config: dict
    schedule_cron: Optional[str] = None

class ScraperConfigUpdate(BaseModel):
    name: Optional[str] = None
    is_enabled: Optional[bool] = None
    config: Optional[dict] = None
    schedule_cron: Optional[str] = None

class ScraperConfigResponse(BaseModel):
    id: UUID
    name: str
    scraper_type: str
    is_enabled: bool
    config: dict
    schedule_cron: Optional[str] = None
    last_run_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}

class ScrapeRunResponse(BaseModel):
    id: UUID
    scraper_config_id: UUID
    status: str
    trigger_type: str
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    stats: dict = {}
    error_message: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}

# Opportunity
class OpportunityResponse(BaseModel):
    id: UUID
    external_id: str
    source: str
    source_url: Optional[str] = None
    title: str
    solicitation_number: Optional[str] = None
    description: Optional[str] = None
    notice_type: Optional[str] = None
    posted_date: Optional[datetime] = None
    response_deadline: Optional[datetime] = None
    set_aside_type: Optional[str] = None
    set_aside_description: Optional[str] = None
    classification_code: Optional[str] = None
    naics_code: Optional[str] = None
    agency: Optional[str] = None
    office: Optional[str] = None
    place_of_performance_state: Optional[str] = None
    place_of_performance_city: Optional[str] = None
    contact_name: Optional[str] = None
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None
    award_amount: Optional[float] = None
    award_date: Optional[str] = None
    awardee_name: Optional[str] = None
    is_active: bool
    documents: list[dict] = []
    created_at: datetime
    updated_at: datetime
    analysis: Optional["OpportunityAnalysisResponse"] = None
    pipeline_entry: Optional["PipelineEntryResponse"] = None

    model_config = {"from_attributes": True}

class OpportunityAnalysisResponse(BaseModel):
    id: UUID
    opportunity_id: UUID
    company_id: Optional[UUID] = None
    relevancy_score: Optional[float] = None
    relevancy_label: Optional[str] = None
    relevancy_explanation: Optional[str] = None
    capability_matches: list[dict] = []
    requirements_met: list[dict] = []
    gaps: list[dict] = []
    implementation_needs: list[dict] = []
    future_goal_matches: list[dict] = []
    ai_model: Optional[str] = None
    status: str
    error_message: Optional[str] = None
    tokens_used: Optional[int] = None
    analyzed_at: Optional[datetime] = None
    created_at: datetime

    model_config = {"from_attributes": True}

# Pipeline
class PipelineEntryCreate(BaseModel):
    opportunity_id: UUID
    stage: str = "found"
    notes: Optional[str] = None
    priority: int = 5

class PipelineEntryUpdate(BaseModel):
    stage: Optional[str] = None
    assigned_to: Optional[UUID] = None
    notes: Optional[str] = None
    priority: Optional[int] = None

class PipelineEntryResponse(BaseModel):
    id: UUID
    opportunity_id: UUID
    stage: str
    assigned_to: Optional[UUID] = None
    notes: Optional[str] = None
    priority: int
    history: list[dict] = []
    created_at: datetime
    updated_at: datetime
    opportunity: Optional[OpportunityResponse] = None

    model_config = {"from_attributes": True}

# Chat
class ChatSessionResponse(BaseModel):
    id: UUID
    user_id: UUID
    title: Optional[str] = None
    messages: list[dict] = []
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}

class ChatMessageRequest(BaseModel):
    content: str

# Notifications
class NotificationRuleCreate(BaseModel):
    name: str
    trigger_type: str
    is_enabled: bool = True
    conditions: dict = {}
    channels: list[str] = []
    webhook_url: Optional[str] = None
    email_override: Optional[str] = None

class NotificationRuleUpdate(BaseModel):
    name: Optional[str] = None
    is_enabled: Optional[bool] = None
    trigger_type: Optional[str] = None
    conditions: Optional[dict] = None
    channels: Optional[list[str]] = None
    webhook_url: Optional[str] = None
    email_override: Optional[str] = None

class NotificationRuleResponse(BaseModel):
    id: UUID
    user_id: UUID
    name: str
    is_enabled: bool
    trigger_type: str
    conditions: dict = {}
    channels: list[str] = []
    webhook_url: Optional[str] = None
    email_override: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}

class NotificationLogResponse(BaseModel):
    id: UUID
    rule_id: Optional[UUID] = None
    user_id: UUID
    channel: str
    subject: Optional[str] = None
    body: Optional[str] = None
    status: str
    opportunity_id: Optional[UUID] = None
    created_at: datetime

    model_config = {"from_attributes": True}

# LDAP Groups
class LdapGroupRoleCreate(BaseModel):
    group_dn: str
    group_name: str
    role: str

class LdapGroupRoleUpdate(BaseModel):
    group_name: Optional[str] = None
    role: Optional[str] = None

class LdapGroupRoleResponse(BaseModel):
    id: UUID
    group_dn: str
    group_name: str
    role: str
    created_at: datetime

    model_config = {"from_attributes": True}

# Codes
class NAICSCodeResponse(BaseModel):
    code: str
    title: str
    description: Optional[str] = None

    model_config = {"from_attributes": True}

class PSCCodeResponse(BaseModel):
    code: str
    description: str

    model_config = {"from_attributes": True}

# Pagination
class PaginatedResponse(BaseModel):
    items: list[Any] = []
    total: int
    page: int
    page_size: int
    pages: int

# Dashboard / Analytics
class DashboardResponse(BaseModel):
    active_opportunities: int
    high_relevancy_count: int
    approaching_deadlines: int
    pipeline_counts: dict[str, int]
    recent_high_relevancy: list[OpportunityResponse]
    upcoming_deadlines: list[OpportunityResponse]
    recent_scrape_runs: list[ScrapeRunResponse]

# AI Config
class AIConfigResponse(BaseModel):
    api_base_url: str
    model: str
    max_tokens: int
    temperature: float

class AIConfigUpdate(BaseModel):
    api_base_url: Optional[str] = None
    api_key: Optional[str] = None
    model: Optional[str] = None
    max_tokens: Optional[int] = None
    temperature: Optional[float] = None

# FutureGoal
class FutureGoalItem(BaseModel):
    id: Optional[str] = None
    title: str
    description: str = ""
    target_naics: list[str] = []
    target_keywords: list[str] = []
    priority: int = 5
    active: bool = True


# Rebuild forward references
TokenResponse.model_rebuild()
OpportunityResponse.model_rebuild()
PipelineEntryResponse.model_rebuild()
