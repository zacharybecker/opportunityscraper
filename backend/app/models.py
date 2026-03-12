import uuid

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID, TSVECTOR
from sqlalchemy.orm import DeclarativeBase, relationship
from sqlalchemy.types import DateTime


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username = Column(String(255), unique=True, nullable=False)
    email = Column(String(255))
    display_name = Column(String(255))
    role = Column(String(50), nullable=False, default="viewer")
    ldap_groups = Column(JSONB, default=[])
    is_active = Column(Boolean, default=True)
    is_superadmin = Column(Boolean, default=False)
    auth_provider = Column(String(20), default="ldap")
    password_hash = Column(String(255), nullable=True)
    email_verified = Column(Boolean, default=False)
    password_reset_token = Column(String(255), nullable=True)
    password_reset_expires = Column(DateTime(timezone=True), nullable=True)
    last_login = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    notification_rules = relationship("NotificationRule", back_populates="user", cascade="all, delete-orphan")
    chat_sessions = relationship("ChatSession", back_populates="user", cascade="all, delete-orphan")



class LdapGroupRole(Base):
    __tablename__ = "ldap_group_roles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    group_dn = Column(String(512), unique=True, nullable=False)
    group_name = Column(String(255), nullable=False)
    role = Column(String(50), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class CompanyProfile(Base):
    __tablename__ = "company_profiles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    uei_sam = Column(String(12))
    cage_code = Column(String(10))
    description = Column(Text)
    capabilities = Column(JSONB, default=[])
    small_business_types = Column(ARRAY(String), default=[])
    naics_codes = Column(ARRAY(String), default=[])
    certifications = Column(JSONB, default=[])
    past_performance = Column(JSONB, default=[])
    future_goals = Column(JSONB, default=[])
    relevancy_settings = Column(JSONB, default={})
    employee_count = Column(Integer)
    annual_revenue = Column(Numeric(15, 2))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class ScraperConfig(Base):
    __tablename__ = "scraper_configs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    scraper_type = Column(String(50), nullable=False)
    is_enabled = Column(Boolean, default=True)
    config = Column(JSONB, nullable=False)
    schedule_cron = Column(String(100))
    last_run_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    runs = relationship("ScrapeRun", back_populates="scraper_config", cascade="all, delete-orphan")


class ScrapeRun(Base):
    __tablename__ = "scrape_runs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    scraper_config_id = Column(UUID(as_uuid=True), ForeignKey("scraper_configs.id", ondelete="CASCADE"))
    status = Column(String(20), nullable=False, default="pending")
    trigger_type = Column(String(20), nullable=False)
    started_at = Column(DateTime(timezone=True))
    completed_at = Column(DateTime(timezone=True))
    stats = Column(JSONB, default={})
    error_message = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    scraper_config = relationship("ScraperConfig", back_populates="runs")


class Opportunity(Base):
    __tablename__ = "opportunities"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    external_id = Column(String(255), nullable=False)
    source = Column(String(50), nullable=False)
    source_url = Column(String(2048))
    scrape_run_id = Column(UUID(as_uuid=True), ForeignKey("scrape_runs.id"))
    title = Column(String(1000), nullable=False)
    solicitation_number = Column(String(255))
    description = Column(Text)
    notice_type = Column(String(50))
    posted_date = Column(DateTime(timezone=True))
    response_deadline = Column(DateTime(timezone=True))
    set_aside_type = Column(String(50))
    set_aside_description = Column(String(255))
    classification_code = Column(String(10))
    naics_code = Column(String(6))
    agency = Column(String(500))
    office = Column(String(500))
    place_of_performance_state = Column(String(2))
    place_of_performance_city = Column(String(255))
    contact_name = Column(String(255))
    contact_email = Column(String(255))
    contact_phone = Column(String(50))
    award_amount = Column(Numeric(15, 2))
    award_date = Column(Date)
    awardee_name = Column(String(500))
    is_active = Column(Boolean, default=True)
    raw_data = Column(JSONB)
    documents = Column(JSONB, default=[])
    content_hash = Column(String(64))
    search_vector = Column(TSVECTOR)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        UniqueConstraint("external_id", "source", name="uq_opp_external_source"),
        Index("idx_opp_deadline", "response_deadline", postgresql_where=text("is_active = true")),
        Index("idx_opp_posted", "posted_date"),
        Index("idx_opp_hash", "content_hash"),
        Index("idx_opp_naics", "naics_code"),
        Index("idx_opp_search", "search_vector", postgresql_using="gin"),
    )

    analysis = relationship("OpportunityAnalysis", back_populates="opportunity", uselist=False, cascade="all, delete-orphan")
    pipeline_entry = relationship("PipelineEntry", back_populates="opportunity", uselist=False, cascade="all, delete-orphan")


class OpportunityAnalysis(Base):
    __tablename__ = "opportunity_analyses"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    opportunity_id = Column(UUID(as_uuid=True), ForeignKey("opportunities.id", ondelete="CASCADE"), unique=True)
    company_id = Column(UUID(as_uuid=True), ForeignKey("company_profiles.id", ondelete="CASCADE"))
    relevancy_score = Column(Numeric(5, 2))
    relevancy_label = Column(String(20))
    relevancy_explanation = Column(Text)
    capability_matches = Column(JSONB, default=[])
    requirements_met = Column(JSONB, default=[])
    gaps = Column(JSONB, default=[])
    implementation_needs = Column(JSONB, default=[])
    future_goal_matches = Column(JSONB, default=[])
    ai_model = Column(String(100))
    prompt_version = Column(String(20))
    status = Column(String(20), default="pending")
    error_message = Column(Text)
    tokens_used = Column(Integer)
    analyzed_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("idx_analysis_score", "relevancy_score"),
    )

    opportunity = relationship("Opportunity", back_populates="analysis")


