"""
Interactive settings menu for configuring Membria providers, roles, and agents.
"""

from typing import Optional, Dict, List
from dataclasses import dataclass
from .model_fetcher import ModelFetcher
import asyncio


@dataclass
class Provider:
    """Configuration for an LLM provider."""
    name: str
    type: str  # "openai", "anthropic", "local"
    api_key: str = ""
    endpoint: str = ""
    model: str = ""
    enabled: bool = True


@dataclass
class Role:
    """Configuration for an agent role."""
    name: str
    title: str
    description: str
    provider: str  # Which provider to use
    model: str
    capabilities: List[str]
    calibration_score: float = 0.5


class SettingsManager:
    """Manage Membria configuration settings."""
    
    def __init__(self, config_manager):
        """Initialize settings manager."""
        self.config_manager = config_manager
        self.providers: Dict[str, Provider] = {}
        self.roles: Dict[str, Role] = {}
        self.model_fetcher = ModelFetcher()
        self._load_settings()
    
    def _load_settings(self):
        """Load settings from config."""
        config = self.config_manager.config
        
        # Load providers from config.providers (dict)
        providers_dict = getattr(config, 'providers', {}) or {}

        # Normalize / migrate provider entries (add missing providers, update old model names)
        changed = self._migrate_providers_if_needed(providers_dict)
        
        # Try to refresh models from API if we have credentials
        if any(p.get('api_key') for p in providers_dict.values() if isinstance(p, dict)):
            api_updated = self._refresh_models_from_api(providers_dict)
            changed = changed or api_updated
        
        if changed:
            # persist migrated providers back to config
            config.providers = providers_dict
            try:
                self.config_manager.save()
            except Exception:
                # ignore save errors here; settings will still load in-memory
                pass

        if providers_dict:
            for name, provider_data in providers_dict.items():
                # Provider data is a dict from config
                if isinstance(provider_data, dict):
                    self.providers[name] = Provider(
                        name=name,
                        type=provider_data.get("type", "openai"),
                        api_key=provider_data.get("api_key", ""),
                        endpoint=provider_data.get("endpoint", ""),
                        model=provider_data.get("model", "gpt-4"),
                        enabled=provider_data.get("enabled", True),
                    )
        else:
            # If no providers configured, use defaults from config
            print(f"[DEBUG] No providers in config, using defaults")
            if hasattr(config, 'providers'):
                config.providers = {
                    "anthropic": {
                        "type": "anthropic",
                        "model": "claude-3-5-sonnet-latest",
                        "api_key": "",
                        "endpoint": "https://api.anthropic.com/v1",
                        "enabled": True
                    },
                    "openai": {
                        "type": "openai",
                        "model": "gpt-4-turbo",
                        "api_key": "",
                        "endpoint": "https://api.openai.com/v1",
                        "enabled": True
                    },
                    "kilo": {
                        "type": "kilo",
                        "model": "kilo-code",
                        "api_key": "",
                        "endpoint": "http://kilo.ai",
                        "enabled": False
                    },
                    "openrouter": {
                        "type": "openrouter",
                        "model": "kilo-code",
                        "api_key": "",
                        "endpoint": "https://openrouter.ai/api/v1",
                        "enabled": False
                    }
                }
                # Retry loading
                self._load_settings()
                return
        
        # Load roles from config.team.agents (dict)
        if hasattr(config, 'team') and config.team and hasattr(config.team, 'agents'):
            for name, agent_data in config.team['agents'].items():
                self.roles[name] = Role(
                    name=name,
                    title=agent_data.get("label", name.title()),
                    description=f"Role: {agent_data.get('role', name)}",
                    provider=agent_data.get("provider", "anthropic"),
                    model=agent_data.get("model", "gpt-4"),
                    capabilities=[agent_data.get("role", name)],
                    calibration_score=0.85,
                )
    
    def get_settings_menu(self) -> str:
        """Return the main settings menu."""
        menu = """[#5AA5FF][bold]╭─ Membria Settings ─╮[/bold][/#5AA5FF]

[#FFB84D]🔌 Provider Management[/#FFB84D]
  /settings providers              List all providers (interactive)
  /settings toggle <name>          Enable/disable provider
  /settings set-key <name> <key>   Set or update API key
  /settings set-model <name> <m>   Change model for provider
  /settings test-provider <name>   Test provider connection
  /settings add-provider <n> <t>   Add new provider
  /settings remove <name>          Remove provider

[#FFB84D]👥 Roles & Agents[/#FFB84D]
  /settings roles                  List all expert roles
  /settings assign-role <r> <p>   Assign role to provider
  /settings calibrate <r> <score> Update accuracy score

[#FFB84D]⚙️  Advanced[/#FFB84D]
  /settings mode                   Show/change orchestration mode
  /settings monitoring             Set monitoring level
  /settings reset                  Reset to defaults

[#5AA5FF]╰──────────────────────────────╯[/#5AA5FF]
"""
        return menu
    
    def list_providers(self) -> str:
        """Interactive provider management menu with toggle/edit/test options."""
        if not self.providers:
            return "[yellow]No providers configured[/yellow]"
        
        output = "[#FFB84D][bold]╭─ Provider Manager ─╮[/bold][/#FFB84D]\n\n"
        
        for i, (name, provider) in enumerate(self.providers.items(), 1):
            status_icon = "[#21C93A]✓[/#21C93A]" if provider.enabled else "[red]✗[/red]"
            status_text = "[#21C93A]ENABLED[/#21C93A]" if provider.enabled else "[red]DISABLED[/red]"
            
            output += (
                f"{i}. {status_icon} [#5AA5FF][bold]{name}[/bold][/#5AA5FF] ({status_text})\n"
                f"   Type: {provider.type} | Model: [#FFB84D]{provider.model}[/#FFB84D]\n"
                f"   Endpoint: {provider.endpoint or '[#E8E8E8]default[/#E8E8E8]'}\n"
                f"   Auth: {'[#21C93A]Configured[/#21C93A]' if provider.api_key else '[yellow]Missing[/yellow]'}\n\n"
            )
        
        output += "[#FFB84D]Quick Commands:[/#FFB84D]\n"
        output += "  /settings toggle <name>        Enable/disable provider\n"
        output += "  /settings set-key <name> <key> Set API key\n"
        output += "  /settings set-model <name> <m> Change model\n"
        output += "  /settings test-provider <name> Test connection\n"
        output += "  /settings add-provider <name>  Add new provider\n"
        output += "  /settings remove <name>        Remove provider\n"
        output += "\n[#FFB84D]Example:[/#FFB84D]\n"
        output += "  /settings toggle openai        → Toggle OpenAI on/off\n"
        output += "  /settings test-provider kilo   → Test Kilo endpoint\n"
        output += "[#5AA5FF]╰──────────────────────╯[/#5AA5FF]"
        
        return output
    
    def toggle_provider(self, name: str) -> str:
        """Enable/disable a provider."""
        if name not in self.providers:
            return f"[red]Provider '{name}' not found[/red]"
        
        provider = self.providers[name]
        provider.enabled = not provider.enabled
        self._save_settings()
        
        status = "[#21C93A]ENABLED[/#21C93A]" if provider.enabled else "[red]DISABLED[/red]"
        return f"[#21C93A]✓ Provider '{name}' {status}[/#21C93A]"
    
    def set_provider_key(self, name: str, api_key: str) -> str:
        """Set API key for a provider."""
        if name not in self.providers:
            return f"[red]Provider '{name}' not found[/red]"
        
        provider = self.providers[name]
        # Store last 4 chars of key for verification
        key_suffix = api_key[-4:] if len(api_key) >= 4 else "****"
        provider.api_key = api_key
        self._save_settings()
        
        return f"[#21C93A]✓ API key set for '{name}' (ends with: {key_suffix})[/#21C93A]"
    
    def set_provider_model(self, name: str, model: str) -> str:
        """Change the model for a provider."""
        if name not in self.providers:
            return f"[red]Provider '{name}' not found[/red]"
        
        provider = self.providers[name]
        old_model = provider.model
        provider.model = model
        self._save_settings()
        
        return f"[#21C93A]✓ Model updated: {old_model} → {model}[/#21C93A]"
    
    def remove_provider(self, name: str) -> str:
        """Remove a provider from configuration."""
        if name not in self.providers:
            return f"[red]Provider '{name}' not found[/red]"
        
        del self.providers[name]
        # Also remove from config
        if hasattr(self.config_manager.config, 'providers') and name in self.config_manager.config.providers:
            del self.config_manager.config.providers[name]
        
        self._save_settings()
        return f"[#21C93A]✓ Provider '{name}' removed[/#21C93A]"
    
    def add_provider(self, name: str, provider_type: str, **kwargs) -> str:
        """Add a new provider."""
        if name in self.providers:
            return f"[red]Provider '{name}' already exists[/red]"
        
        provider = Provider(
            name=name,
            type=provider_type,
            api_key=kwargs.get("api_key", ""),
            endpoint=kwargs.get("endpoint", ""),
            model=kwargs.get("model", "gpt-4"),
            enabled=True
        )
        
        self.providers[name] = provider
        self._save_settings()
        
        return f"[#21C93A]✓ Provider '{name}' added successfully[/#21C93A]"
    
    def list_roles(self) -> str:
        """List all expert roles."""
        if not self.roles:
            return "[yellow]No roles configured[/yellow]"
        
        output = "[#FFB84D]Expert Roles:[/#FFB84D]\n\n"
        for name, role in self.roles.items():
            calibration_color = "#21C93A" if role.calibration_score > 0.8 else "#FFB84D"
            output += (
                f"[#5AA5FF]{role.title}[/#5AA5FF] ({name})\n"
                f"   {role.description}\n"
                f"   Calibration: {calibration_color}{role.calibration_score:.1%}[/{calibration_color}]\n"
                f"   Provider: {role.provider} | Capabilities: {', '.join(role.capabilities)}\n\n"
            )
        
        return output
    
    def assign_role(self, role_name: str, provider: str, model: str = "gpt-4") -> str:
        """Assign a role to an agent with specific provider."""
        if role_name not in self.roles:
            return f"[red]Unknown role: {role_name}[/red]"
        
        if provider not in self.providers:
            return f"[red]Unknown provider: {provider}[/red]"
        
        role = self.roles[role_name]
        role.provider = provider
        role.model = model
        
        self._save_settings()
        
        return (
            f"[#21C93A]✓ Role '{role_name}' assigned to provider '{provider}'[/#21C93A]\n"
            f"   Model: {model}"
        )
    
    def calibrate_agent(self, role_name: str, accuracy: float) -> str:
        """Update calibration score for an agent."""
        if role_name not in self.roles:
            return f"[red]Unknown role: {role_name}[/red]"
        
        # Clamp accuracy to 0.0-1.0
        accuracy = max(0.0, min(1.0, accuracy))
        
        role = self.roles[role_name]
        old_score = role.calibration_score
        role.calibration_score = accuracy
        
        self._save_settings()
        
        trend = "📈" if accuracy > old_score else "📉" if accuracy < old_score else "➡️"
        return (
            f"[#21C93A]✓ Calibrated '{role_name}'[/#21C93A]\n"
            f"   {old_score:.1%} → {trend} {accuracy:.1%}"
        )
    
    def get_provider_info(self, name: str) -> Optional[Provider]:
        """Get provider configuration."""
        return self.providers.get(name)

    def _migrate_providers_if_needed(self, providers: Dict[str, dict]) -> bool:
        """Detect & migrate outdated provider configs in-place.

        - add missing `kilo` provider (disabled by default)
        - upgrade common old model names to current defaults
        Returns True if any change was made.
        """
        changed = False
        # Ensure Kilo provider exists (disabled by default)
        if 'kilo' not in providers:
            providers['kilo'] = {
                'type': 'kilo',
                'model': 'kilo-code',
                'api_key': '',
                'endpoint': 'http://kilo.ai',
                'enabled': False,
            }
            changed = True
        if 'openrouter' not in providers:
            providers['openrouter'] = {
                'type': 'openrouter',
                'model': 'kilo-code',
                'api_key': '',
                'endpoint': 'https://openrouter.ai/api/v1',
                'enabled': False,
            }
            changed = True

        # Normalize Anthropic model names
        anthropic = providers.get('anthropic')
        if anthropic and isinstance(anthropic, dict):
            model = str(anthropic.get('model', '') or '')
            # if model is old or unspecified, upgrade to recommended latest
            if not model or ('claude-3-5-sonnet' not in model and model.startswith('claude')):
                anthropic['model'] = 'claude-3-5-sonnet-latest'
                changed = True

        # Normalize OpenAI model names
        openai = providers.get('openai')
        if openai and isinstance(openai, dict):
            model = str(openai.get('model', '') or '')
            if model == 'gpt-4' or (model and 'turbo' not in model and model.startswith('gpt')):
                openai['model'] = 'gpt-4-turbo'
                changed = True

        # Lightweight scan for obviously deprecated keys (e.g. old provider names)
        # (no-op but left for future extensions)

        return changed

    def _refresh_models_from_api(self, providers: Dict[str, dict]) -> bool:
        """Attempt to fetch latest available models from provider APIs.
        
        Updates provider models in place with the first available model from API.
        Returns True if any models were updated.
        """
        changed = False
        
        # Try to fetch anthropic models if api_key provided
        anthropic = providers.get('anthropic')
        if anthropic and anthropic.get('api_key'):
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                models = loop.run_until_complete(
                    self.model_fetcher.fetch_anthropic_models(anthropic['api_key'])
                )
                loop.close()
                if models:
                    old_model = anthropic.get('model', '')
                    anthropic['model'] = models[0]
                    if old_model != anthropic['model']:
                        changed = True
                        print(f"[DEBUG] Updated Anthropic model: {old_model} → {anthropic['model']}")
            except Exception as e:
                print(f"[DEBUG] Could not fetch Anthropic models: {e}")
        
        # Try to fetch OpenAI models if api_key provided
        openai = providers.get('openai')
        if openai and openai.get('api_key'):
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                models = loop.run_until_complete(
                    self.model_fetcher.fetch_openai_models(openai['api_key'])
                )
                loop.close()
                if models:
                    old_model = openai.get('model', '')
                    openai['model'] = models[0]
                    if old_model != openai['model']:
                        changed = True
                        print(f"[DEBUG] Updated OpenAI model: {old_model} → {openai['model']}")
            except Exception as e:
                print(f"[DEBUG] Could not fetch OpenAI models: {e}")
        
        # Try to fetch Kilo models if enabled and api_key provided
        kilo = providers.get('kilo')
        if kilo and kilo.get('enabled') and kilo.get('api_key'):
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                models = loop.run_until_complete(
                    self.model_fetcher.fetch_kilo_models(
                        kilo.get('endpoint', ''), 
                        kilo['api_key']
                    )
                )
                loop.close()
                if models:
                    old_model = kilo.get('model', '')
                    kilo['model'] = models[0]
                    if old_model != kilo['model']:
                        changed = True
                        print(f"[DEBUG] Updated Kilo model: {old_model} → {kilo['model']}")
            except Exception as e:
                print(f"[DEBUG] Could not fetch Kilo models: {e}")
        
        return changed    
    def get_role_info(self, name: str) -> Optional[Role]:
        """Get role configuration."""
        return self.roles.get(name)
    
    def _save_settings(self):
        """Save settings to config file."""
        # Convert dataclasses to dicts
        providers_dict = {
            name: {
                "name": p.name,
                "type": p.type,
                "api_key": p.api_key,
                "endpoint": p.endpoint,
                "model": p.model,
                "enabled": p.enabled,
            }
            for name, p in self.providers.items()
        }
        
        roles_dict = {
            name: {
                "name": r.name,
                "title": r.title,
                "description": r.description,
                "provider": r.provider,
                "model": r.model,
                "capabilities": r.capabilities,
                "calibration_score": r.calibration_score,
            }
            for name, r in self.roles.items()
        }
        
        # Update config
        self.config_manager.config["providers"] = providers_dict
        self.config_manager.config["roles"] = roles_dict
        self.config_manager.save()
    
    def set_provider_api_key(self, provider_name: str, api_key: str) -> str:
        """Set API key for a provider and test connection."""
        if provider_name not in self.providers:
            return f"[red]Unknown provider: {provider_name}[/red]"
        
        provider = self.providers[provider_name]
        provider.api_key = api_key
        
        # Update config
        self.config_manager.config["providers"][provider_name]["api_key"] = api_key
        self.config_manager.save()
        
        # Test the connection
        return self.test_provider_connection(provider_name)
    
    def test_provider_connection(self, provider_name: str) -> str:
        """Test connection to a provider's API."""
        if provider_name not in self.providers:
            return f"[red]Unknown provider: {provider_name}[/red]"
        
        provider = self.providers[provider_name]
        
        if not provider.api_key:
            return f"[yellow]⚠️  Provider '{provider_name}' has no API key configured[/yellow]"
        
        # Test by fetching models
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            if provider.type == "anthropic":
                models = loop.run_until_complete(
                    self.model_fetcher.fetch_anthropic_models(provider.api_key)
                )
                if models:
                    provider.model = models[0]
                    # Update config with new model
                    self.config_manager.config["providers"][provider_name]["model"] = models[0]
                    self.config_manager.save()
                    return (
                        f"[#21C93A]✓ Connected to Anthropic successfully![/#21C93A]\n"
                        f"   Available models: {', '.join(models[:3])}\n"
                        f"   Active model: {models[0]}"
                    )
            
            elif provider.type == "openai":
                models = loop.run_until_complete(
                    self.model_fetcher.fetch_openai_models(provider.api_key)
                )
                if models:
                    provider.model = models[0]
                    self.config_manager.config["providers"][provider_name]["model"] = models[0]
                    self.config_manager.save()
                    return (
                        f"[#21C93A]✓ Connected to OpenAI successfully![/#21C93A]\n"
                        f"   Available models: {', '.join(models[:3])}\n"
                        f"   Active model: {models[0]}"
                    )
            
            elif provider.type == "kilo":
                models = loop.run_until_complete(
                    self.model_fetcher.fetch_kilo_models(
                        provider.endpoint or "http://kilo.ai",
                        provider.api_key
                    )
                )
                if models:
                    provider.model = models[0]
                    self.config_manager.config["providers"][provider_name]["model"] = models[0]
                    self.config_manager.save()
                    return (
                        f"[#21C93A]✓ Connected to Kilo successfully![/#21C93A]\n"
                        f"   Available models: {', '.join(models[:3])}\n"
                        f"   Active model: {models[0]}"
                    )
            
            loop.close()
            return f"[red]✗ Connection failed: No models received[/red]"
            
        except Exception as e:
            return f"[red]✗ Connection failed: {str(e)}[/red]"
