import logging
from typing import Literal, Optional

import yaml
from pydantic import BaseModel, Field, ValidationError


class OllamaConfig(BaseModel):
    text_model: str
    vision_model: str
    keep_alive: str
    stream: bool


class PromptDetails(BaseModel):
    shortcut: str
    type: Literal["text", "vision"]
    template: str


class AppConfig(BaseModel):
    clipboard_delay: float = Field(0.2, gt=0)


class Settings(BaseModel):
    # We wrestled a gnarly YAML file into this beautiful, civilized thing
    ollama: OllamaConfig
    prompts: dict[str, PromptDetails]
    app: AppConfig

    @classmethod
    def load_from_yaml(cls, path: str) -> Optional["Settings"]:
        """Loads configuration from a YAML file, or dies trying"""
        try:
            with open(path, encoding="utf-8") as f:
                data = yaml.safe_load(f)
            return cls.model_validate(data)
        except FileNotFoundError:
            logging.critical("Config file not found at '%s'. The universe is indifferent", path)
            return None
        except (ValidationError, yaml.YAMLError) as e:
            logging.critical("Config file is a mess. Here's the autopsy report:\n%s", e)
            return None