class PipelineEntry(Base):
    __tablename__ = "pipeline_entries"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    opportunity_id = Column(UUID(as_uuid=True), ForeignKey("opportunities.id", ondelete="CASCADE"))
    stage = Column(String(30), nullable=False, default="found")
    assigned_to = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    notes = Column(Text)
    priority = Column(Integer, default=5)
    position = Column(Integer, default=0)
    history = Column(JSONB, default=[])
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index("idx_pipeline_stage", "stage"),
    )

    opportunity = relationship("Opportunity", back_populates="pipeline_entry")
    pipeline_comments = relationship("PipelineComment", back_populates="pipeline_entry", cascade="all, delete-orphan")


class PipelineComment(Base):
    __tablename__ = "pipeline_comments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    pipeline_entry_id = Column(UUID(as_uuid=True), ForeignKey("pipeline_entries.id", ondelete="CASCADE"))
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    content = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    pipeline_entry = relationship("PipelineEntry", back_populates="pipeline_comments")


class NotificationRule(Base):
    __tablename__ = "notification_rules"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"))
    name = Column(String(255), nullable=False)
    is_enabled = Column(Boolean, default=True)
    trigger_type = Column(String(50), nullable=False)
    conditions = Column(JSONB, default={})
    channels = Column(ARRAY(String), default=[])
    webhook_url = Column(String(2048))
    email_override = Column(String(255))
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="notification_rules")


class NotificationLog(Base):
    __tablename__ = "notification_log"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    rule_id = Column(UUID(as_uuid=True), ForeignKey("notification_rules.id", ondelete="SET NULL"))
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    channel = Column(String(20), nullable=False)
    subject = Column(String(500))
    body = Column(Text)
    status = Column(String(20), default="sent")
    opportunity_id = Column(UUID(as_uuid=True), ForeignKey("opportunities.id", ondelete="SET NULL"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class KnowledgeDocument(Base):
    __tablename__ = "knowledge_documents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id = Column(UUID(as_uuid=True), ForeignKey("company_profiles.id", ondelete="CASCADE"), nullable=True)
    title = Column(String(500), nullable=False)
    doc_type = Column(String(20), nullable=False, default="text")
    file_path = Column(String(2048), nullable=True)
    original_filename = Column(String(500))
    url = Column(String(2048), nullable=True)
    extracted_text = Column(Text, nullable=True)
    metadata_ = Column("metadata", JSONB, default={})
    category = Column(String(50), default="general")
    search_vector = Column(TSVECTOR, nullable=True)
    uploaded_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index("idx_kb_search", "search_vector", postgresql_using="gin"),
    )


class InAppNotification(Base):
    __tablename__ = "in_app_notifications"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"))
    title = Column(String(500), nullable=False)
    body = Column(Text)
    category = Column(String(50), default="system")
    link = Column(String(2048), nullable=True)
    is_read = Column(Boolean, default=False)
    opportunity_id = Column(UUID(as_uuid=True), ForeignKey("opportunities.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("idx_notif_user_read", "user_id", "is_read", "created_at"),
    )


class ChatSession(Base):
    __tablename__ = "chat_sessions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"))
    title = Column(String(255))
    messages = Column(JSONB, default=[])
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    user = relationship("User", back_populates="chat_sessions")


class Proposal(Base):
    __tablename__ = "proposals"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    opportunity_id = Column(UUID(as_uuid=True), ForeignKey("opportunities.id", ondelete="SET NULL"), nullable=True)
    title = Column(String(500), nullable=False)
    status = Column(String(30), default="draft")
    template_id = Column(UUID(as_uuid=True), ForeignKey("proposal_templates.id", ondelete="SET NULL"), nullable=True)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    versions = relationship("ProposalVersion", back_populates="proposal", cascade="all, delete-orphan")
    comments = relationship("ProposalComment", back_populates="proposal", cascade="all, delete-orphan")
    opportunity = relationship("Opportunity")


class ProposalVersion(Base):
    __tablename__ = "proposal_versions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    proposal_id = Column(UUID(as_uuid=True), ForeignKey("proposals.id", ondelete="CASCADE"))
    version_number = Column(Integer, nullable=False, default=1)
    content = Column(JSONB, default={})
    sections = Column(JSONB, default=[])
    change_summary = Column(Text, nullable=True)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    proposal = relationship("Proposal", back_populates="versions")


class ProposalTemplate(Base):
    __tablename__ = "proposal_templates"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    sections = Column(JSONB, default=[])
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class ProposalComment(Base):
    __tablename__ = "proposal_comments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    proposal_id = Column(UUID(as_uuid=True), ForeignKey("proposals.id", ondelete="CASCADE"))
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    content = Column(Text, nullable=False)
    section_key = Column(String(255), nullable=True)
    resolved = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    proposal = relationship("Proposal", back_populates="comments")


class NAICSCode(Base):
    __tablename__ = "naics_codes"

    code = Column(String(6), primary_key=True)
    title = Column(String(500), nullable=False)
    description = Column(Text)


class PSCCode(Base):
    __tablename__ = "psc_codes"

    code = Column(String(4), primary_key=True)
    description = Column(String(500), nullable=False)
