import io
import logging
import re
import time
from string import Template

import pyperclip
from PIL import Image, ImageGrab
from pynput.keyboard import Controller, Key, KeyCode, Listener

from .config import Settings
from .llm import call_ollama


class ClipAssistant:
    """The conductor of this strange orchestra"""

    def __init__(self, settings: Settings):
        self.settings = settings
        self.controller = Controller()
        self.current_keys: set[Key | KeyCode | None] = set()

        self.prompts: dict[str, Template] = {
            name: Template(details.template) for name, details in self.settings.prompts.items()
        }
        self.actions: dict[KeyCode, str] = self._initialize_actions()

        # A brief, respectful pause.
        self.clipboard_delay = self.settings.app.clipboard_delay

    def _initialize_actions(self) -> dict[KeyCode, str]:
        """Maps mortal keystrokes to divine actions"""
        action_map = {}
        for name, details in self.settings.prompts.items():
            try:
                action_map[KeyCode.from_char(details.shortcut)] = name
            except (ValueError, TypeError):
                # Some shortcuts are just not meant to be.
                logging.warning(
                    "Shortcut '%s' for action '%s' is weird. Ignoring it",
                    details.shortcut,
                    name,
                )
        return action_map

    def _get_clipboard_content(self, content_type: str = "text"):
        """A desperate grab for whatever is in the clipboard's soul"""
        try:
            with self.controller.pressed(Key.ctrl):
                self.controller.tap("c")
            time.sleep(self.clipboard_delay)

            if content_type == "text":
                return pyperclip.paste() or None
            if content_type == "image":
                img = ImageGrab.grabclipboard()
                if not isinstance(img, Image.Image):
                    return None
                buffer = io.BytesIO()
                img.save(buffer, format="PNG")
                return buffer.getvalue()
            return None
        except Exception as e:
            # The clipboard is a fickle beast.
            logging.error("Failed to commune with the clipboard: %s", e)
            return None

    def _set_clipboard_text(self, text: str) -> None:
        """Places the processed text back into the void, then unleashes it"""
        try:
            pyperclip.copy(text)
            time.sleep(self.clipboard_delay / 2)
            with self.controller.pressed(Key.ctrl):
                self.controller.tap("v")
            logging.info("Mission accomplished. The text has been... pasted")
        except Exception as e:
            logging.error("Could not paste. The system resists. %s", e)

    def _clean_code_snippet(self, response: str) -> str:
        """Strips the LLM's rambling preamble from a code block"""
        if match := re.search(r"```(?:\w+)?\s*(.*?)\s*```", response, re.DOTALL):
            return match.group(1).strip()
        return response  # If there's no code block, we just return the raw, untamed text.

    def _process_action(self, action_name: str) -> None:
        """The main dispatch logic. One function to rule them all"""
        logging.info("Action '%s' triggered. Let's do this", action_name)
        action_config = self.settings.prompts[action_name]

        content = self._get_clipboard_content(action_config.type)
        if not content:
            logging.warning("Action cancelled. The clipboard was empty, like my soul")
            return

        images = None
        if action_config.type == "vision":
            # The vision, it's... temporarily blind. Awaiting a miracle.
            logging.warning("Vision processing is a dream for another day. Aborting")
            return
            # images = [base64.b64encode(content).decode("utf-8")]
            # prompt_text = self.prompts[action_name].substitute()
        else:
            # TODO: A more elegant way to handle dynamic prompt args. For now, we brute-force it.
            # This is where the sausage gets made.
            try:
                if action_name == "traducir_texto":
                    prompt_text = self.prompts[action_name].substitute(text=content, idioma="inglés")
                elif action_name == "cambiar_tono":
                    prompt_text = self.prompts[action_name].substitute(text=content, tono="formal")
                else:
                    prompt_text = self.prompts[action_name].substitute(text=content)
            except KeyError as e:
                logging.error("Prompt for '%s' is missing a placeholder: %s", action_name, e)
                return

        response = call_ollama(prompt_text, self.settings.ollama, images=images)
        if not response:
            logging.warning("Action '%s' yielded nothing. The void stares back", action_name)
            return

        if "python" in action_name:
            response = self._clean_code_snippet(response)

        self._set_clipboard_text(response)

    def _on_press(self, key: Key | KeyCode | None) -> None:
        """Listens for the whispers of the keyboard"""
        if isinstance(key, (Key, KeyCode)):
            self.current_keys.add(key)

        is_modifier_pressed = Key.ctrl in self.current_keys or Key.cmd in self.current_keys

        if key in self.actions and is_modifier_pressed:
            self._process_action(self.actions[key])

    def _on_release(self, key: Key | KeyCode | None) -> None:
        """Forgets the key ever existed"""
        if key in self.current_keys:
            self.current_keys.remove(key)

    def run(self) -> None:
        """Starts the eternal watch"""
        logging.info("ClipAssistant is now watching. Silently. Always")
        logging.info("Text Model: %s, Vision Model: %s", self.settings.ollama.text_model, self.settings.ollama.vision_model)
        logging.info("Press Ctrl + [shortcut] to summon the spirits")

        try:
            with Listener(on_press=self._on_press, on_release=self._on_release) as listener:
                listener.join()
        except Exception as e:
            logging.critical("The listener has fallen and it can't get up: %s", e)
        finally:
            # Live with dignity, die like a pig.
            logging.info("ClipAssistant has ceased its watch")
