import yaml
import time
import io
import base64
from string import Template
from pynput import keyboard
from pynput.keyboard import Key, KeyCode, Controller
import pyperclip
from PIL import ImageGrab
import re
import ollama


with open('config.yaml', 'r') as file:
    config = yaml.safe_load(file)

controller = Controller()

# Ollama RLZ!
TEXT_MODEL = config['ollama']['text_model']
VISION_MODEL = config['ollama']['vision_model']
OLLAMA_CONFIG = {
    "keep_alive": config['ollama']['keep_alive'],
    "stream": config['ollama']['stream'],
}

PROMPTS = {k: Template(v['template']) for k, v in config['prompts'].items()}


def clean_code(response_text):
    # Elimina etiquetas de código y cualquier texto no relacionado con el código
    clean_text = re.sub(r'^```python\s*|\s*```$', '', response_text, flags=re.MULTILINE)
    return clean_text.strip()

def process_text(text, accion, **kwargs):
    print(f"kwargs: {kwargs}") 
    prompt = PROMPTS[accion].substitute(text=text, **kwargs)
    print (prompt)
    response = ollama.generate(
        model=TEXT_MODEL,
        prompt=prompt,
        **OLLAMA_CONFIG
    )

    if 'error' in response:
        print("Error:", response['error'])
        return None
    
    if 'python' in accion:
        cleaned_response = clean_code(response['response'])
        return cleaned_response
    return response['response']

def execute(accion, **kwargs):
    with controller.pressed(Key.ctrl):
        controller.tap("c")
    time.sleep(0.1)
    text = pyperclip.paste()
    if not text:
        return
    print (text, accion)
    fixed_text = process_text(text, accion, **kwargs)
    if not fixed_text:
        return
    pyperclip.copy(fixed_text)
    time.sleep(0.1)
    print(text)
    print(fixed_text)
    with controller.pressed(Key.ctrl):
        controller.tap("v")

def get_image_from_clipboard():
    try:
        image = ImageGrab.grabclipboard()
    except:
        print("No image found in clipboard")
        return None
    if image is None:
        print("No image found in clipboard")
        return None
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return base64.b64encode(buffer.getvalue()).decode('utf-8')

def process_image(action):
    image_base64 = get_image_from_clipboard()
    if image_base64 is None:
        return "No pude obtener la imagen 🙃"

    prompt = PROMPTS[action].substitute()
    print(f'Prompt enviado: {prompt}')
    response = ollama.generate(
        model=VISION_MODEL,
        prompt=prompt,
        images=[image_base64],
        **OLLAMA_CONFIG
    )

    if 'error' in response:
        print("Error:", response['error'])
        return None
    result = response['response']

    print(result)
    pyperclip.copy(result)
    with controller.pressed(Key.ctrl):
        controller.tap("v")

"""
ACCIONES
"""
actions = {KeyCode.from_char(config['prompts'][k]['shortcut']): k for k in config['prompts']}
print(actions)

def on_press(key):
    if key in actions and Key.ctrl in current_keys:
        action = actions[key]
        print(action)
        if config['prompts'][action]['type'] == 'vision':
            process_image(action)
        elif action == 'traducir_texto':
            execute(action, idioma="español")
        elif action == 'cambiar_tono':
            execute(action, tono="informal")
        else:
            execute(action)

def on_release(key):
    try:
        current_keys.remove(key)
    except KeyError:
        pass

current_keys = set()

def on_press_mod(key):
    if key not in current_keys:
        current_keys.add(key)
    on_press(key)

def start_listener():
    with keyboard.Listener(on_press=on_press_mod, on_release=on_release) as listener:
        listener.join()

if __name__ == "__main__":
    print("Comencemos...")
    start_listener()
