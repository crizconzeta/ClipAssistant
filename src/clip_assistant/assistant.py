import base64
import io
import logging
import re
import time
from string import Template

import httpx
import pyperclip
from PIL import Image, ImageGrab, UnidentifiedImageError
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
        self.clipboard_delay = self.settings.app.clipboard_delay

    def _initialize_actions(self) -> dict[KeyCode, str]:
        """Maps mortal keystrokes to machine actions"""
        action_map = {}
        for name, details in self.settings.prompts.items():
            try:
                if len(details.shortcut) == 1:
                    action_map[KeyCode.from_char(details.shortcut)] = name
                else:
                    logging.warning("Complex shortcut '%s' not yet implemented", details.shortcut)
            except (ValueError, TypeError):
                logging.warning(
                    "Shortcut '%s' for action '%s' is weird. Ignoring it",
                    details.shortcut,
                    name,
                )
        return action_map

    def _get_clipboard_image(self) -> bytes | None:
        """A more desperate, multi-pronged attempt to grab an image from the clipboard"""
        # 1. The direct approach with Pillow
        try:
            img = ImageGrab.grabclipboard()
            if isinstance(img, Image.Image):
                logging.info("Image found via ImageGrab")
                buffer = io.BytesIO()
                img.save(buffer, format="PNG")
                return buffer.getvalue()
        except Exception as e:
            logging.warning("ImageGrab failed, as it often does on Linux. Reason: %s", e)

        # 2. The textual approach. it's a path or a URL
        try:
            raw_content = pyperclip.paste()
            logging.debug("Raw clipboard content for image search: %s", repr(raw_content))
            if not raw_content:
                return None

            clipboard_content = raw_content.strip()

            if clipboard_content.startswith(("file://", "/")) and clipboard_content.lower().endswith(
                (".png", ".jpg", ".jpeg", ".webp")
            ):
                path = clipboard_content.replace("file://", "")
                logging.info("Clipboard contains a file path: %s", path)
                with open(path, "rb") as f:
                    img_bytes = f.read()
                Image.open(io.BytesIO(img_bytes))  # Verify it's an image
                return img_bytes

            if clipboard_content.startswith(("http://", "https://")):
                logging.info("Clipboard contains a URL, attempting to download: %s", clipboard_content)
                with httpx.Client(timeout=10.0) as client:
                    response = client.get(clipboard_content)
                    response.raise_for_status()
                Image.open(io.BytesIO(response.content))
                return response.content

        except (OSError, UnidentifiedImageError, httpx.RequestError) as e:
            logging.warning("Clipboard content looked like a path/URL, but failed to load as image: %s", e)
        except Exception as e:
            logging.error("An unexpected existential crisis in _get_clipboard_image: %s", e)

        return None

    def _get_clipboard_content(self, content_type: str) -> str | bytes | None:
        """
        Grabs content from the clipboard, assuming the user has already copied it.
        This function is the single entry point for getting clipboard data.
        """
        logging.debug("Attempting to fetch clipboard content of type '%s'", content_type)
        try:
            time.sleep(0.05)

            if content_type == "text":
                content = pyperclip.paste()
                if content:
                    logging.info("Text obtained from clipboard")
                    return content
                logging.warning("No text found in clipboard")
                return None

            if content_type == "vision":
                logging.debug("Content type is 'vision', proceeding to image search")
                image_bytes = self._get_clipboard_image()
                if image_bytes:
                    logging.info("Image bytes successfully captured")
                    return image_bytes
                logging.warning("No image found in clipboard after extensive searching")
                return None

            logging.error("Unsupported content type requested: '%s'", content_type)
            return None

        except Exception as e:
            logging.error("A catastrophic failure occurred while communing with the clipboard: %s", e, exc_info=True)
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
        return response

    def _process_action(self, action_name: str) -> None:
        """The main dispatch logic. One function to rule them all"""
        logging.info("Action '%s' triggered. Let's do this", action_name)
        action_config = self.settings.prompts[action_name]

        content = self._get_clipboard_content(action_config.type)
        if not content:
            logging.warning("Action cancelled. The clipboard was empty, like my soul")
            return

        images_b64 = None
        prompt_text = ""

        if action_config.type == "vision":
            if isinstance(content, bytes):
                images_b64 = [base64.b64encode(content).decode("utf-8")]
                prompt_text = self.prompts[action_name].substitute()
                logging.info("Prepared image for Ollama (first 100 chars of base64): %s..", images_b64[0][:100])
            else:
                logging.error("Vision action triggered, but content is not bytes. This shouldn't happen")
                return
        else:  # text action
            if not isinstance(content, str):
                logging.error("Text action triggered, but content is not a string. This is weird")
                return
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

        response = call_ollama(prompt_text, self.settings.ollama, images=images_b64)
        if not response:
            logging.warning("Action '%s' yielded nothing. The void stares back", action_name)
            return

        if "python" in action_name:
            response = self._clean_code_snippet(response)

        self._set_clipboard_text(response)

    def _on_press(self, key: Key | KeyCode | None) -> None:
        """Listens for the whispers of the keyboard"""
        if isinstance(key, Key | KeyCode):
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
            logging.info("ClipAssistant has ceased its watch")
