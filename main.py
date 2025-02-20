"""
ClipAssistant funciones simples que puedo delegar a un LLM pequeño para disminuir mi carga cognitiva
"""

import re
import io
import time
import base64
import logging
from string import Template
import yaml
from pynput import keyboard
from pynput.keyboard import Key, KeyCode, Controller
import pyperclip
from PIL import ImageGrab
import ollama

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')


def load_config(file_path: str = 'config.yaml') -> dict:
    """Carga y retorna la configuración desde un archivo YAML."""
    with open(file_path, 'r', encoding='utf-8') as file:
        return yaml.safe_load(file)


config = load_config()

# Ollama

controller = Controller()

TEXT_MODEL = config['ollama']['text_model']
VISION_MODEL = config['ollama']['vision_model']
OLLAMA_CONFIG = {
    "keep_alive": config['ollama']['keep_alive'],
    "stream": config['ollama']['stream'],
}
PROMPTS = {k: Template(v['template']) for k, v in config['prompts'].items()}


def clean_code(response_text: str) -> str:
    """
    Elimina etiquetas de código y retorna solo el código limpio.

    Args:
        response_text (str): Respuesta original que puede contener delimitadores de código.

    Returns:
        str: Código limpio sin delimitadores.
    """
    clean_text = re.sub(r'^```python\s*|\s*```$', '',
                        response_text, flags=re.MULTILINE)
    return clean_text.strip()


def process_text(text: str, accion: str, **kwargs) -> str:
    """
    Procesa el texto de entrada aplicando el prompt correspondiente y retorna la respuesta procesada

    Args:
        text (str): Texto de entrada obtenido del portapapeles.
        accion (str): Identificador de la acción a ejecutar.
        **kwargs: Argumentos adicionales para el template del prompt.

    Returns:
        str: Respuesta generada y procesada.
    """
    logging.info("Procesando texto con argumentos: %s", kwargs)
    prompt = PROMPTS[accion].substitute(text=text, **kwargs)
    logging.info("Prompt generado: %s", prompt)
    response = ollama.generate(
        model=TEXT_MODEL,
        prompt=prompt,
        **OLLAMA_CONFIG,
        options={'temperature': 0.1}
    )
    if 'error' in response:
        logging.error("Error en la respuesta: %s", response['error'])
        return None

    result = response.get('response', '')
    if 'python' in accion:
        return clean_code(result)
    return result


def execute(accion: str, **kwargs) -> None:
    """
    Ejecuta la acción copiando el contenido del portapapeles, procesándolo y pegándolo nuevamente.

    Args:
        accion (str): Identificador de la acción a ejecutar.
        **kwargs: Argumentos adicionales para el procesamiento del texto.
    """
    with controller.pressed(Key.ctrl):
        controller.tap("c")
    time.sleep(0.1)
    text = pyperclip.paste()
    if not text:
        logging.warning("No se encontró texto en el portapapeles.")
        return
    logging.info("Ejecutando acción '%s' con texto: %s", accion, text)
    processed_text = process_text(text, accion, **kwargs)
    if not processed_text:
        return
    pyperclip.copy(processed_text)
    time.sleep(0.1)
    with controller.pressed(Key.ctrl):
        controller.tap("v")


def get_image_from_clipboard() -> str:
    """
    Obtiene una imagen del portapapeles y la retorna codificada en base64.

    Returns:
        str: Imagen en base64 o None si no se encontró imagen.
    """
    try:
        image = ImageGrab.grabclipboard()
    except OSError as e:
        logging.error("Ocurrió un error al acceder al portapapeles: %s", e)
        return None

    if image is None:
        logging.warning("No se encontró imagen en el portapapeles.")
        return None

    try:
        buffer = io.BytesIO()
        image.save(buffer, format="PNG")
    except (ValueError, OSError) as e:
        logging.error("Error al guardar la imagen: %s", e)
        return None
    return base64.b64encode(buffer.getvalue()).decode("utf-8")


def process_image(action: str) -> None:
    """
    Procesa una imagen usando el modelo de visión y pega el resultado en el portapapeles.

    Args:
        action (str): Identificador de la acción de visión a ejecutar.
    """
    image_base64 = get_image_from_clipboard()
    if image_base64 is None:
        logging.warning("No se pudo obtener la imagen.")
        return
    prompt = PROMPTS[action].substitute()
    logging.info("Prompt enviado para imagen: %s", prompt)
    response = ollama.generate(
        model=VISION_MODEL,
        prompt=prompt,
        images=[image_base64],
        **OLLAMA_CONFIG
    )
    logging.info(response)
    if 'error' in response:
        logging.error("Error en el procesamiento de imagen: %s",
                      response['error'])
        return
    result = response.get('response', '')
    pyperclip.copy(result)
    with controller.pressed(Key.ctrl):
        controller.tap("v")


def initialize_actions() -> dict:
    """
    Inicializa y retorna un diccionario de acciones basadas en los atajos de teclado definidos en la configuración.

    Returns:
        dict: Mapeo de atajos de teclado a identificadores de acción.
    """
    return {KeyCode.from_char(config['prompts'][k]['shortcut']): k for k in config['prompts']}


def on_press(key) -> None:
    """
    Manejador de eventos para la pulsación de teclas.

    Args:
        key: Tecla presionada.
    """
    if key in ACTIONS and Key.ctrl in current_keys:
        action = ACTIONS[key]
        logging.info("Acción detectada: %s", action)
        prompt_type = config['prompts'][action].get('type')
        if prompt_type == 'vision':
            process_image(action)
        elif action == 'traducir_texto':
            execute(action, idioma="inglés")
        elif action == 'cambiar_tono':
            execute(action, tono="informal")
        else:
            execute(action)


def on_release(key) -> None:
    """
    Manejador de eventos para la liberación de teclas.

    Args:
        key: Tecla liberada.
    """
    current_keys.discard(key)


def on_press_mod(key) -> None:
    """
    Actualiza el conjunto de teclas presionadas y llama al manejador de pulsaciones.

    Args:
        key: Tecla presionada.
    """
    current_keys.add(key)
    on_press(key)


def start_listener() -> None:
    """
    Inicia el escuchador de teclas y mantiene el programa en ejecución.
    """
    with keyboard.Listener(on_press=on_press_mod, on_release=on_release) as listener:
        listener.join()


ACTIONS = initialize_actions()
current_keys = set()


def main() -> None:
    """Función principal que inicia la aplicación."""
    logging.info("Iniciando el programa...")
    start_listener()


if __name__ == "__main__":
    main()
