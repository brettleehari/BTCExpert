"""
CIAL Pydantic Models
Data models for intelligence messages, agents, and API requests/responses
"""

from pydantic import BaseModel, Field, validator
from typing import Optional, Dict, Any, List, Literal
from datetime import datetime
from enum import Enum


# Enums

class IntelligenceImportance(str, Enum):
    """Intelligence importance classification"""
    CRITICAL = "critical"
    NORMAL = "normal"
    LOW = "low"


class IntelligenceType(str, Enum):
    """Types of intelligence data"""
    PRICE = "price"
    SENTIMENT = "sentiment"
    WHALE = "whale"
    TECHNICAL = "technical"
    REGULATORY = "regulatory"
    DEFI = "defi"
    ONCHAIN = "onchain"


class AgentType(str, Enum):
    """Types of agents that can consume CIAL intelligence"""
    TRADING = "trading"
    RISK = "risk"
    SENTIMENT = "sentiment"
    PORTFOLIO = "portfolio"
    MARKET = "market"
    CONTENT = "content"


class AgentStatus(str, Enum):
    """Agent operational status"""
    INITIALIZING = "initializing"
    ACTIVE = "active"
    INACTIVE = "inactive"
    PAUSED = "paused"
    STOPPED = "stopped"
    ERROR = "error"


# Intelligence Models

class IntelligenceMessage(BaseModel):
    """
    Core intelligence message that flows through CIAL.
    """
    id: str = Field(..., description="Unique intelligence message ID")
    type: IntelligenceType = Field(..., description="Type of intelligence")
    importance: IntelligenceImportance = Field(..., description="Importance classification")
    source: str = Field(..., description="Data source (e.g., coingecko, newsapi)")
    symbol: Optional[str] = Field(None, description="Cryptocurrency symbol (BTC, ETH, etc.)")
    data: Dict[str, Any] = Field(..., description="Intelligence data payload")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Message timestamp")
    expires_at: Optional[datetime] = Field(None, description="Expiration timestamp")
    validated: bool = Field(default=False, description="Whether data has been cross-validated")

    class Config:
        json_schema_extra = {
            "example": {
                "id": "price_btc_20250116_123456",
                "type": "price",
                "importance": "critical",
                "source": "coingecko",
                "symbol": "BTC",
                "data": {
                    "current_price": 62500.0,
                    "price_change_24h": 5.2,
                    "volume_24h": 28500000000
                },
                "metadata": {
                    "market_cap": 1200000000000,
                    "rank": 1
                },
                "validated": True
            }
        }


class PriceIntelligence(BaseModel):
    """Price intelligence data structure"""
    symbol: str
    current_price: float
    price_change_24h: float
    price_change_percentage_24h: float
    volume_24h: float
    market_cap: float
    high_24h: Optional[float] = None
    low_24h: Optional[float] = None


class SentimentIntelligence(BaseModel):
    """Sentiment intelligence data structure"""
    symbol: str
    sentiment_score: float = Field(..., ge=-1, le=1, description="Sentiment score from -1 to 1")
    confidence: float = Field(..., ge=0, le=1, description="Confidence in sentiment analysis")
    source_count: int = Field(..., description="Number of sources analyzed")
    trending_keywords: List[str] = Field(default_factory=list)
    bullish_count: int = 0
    bearish_count: int = 0
    neutral_count: int = 0


# Agent Models

class AgentCapabilities(BaseModel):
    """Agent capabilities and configuration"""
    intelligence_types: List[IntelligenceType] = Field(..., description="Types of intelligence the agent consumes")
    symbols: List[str] = Field(default_factory=list, description="Symbols the agent monitors (empty = all)")
    min_importance: IntelligenceImportance = Field(default=IntelligenceImportance.NORMAL)
    real_time: bool = Field(default=True, description="Whether agent needs real-time streams")
    batch_processing: bool = Field(default=False, description="Whether agent processes in batches")


class AgentRegistration(BaseModel):
    """Agent registration request"""
    agent_id: str = Field(..., description="Unique agent identifier")
    agent_type: AgentType = Field(..., description="Type of agent")
    capabilities: AgentCapabilities = Field(..., description="Agent capabilities")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional agent metadata")

    @validator('agent_id')
    def validate_agent_id(cls, v):
        if not v or len(v) < 3:
            raise ValueError("agent_id must be at least 3 characters")
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "agent_id": "trading_agent_001",
                "agent_type": "trading",
                "capabilities": {
                    "intelligence_types": ["price", "sentiment", "whale"],
                    "symbols": ["BTC", "ETH"],
                    "min_importance": "normal",
                    "real_time": True,
                    "batch_processing": False
                },
                "metadata": {
                    "version": "1.0.0",
                    "owner": "trader_bot_service"
                }
            }
        }


class Agent(BaseModel):
    """Registered agent information"""
    agent_id: str
    agent_type: AgentType
    capabilities: AgentCapabilities
    status: AgentStatus = Field(default=AgentStatus.ACTIVE)
    registered_at: datetime = Field(default_factory=datetime.utcnow)
    last_active: datetime = Field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    message_count: int = Field(default=0, description="Total messages delivered to agent")


class AgentStatusUpdate(BaseModel):
    """Agent status update request"""
    status: AgentStatus
    metadata: Optional[Dict[str, Any]] = None


# API Response Models

class AgentRegistrationResponse(BaseModel):
    """Response for agent registration"""
    success: bool
    agent_id: str
    message: str
    websocket_url: Optional[str] = None
    kafka_topics: List[str] = Field(default_factory=list)


class AgentListResponse(BaseModel):
    """Response for listing agents"""
    total: int
    agents: List[Agent]


class IntelligenceStreamResponse(BaseModel):
    """Response for intelligence stream query"""
    stream_type: str
    messages: List[IntelligenceMessage]
    total: int
    has_more: bool


# Data Connector Models

class DataConnector(BaseModel):
    """Data connector registration"""
    connector_id: str
    name: str
    intelligence_types: List[IntelligenceType]
    reliability_score: float = Field(default=1.0, ge=0.0, le=1.0)
    rate_limit: Optional[str] = None
    enabled: bool = True
    metadata: Dict[str, Any] = Field(default_factory=dict)


class DataConnectorHealth(BaseModel):
    """Data connector health status"""
    connector_id: str
    healthy: bool
    last_success: Optional[datetime] = None
    last_error: Optional[str] = None
    success_rate: float = Field(default=1.0, ge=0.0, le=1.0)
    request_count: int = 0
    error_count: int = 0
