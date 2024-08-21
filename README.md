# ClipAssistant
Asistente liaviano que vive en la consola y se comunica con el portapapeles. Utiliza Ollama. 
---

## Instalación de Ollama

**ClipAssistant** utiliza la API de Ollama para procesamiento de texto e imágenes. A continuación, te explicamos cómo instalar y configurar Ollama:

1. Visita [el sitio web de Ollama](https://ollama.com).
2. Sigue las instrucciones para instalar en tu computador.
Esta sección te ayudará a instalar y configurar Ollama para que puedas usar **ClipAssistant** de manera efectiva. Si tienes más preguntas sobre la instalación o configuración, no dudes en consultarlas.


## Características

- **Procesamiento de Texto**: Utiliza modelos de IA para limpiar, traducir, o ajustar el tono del texto copiado al portapapeles.
- **Procesamiento de Imágenes**: Extrae imágenes del portapapeles, las convierte a formato base64 y las procesa con modelos de visión por computadora.
- **Atajos de Teclado Personalizables**: Configura combinaciones de teclas para ejecutar diferentes acciones de manera rápida.
- **Integración con Modelos de IA**: Utiliza la API de Ollama para generar respuestas basadas en el texto y las imágenes.

## Requisitos

- Python 3.6 o superior
- Configuración de la API de Ollama

## Explicación en Youtube
[![YT](https://img.youtube.com/vi/GwYn5_h9_do/0.jpg)](https://youtu.be/GwYn5_h9_do?feature=shared)


## Instalación

1. Clona este repositorio:
    ```bash
    git clone https://github.com/crizconzeta/clipassistant.git
    ```

2. Navega al directorio del proyecto:
    ```bash
    cd clipassistant
    ```

3. Crea un venv
    ```bash
    cd  python -m venv env  
    ```

4. Activa el venv
    ```bash
    source env/bin/activate
    ```

5. Instala las dependencias necesarias:
    ```bash
    pip install -r requirements.txt
    ```

6. Modifica un archivo de configuración `config.yaml` siguiendo el ejemplo proporcionado en el repositorio.

Asegúrate de reemplazar los valores de `text_model` y `vision_model` con los modelos específicos que tengas instalados en tu computador.

Puedes utilizar cualquier modelo que tu computador sea capaz de correr. 

**Texto**

Gamma2:2b o Qwen2:1.5b para texto, si vas a realizar tareas simples, y toleras que tu asistente sea un poco vago y no responda de forma perfecta el 100% de las veces. 
Gemma2:9b o Llam13.1:8b si tienes un computador con suficiente VRAM y quieres realizar tareas más complejas. 

**Imagenes (vision)**

llava-llama3:latest puede responder en Español. 
Moondream funciona muy bien, pero siempre responde en inglés. 

-------
Esta documentación fue escrita con ClipAssistant 
