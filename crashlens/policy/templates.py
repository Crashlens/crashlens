#!/usr/bin/env python3
"""
Policy Template Manager for CrashLens
Handles loading and management of built-in policy templates
"""

import os
import yaml
from pathlib import Path
from typing import Dict, List, Any, Optional, Set
from .engine import PolicyEngine

class TemplateManager:
    """Manages built-in policy templates"""
    
    def __init__(self):
        self.template_dir = Path(__file__).parent / "templates"
        self._available_templates = None
    
    @property
    def available_templates(self) -> Dict[str, Dict[str, Any]]:
        """Get list of available policy templates with metadata"""
        if self._available_templates is None:
            self._load_template_catalog()
        return self._available_templates or {}
    
    def _load_template_catalog(self):
        """Load and cache template catalog"""
        self._available_templates = {}
        
        if not self.template_dir.exists():
            return
        
        for template_file in self.template_dir.glob("*.yaml"):
            if template_file.name == "README.md":
                continue
                
            try:
                with open(template_file, 'r', encoding='utf-8') as f:
                    template_data = yaml.safe_load(f)
                
                template_id = template_file.stem
                metadata = template_data.get('metadata', {})
                
                self._available_templates[template_id] = {
                    'file_path': template_file,
                    'name': metadata.get('name', template_id),
                    'description': metadata.get('description', ''),
                    'category': metadata.get('category', 'general'),
                    'severity_level': metadata.get('severity_level', 'medium'),
                    'estimated_savings': metadata.get('estimated_savings', 'varies'),
                    'rule_count': len(template_data.get('rules', [])),
                    'metadata': metadata
                }
            except Exception as e:
                print(f"Warning: Could not load template {template_file}: {e}")
                continue
    
    def get_template_path(self, template_name: str) -> Optional[Path]:
        """Get the file path for a template by name"""
        if template_name in self.available_templates:
            return self.available_templates[template_name]['file_path']
        
        # Try with .yaml extension
        template_file = self.template_dir / f"{template_name}.yaml"
        if template_file.exists():
            return template_file
        
        return None
    
    def load_template(self, template_name: str) -> Optional[PolicyEngine]:
        """Load a specific template as a PolicyEngine"""
        template_path = self.get_template_path(template_name)
        if not template_path:
            return None
        
        try:
            engine = PolicyEngine(template_path)
            return engine
        except Exception as e:
            print(f"Error loading template '{template_name}': {e}")
            return None
    
    def load_multiple_templates(self, template_names: List[str]) -> Optional[PolicyEngine]:
        """Load multiple templates into a single PolicyEngine"""
        combined_rules = []
        
        for template_name in template_names:
            template_path = self.get_template_path(template_name)
            if not template_path:
                print(f"Warning: Template '{template_name}' not found, skipping")
                continue
            
            try:
                with open(template_path, 'r', encoding='utf-8') as f:
                    template_data = yaml.safe_load(f)
                
                rules = template_data.get('rules', [])
                # Add template source info to each rule
                for rule in rules:
                    rule['_template_source'] = template_name
                
                combined_rules.extend(rules)
                
            except Exception as e:
                print(f"Warning: Could not load template '{template_name}': {e}")
                continue
        
        if not combined_rules:
            return None
        
        # Create a temporary combined policy
        combined_policy = {
            'metadata': {
                'name': 'Combined Templates',
                'templates': template_names
            },
            'rules': combined_rules
        }
        
        # Create a temporary file for the combined policy
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as temp_file:
            yaml.dump(combined_policy, temp_file, default_flow_style=False)
            temp_path = Path(temp_file.name)
        
        try:
            engine = PolicyEngine(temp_path)
            # Clean up temp file
            temp_path.unlink()
            return engine
        except Exception as e:
            # Clean up temp file on error
            if temp_path.exists():
                temp_path.unlink()
            print(f"Error creating combined policy engine: {e}")
            return None
    
    def load_all_templates(self) -> Optional[PolicyEngine]:
        """Load all available templates into a single PolicyEngine"""
        template_names = list(self.available_templates.keys())
        if not template_names:
            print("No templates available")
            return None
        
        return self.load_multiple_templates(template_names)
    
    def list_templates(self) -> None:
        """Print a formatted list of available templates"""
        if not self.available_templates:
            print("No templates available")
            return
        
        print("📜 Available CrashLens Policy Templates:")
        print("=" * 50)
        
        for template_id, info in self.available_templates.items():
            print(f"• {template_id}")
            print(f"  Name: {info['name']}")
            print(f"  Category: {info['category']}")
            print(f"  Rules: {info['rule_count']}")
            print(f"  Savings: {info['estimated_savings']}")
            print(f"  Description: {info['description']}")
            print()
    
    def get_templates_by_category(self, category: str) -> List[str]:
        """Get template names filtered by category"""
        return [
            template_id for template_id, info in self.available_templates.items()
            if info['category'] == category
        ]
    
    def get_template_categories(self) -> Set[str]:
        """Get all available template categories"""
        return {info['category'] for info in self.available_templates.values()}


# Global template manager instance
_template_manager = None

def get_template_manager() -> TemplateManager:
    """Get the global template manager instance"""
    global _template_manager
    if _template_manager is None:
        _template_manager = TemplateManager()
    return _template_manager
