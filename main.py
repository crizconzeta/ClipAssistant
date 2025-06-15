"""
ClipAssistant: Utilidad para delegar tareas simples a LLMs locales
mediante atajos de teclado y el portapapeles.
"""

import base64
import io
import logging
import re
import time
from string import Template
from typing import Any, Dict, Optional, Set

import ollama
import pyperclip
import yaml
from PIL import Image, ImageGrab
from pynput.keyboard import Controller, Key, KeyCode, Listener

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(module)s - %(message)s")


class ClipAssistant:
    """
    Clase principal que encapsula la lógica de ClipAssistant.

    Gestiona la configuración, la interacción con Ollama, el manejo del portapapeles
    y la escucha de atajos de teclado para ejecutar acciones predefinidas.
    """

    def __init__(self, config_path: str = "config.yaml"):
        """
        Inicializa ClipAssistant.

        Args:
            config_path (str): Ruta al archivo de configuración YAML.
        """
        self.config = self._load_config(config_path)
        if not self.config:
            logging.critical("No se pudo cargar la configuración. Terminando.")
            # Terminar el programa
            exit(1)

        self.controller = Controller()
        self.text_model = self.config["ollama"]["text_model"]
        self.vision_model = self.config["ollama"]["vision_model"]
        self.ollama_options = {
            "keep_alive": self.config["ollama"]["keep_alive"],
            "stream": self.config["ollama"]["stream"],
            "temperature": 0.1,
        }

        # Pre-compilar las plantillas para eficiencia
        self.prompts = self._initialize_prompts()
        self.actions = self._initialize_actions()

        self.current_keys: Set[Key | KeyCode | None] = set()

        self.clipboard_delay = self.config.get("app", {}).get("clipboard_delay", 0.2)

    def _load_config(self, file_path: str) -> Optional[Dict[str, Any]]:
        """
        Carga la configuración desde un archivo YAML de forma segura.

        Args:
            file_path (str): Ruta al archivo YAML.

        Returns:
            Optional[Dict[str, Any]]: Diccionario de configuración o None si ocurre un error.
        """
        try:
            with open(file_path, encoding="utf-8") as file:
                config_data = yaml.safe_load(file)
                # Validación básica de la estructura esperada
                if not all(k in config_data for k in ["ollama", "prompts"]):
                    logging.error("Archivo de configuración incompleto. Faltan secciones 'ollama' o 'prompts'.")
                    return None
                logging.info("Configuración cargada exitosamente desde %s", file_path)
                return config_data
        except FileNotFoundError:
            logging.error("Archivo de configuración no encontrado en: %s", file_path)
            return None
        except yaml.YAMLError as e:
            logging.error("Error al parsear el archivo de configuración YAML: %s", e)
            return None
        except Exception as e:
            logging.error("Error inesperado al cargar la configuración: %s", e)
            return None

    def _initialize_prompts(self) -> Dict[str, Template]:
        """Prepara las plantillas de prompt desde la configuración."""
        return {k: Template(v["template"]) for k, v in self.config["prompts"].items()}

    def _initialize_actions(self) -> Dict[KeyCode, str]:
        """
        Crea el mapeo desde KeyCode (atajo) a nombre de la acción.

        Returns:
            Dict[KeyCode, str]: Diccionario que mapea objetos KeyCode a identificadores de acción.
        """
        actions_map = {}
        for action_name, details in self.config["prompts"].items():
            shortcut = details.get("shortcut")
            if shortcut:
                try:
                    # Usamos KeyCode.from_char para manejar caracteres simples
                    key_code = KeyCode.from_char(shortcut)
                    actions_map[key_code] = action_name
                except ValueError:
                    # TODO
                    # Manejar casos donde el atajo no sea un caracter simple (ej. teclas especiales)
                    # Esto requeriría una lógica más compleja si se necesitan teclas como F1, etc.
                    logging.warning(
                        "Atajo '%s' para la acción '%s' no es un caracter simple y será ignorado.", shortcut, action_name
                    )
            else:
                logging.warning("La acción '%s' no tiene un 'shortcut' definido.", action_name)
        return actions_map

    def _clean_code_snippet(self, response_text: str) -> str:
        """
        Limpia bloques de código de las respuestas del LLM.
        Elimina los delimitadores ```python ... ``` y similares.

        Args:
            response_text (str): Texto de respuesta del LLM.

        Returns:
            str: El código extraído y limpio, o el texto original si no hay bloque de código.
        """
        # Regex mejorado para capturar opcionalmente el lenguaje y ser más robusto
        code_block_match = re.search(r"```(?:\w+)?\s*(.*?)\s*```", response_text, re.DOTALL | re.MULTILINE)
        if code_block_match:
            # Si encuentra un bloque de código, retorna solo el contenido
            return code_block_match.group(1).strip()
        else:
            # Esto es heurístico y puede necesitar ajustes.
            lines = response_text.strip().split("\n")
            if len(lines) > 2 and lines[0].lower().startswith(("here is", "here's", "el código")):
                lines = lines[1:]
            if lines and lines[-1].lower().startswith(("note:", "remember", "este código")):
                lines = lines[:-1]
            # Devuelve el texto potencialmente limpiado o el original si no se aplicó heurística
            return "\n".join(lines).strip()

    def _call_ollama(self, model: str, prompt: str, images: Optional[list[str]] = None) -> Optional[str]:
        """
        Realiza una llamada segura a la API de Ollama.

        Args:
            model (str): Nombre del modelo a usar.
            prompt (str): El prompt para enviar al modelo.
            images (Optional[list[str]]): Lista de imágenes en base64 (para modelos de visión).

        Returns:
            Optional[str]: La respuesta del modelo o None si hay un error.
        """
        try:
            logging.info("Enviando solicitud a Ollama (Modelo: %s)", model)
            logging.debug("Prompt: %s", prompt)
            response = ollama.generate(
                model=model, prompt=prompt, images=images if images else [], options=self.ollama_options
            )
            result = response.get("response")
            if result:
                stripped_result = result.strip()
                if stripped_result:
                    logging.info("Respuesta recibida y validada de Ollama.")
                    return stripped_result
                else:
                    logging.warning("Ollama devolvió una respuesta que solo contenía espacios en blanco.")
                    return None
            else:
                logging.warning("Ollama devolvió una respuesta vacía o sin la clave 'response'.")
                return None

        except ollama.ResponseError as e:
            logging.error("Error en la respuesta de Ollama (status %s): %s", e.status_code, e.error)
            return None
        except Exception as e:
            logging.error("Error inesperado al comunicarse con Ollama: %s", e)
            return None

    def _get_clipboard_content(self, content_type: str = "text") -> Optional[str | bytes]:
        """
        Obtiene contenido del portapapeles de forma segura (texto o imagen).

        Args:
            content_type (str): "text" o "image".

        Returns:
            Optional[str | bytes]: Contenido como texto (str) o imagen PNG (bytes), o None si falla.
        """
        try:
            # Simula Ctrl+C para asegurar que el contenido seleccionado esté en el portapapeles
            with self.controller.pressed(Key.ctrl):
                self.controller.tap("c")
            time.sleep(self.clipboard_delay)

            if content_type == "text":
                content = pyperclip.paste()
                if isinstance(content, str) and content:
                    logging.info("Texto obtenido del portapapeles.")
                    # logging.debug("Texto: %s", content[:100] + "...")
                    return content
                else:
                    logging.warning("No se encontró texto válido en el portapapeles.")
                    return None
            elif content_type == "image":
                image = None
                try:
                    image = ImageGrab.grabclipboard()

                    if isinstance(image, Image.Image):
                        img_format = getattr(image, "format", "N/A")
                        img_mode = getattr(image, "mode", "N/A")
                        img_size = getattr(image, "size", "N/A")
                        logging.info(
                            f"Imagen detectada en portapapeles. Info PIL: Formato={img_format}, Modo={img_mode}, Tamaño={img_size}"
                        )

                        buffer = io.BytesIO()
                        image.save(buffer, format="PNG")
                        logging.info("Imagen convertida a PNG en memoria.")
                        return buffer.getvalue()

                    elif image is not None:
                        logging.warning(
                            f"Contenido del portapapeles no es un objeto PIL Image reconocido. Tipo recibido: {type(image)}"
                        )
                        return None
                    else:
                        logging.warning(
                            "No se encontró una imagen en el portapapeles (ImageGrab.grabclipboard() devolvió None)."
                        )
                        return None

                except (OSError, ValueError, TypeError, SyntaxError) as e:
                    # Este bloque captura errores tanto de ImageGrab como de image.save
                    # Loguear detalles de la imagen si se llegó a obtener el objeto
                    details = (
                        f"Info PIL: Formato={getattr(image, 'format', 'N/A')}, Modo={getattr(image, 'mode', 'N/A')}"
                        if image
                        else "No se pudo obtener objeto Image."
                    )
                    logging.error(f"Error al obtener o procesar la imagen del portapapeles: {e}. {details}", exc_info=True)
                    return None
            else:
                logging.error("Tipo de contenido no soportado: %s", content_type)
                return None

        except pyperclip.PyperclipException as e:
            logging.error("Error de Pyperclip al acceder al portapapeles (texto): %s", e, exc_info=True)
            return None
        # Quitado el catch genérico aquí para que el catch específico de imagen funcione mejor
        # except Exception as e:
        #    logging.error("Error inesperado al acceder al portapapeles: %s", e, exc_info=True)
        #    return None

    def _set_clipboard_text(self, text: str) -> bool:
        """
        Coloca texto en el portapapeles y simula Ctrl+V.

        Args:
            text (str): Texto a colocar en el portapapeles.

        Returns:
            bool: True si tuvo éxito, False en caso contrario.
        """
        try:
            pyperclip.copy(text)
            logging.info("Texto procesado copiado al portapapeles.")
            # Pausa antes de pegar para asegurar que el portapapeles se actualizó
            time.sleep(self.clipboard_delay / 2)
            with self.controller.pressed(Key.ctrl):
                self.controller.tap("v")
            logging.info("Texto pegado simulando Ctrl+V.")
            return True
        except pyperclip.PyperclipException as e:
            logging.error("Error de Pyperclip al copiar al portapapeles: %s", e)
            return False
        except Exception as e:
            logging.error("Error inesperado al pegar desde el portapapeles: %s", e)
            return False

    def _process_text_action(self, action: str, **kwargs) -> None:
        """
        Orquesta el procesamiento de una acción de texto:
        Obtiene texto -> Llama a Ollama -> Pega resultado.
        """
        input_text = self._get_clipboard_content("text")
        if not input_text:
            logging.warning("Acción '%s' cancelada: no se pudo obtener texto.", action)
            return

        logging.info("Ejecutando acción de texto: '%s'", action)
        try:
            # Sustituir placeholders en la plantilla del prompt
            prompt = self.prompts[action].substitute(text=input_text, **kwargs)
        except KeyError as e:
            # Si falta un placeholder esperado en kwargs (p.ej. 'idioma')
            logging.error("Error al generar prompt para '%s': Falta el argumento %s", action, e)
            return

        processed_text = self._call_ollama(self.text_model, prompt)
        if not processed_text:
            logging.warning("Acción '%s' cancelada: no se recibió respuesta del LLM.", action)
            return

        # Limpiar si es una acción de código Python
        if "python" in action:
            processed_text = self._clean_code_snippet(processed_text)

        self._set_clipboard_text(processed_text)

    def _process_image_action(self, action: str) -> None:
        """
        Orquesta el procesamiento de una acción de visión:
        Obtiene imagen -> Llama a Ollama (visión) -> Pega resultado (descripción/texto).
        """
        image_bytes = self._get_clipboard_content("image")
        if not image_bytes:
            logging.warning("Acción '%s' cancelada: no se pudo obtener imagen.", action)
            return

        # Codificar la imagen en base64 para Ollama
        image_base64 = base64.b64encode(image_bytes).decode("utf-8")

        logging.info("Ejecutando acción de visión: '%s'", action)
        # Las acciones de visión pueden no necesitar argumentos en el prompt
        prompt = self.prompts[action].substitute()

        description = self._call_ollama(self.vision_model, prompt, images=[image_base64])
        if not description:
            logging.warning("Acción '%s' cancelada: no se recibió descripción del LLM.", action)
            return

        # TODO
        # if self.config['prompts'][action].get('needs_translation'):
        #    description = self._translate_text(description, target_language='es')

        self._set_clipboard_text(description)

    def _on_press(self, key: Key | KeyCode | None) -> None:
        """
        Manejador de eventos para la pulsación de teclas.
        Identifica si la combinación de teclas activa una acción.
        """
        # Verificar si Ctrl (o Cmd en Mac) está presionado
        # pynput mapea Cmd a Key.cmd
        modifier_pressed = Key.ctrl in self.current_keys or Key.cmd in self.current_keys

        if key in self.actions and modifier_pressed:
            action = self.actions[key]
            action_config = self.config["prompts"][action]
            action_type = action_config.get("type", "text")  # Default a 'text'

            logging.info("Atajo detectado para acción: '%s' (Tipo: %s)", action, action_type)

            # TODO: Mejorar el manejo de parámetros dinámicos (ej. idioma, tono)
            #       Actualmente están hardcodeados aquí abajo. Podrían venir de la config
            #       o de una mini-GUI.
            if action_type == "vision":
                # self._process_image_action(action)
                # TODO
                logging.info("La funcionalidad de procesamiento de imágenes está temporalmente deshabilitada.")

            elif action_type == "text":
                if action == "traducir_texto":
                    self._process_text_action(action, idioma="inglés")
                elif action == "cambiar_tono":
                    self._process_text_action(action, tono="formal")
                else:
                    self._process_text_action(action)
            else:
                logging.warning("Tipo de acción '%s' no reconocido para '%s'.", action_type, action)

    def _on_release(self, key: Key | KeyCode | None) -> None:
        """
        Manejador de eventos para la liberación de teclas.
        Actualiza el conjunto de teclas presionadas.
        """
        if key in self.current_keys:
            self.current_keys.remove(key)

    def _on_press_mod(self, key: Key | KeyCode | None) -> None:
        """
        Wrapper para on_press que primero actualiza el estado de las teclas presionadas.
        """
        # Añadir la tecla presionada al conjunto DE INMEDIATO
        # Esto es crucial para detectar combinaciones como Ctrl+Tecla
        if isinstance(key, (Key, KeyCode)):
            self.current_keys.add(key)
        self._on_press(key)

    def run(self) -> None:
        """Inicia el escuchador de teclado y mantiene la aplicación corriendo."""
        logging.info("Iniciando ClipAssistant...")
        logging.info("Modelos configurados: Texto=%s, Visión=%s", self.text_model, self.vision_model)
        logging.info("Escuchando atajos de teclado (Ctrl + Tecla)...")

        try:
            with Listener(on_press=self._on_press_mod, on_release=self._on_release) as listener:
                listener.join()
        except Exception as e:
            logging.critical("Error fatal en el listener de teclado: %s", e, exc_info=True)
        finally:
            logging.info("ClipAssistant detenido.")


if __name__ == "__main__":
    assistant = ClipAssistant()
    assistant.run()
