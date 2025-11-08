"""
Metrics configuration schema for CrashLens.

This module defines the configuration models for metrics collection,
including global sampling rates and per-rule overrides.

Example YAML configuration:
```yaml
metrics:
  enabled: true
  sampling:
    rate: 0.1  # Global 10% sampling
    per_rule:
      expensive_rule: 0.01  # 1% for expensive rules
      rare_event: 1.0       # 100% for rare events
  pushgateway:
    url: http://localhost:9091
    job: crashlens-guard
```
"""

from typing import Dict, Optional
from pydantic import BaseModel, Field, field_validator


class SamplingConfig(BaseModel):
    """Configuration for metrics sampling.
    
    Attributes:
        rate: Global sampling rate (0.0-1.0). Default: 1.0 (100% sampling)
        per_rule: Per-rule sampling rate overrides. Rule name -> sampling rate.
                  Overrides the global rate for specific rules.
    
    Example:
        ```python
        config = SamplingConfig(
            rate=0.1,  # 10% global sampling
            per_rule={
                "high_frequency_rule": 0.01,  # 1% for noisy rules
                "critical_violation": 1.0,    # 100% for important rules
            }
        )
        ```
    """
    
    rate: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description="Global sampling rate (0.0-1.0)"
    )
    per_rule: Dict[str, float] = Field(
        default_factory=dict,
        description="Per-rule sampling rate overrides"
    )
    
    @field_validator('per_rule')
    @classmethod
    def validate_per_rule_rates(cls, v: Dict[str, float]) -> Dict[str, float]:
        """Validate per-rule sampling rates.
        
        Args:
            v: Dictionary of rule name -> sampling rate
        
        Returns:
            Validated dictionary
        
        Raises:
            ValueError: If any rate is outside 0.0-1.0 or rule name is empty
        """
        for rule_name, rate in v.items():
            # Validate rule name
            if not rule_name or not rule_name.strip():
                raise ValueError(
                    f"Rule name cannot be empty (found: '{rule_name}')"
                )
            
            # Validate rate range
            if not (0.0 <= rate <= 1.0):
                raise ValueError(
                    f"Sampling rate for rule '{rule_name}' must be between 0.0 and 1.0, "
                    f"got {rate}"
                )
        
        return v
    
    def get_rate(self, rule_name: str) -> float:
        """Get sampling rate for a specific rule.
        
        Returns per-rule rate if configured, otherwise returns global rate.
        
        Args:
            rule_name: Name of the rule to get rate for
        
        Returns:
            Sampling rate for the rule (0.0-1.0)
        
        Example:
            ```python
            config = SamplingConfig(rate=0.1, per_rule={"rare": 1.0})
            assert config.get_rate("common") == 0.1  # Uses global rate
            assert config.get_rate("rare") == 1.0    # Uses per-rule rate
            ```
        """
        return self.per_rule.get(rule_name, self.rate)


class PushgatewayConfig(BaseModel):
    """Configuration for Prometheus Pushgateway.
    
    Attributes:
        url: Pushgateway URL (e.g., http://localhost:9091)
        job: Job name for metrics grouping
        timeout: Push timeout in seconds
    """
    
    url: str = Field(
        default="http://localhost:9091",
        description="Pushgateway URL"
    )
    job: str = Field(
        default="crashlens-guard",
        description="Job name for metrics grouping"
    )
    timeout: int = Field(
        default=5,
        ge=1,
        le=60,
        description="Push timeout in seconds"
    )


class HttpServerConfig(BaseModel):
    """Configuration for HTTP metrics server.
    
    Attributes:
        enabled: Whether HTTP server mode is enabled
        port: Server port (1024-65535)
        addr: Bind address (default: 127.0.0.1 for security)
    """
    
    enabled: bool = Field(
        default=False,
        description="Enable HTTP server mode"
    )
    port: int = Field(
        default=9090,
        ge=1024,
        le=65535,
        description="Server port (unprivileged ports only)"
    )
    addr: str = Field(
        default="127.0.0.1",
        description="Bind address (default: localhost-only)"
    )


class MetricsConfig(BaseModel):
    """Complete metrics configuration.
    
    Attributes:
        enabled: Whether metrics collection is enabled
        sampling: Sampling configuration
        pushgateway: Pushgateway configuration (for push mode)
        http_server: HTTP server configuration (for scraping mode)
    
    Example:
        ```python
        config = MetricsConfig(
            enabled=True,
            sampling=SamplingConfig(
                rate=0.1,
                per_rule={"expensive": 0.01}
            ),
            pushgateway=PushgatewayConfig(
                url="http://prometheus:9091"
            )
        )
        ```
    """
    
    enabled: bool = Field(
        default=False,
        description="Enable metrics collection"
    )
    sampling: SamplingConfig = Field(
        default_factory=SamplingConfig,
        description="Sampling configuration"
    )
    pushgateway: Optional[PushgatewayConfig] = Field(
        default=None,
        description="Pushgateway configuration (push mode)"
    )
    http_server: Optional[HttpServerConfig] = Field(
        default=None,
        description="HTTP server configuration (scraping mode)"
    )
    
    @field_validator('pushgateway', 'http_server')
    @classmethod
    def set_defaults(cls, v: Optional[BaseModel], info) -> Optional[BaseModel]:
        """Set default configurations if not provided."""
        if v is None and info.field_name == 'pushgateway':
            return PushgatewayConfig()
        elif v is None and info.field_name == 'http_server':
            return HttpServerConfig()
        return v


# Example configurations for documentation

EXAMPLE_CONFIG_MINIMAL = """
metrics:
  enabled: true
  sampling:
    rate: 0.1  # 10% sampling
"""

EXAMPLE_CONFIG_PER_RULE = """
metrics:
  enabled: true
  sampling:
    rate: 0.1  # 10% default sampling
    per_rule:
      # High-frequency rules: lower sampling
      rate_limit_violation: 0.01  # 1%
      prompt_too_long: 0.01       # 1%
      
      # Critical violations: full sampling
      security_breach: 1.0        # 100%
      cost_overrun: 1.0           # 100%
      
      # Medium priority: moderate sampling
      model_overkill: 0.2         # 20%
"""

EXAMPLE_CONFIG_FULL = """
metrics:
  enabled: true
  
  sampling:
    rate: 0.1  # 10% default
    per_rule:
      expensive_rule: 0.01
      rare_event: 1.0
  
  pushgateway:
    url: http://prometheus:9091
    job: crashlens-production
    timeout: 10
  
  http_server:
    enabled: false
    port: 9090
    addr: 127.0.0.1
"""
