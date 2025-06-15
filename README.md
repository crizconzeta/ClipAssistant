# ClipAssistant

## Un asistente liviano que vive en tu consola y te ayuda con el texto del portapapeles usando IA local

[![Demostración en Youtube](https://img.youtube.com/vi/GwYn5_h9_do/0.jpg)](https://youtu.be/GwYn5_h9_do?feature=shared)

---

## Why?

Vivimos en un mundo de constante comunicación escrita. Para algunos, esto presenta desafíos únicos: dificultades para recordar palabras, errores frecuentes al teclear debido a la coordinación ojo-mano, o simplemente una carga cognitiva alta al tener que corregir y refinar textos constantemente. Además, existe una creciente preocupación por la privacidad y la dependencia de servicios en la nube que procesan nuestros datos.

**ClipAssistant nace de la necesidad de una herramienta:**

- **Local y Privada:** Que no envíe tus textos sensibles a servidores de terceros. Todo el procesamiento de IA se realiza en tu propia máquina usando Ollama.
- **Liviana y Rápida:** Que se ejecute en segundo plano sin consumir excesivos recursos y responda rápidamente.
- **Simple y Efectiva:** Que se enfoque en tareas comunes de manipulación de texto para reducir la carga cognitiva y agilizar el flujo de trabajo.

## How?

Aprovechando conocimientos de programación en Python y la flexibilidad de los modelos de lenguaje grandes (LLMs) locales, ClipAssistant:

1. **Escucha atajos de teclado** globales definidos por el usuario.
2. **Interactúa con el portapapeles** del sistema para copiar el texto seleccionado.
3. **Se comunica con un servicio local de Ollama** para enviar el texto a un modelo de IA (previamente descargado) junto con instrucciones específicas (prompts).
4. **Recibe la respuesta** procesada del modelo.
5. **Reemplaza el contenido del portapapeles** y automáticamente pega el texto resultante.

## What?

**ClipAssistant** es el resultado: una utilidad de línea de comandos (que se ejecuta en segundo plano) que te permite aplicar transformaciones de IA a cualquier texto que puedas copiar al portapapeles, simplemente usando un atajo de teclado.

---

## Características Principales

- **Procesamiento de Texto Local:** Corrige, mejora, traduce, resume o cambia el tono del texto usando modelos de IA que se ejecutan en tu máquina vía Ollama.
- **Activación por Atajos de Teclado:** Define combinaciones de teclas (ej. `Ctrl + 1`, `Ctrl + 2`) para invocar diferentes acciones sobre el texto seleccionado.
- **Configuración Flexible:** Personaliza los modelos de IA, los prompts y los atajos a través de un archivo `config.yaml` simple.
- **Enfoque en la Privacidad:** Tus datos del portapapeles nunca abandonan tu computadora durante el procesamiento de IA.
- **Liviano:** Diseñado para tener un bajo impacto en los recursos del sistema.
- _(Funcionalidad de Imágenes Deshabilitada Temporalmente): La capacidad de describir imágenes fue pausada debido a desafíos de compatibilidad multiplataforma con el portapapeles._

## Requisitos

- **Python:** Versión 3.12 o superior recomendada.
- **Ollama:** El servicio Ollama debe estar [instalado](https://ollama.com) y ejecutándose en tu máquina.
- **Modelos de Ollama:** Debes haber descargado los modelos de IA que desees usar (ej. `ollama pull llama3.2:3b`).
- **Dependencias de Python:** Las listadas en `requirements.txt` (se instalan con `pip`).
- **Sistema Operativo:** Probado principalmente en **Linux**. Debería funcionar en **macOS** y **Windows** para las funciones de texto, pero puede requerir ajustes o tener comportamientos inesperados con los atajos de teclado o el portapapeles en esos sistemas. La eliminación de la función de imágenes mejora la probabilidad de compatibilidad.

## Instalación

1. **Clona el Repositorio:**

   ```bash
   git clone https://github.com/crizconzeta/clipassistant.git
   cd clipassistant
   ```

2. **Instala Ollama:** Si aún no lo tienes, visita [ollama.com](https://ollama.com) y sigue las instrucciones para tu sistema operativo.

3. **Descarga un Modelo de IA (Ejemplo):**
   Abre tu terminal y ejecuta (elige un modelo adecuado para tu hardware):

   ```bash
   ollama pull llama3.2:3b
   ```

   _Asegúrate de que Ollama esté corriendo._

4. **Crea y Activa un Entorno Virtual (Recomendado):**

   ```bash
   python -m venv env
   source env/bin/activate  # En Linux/macOS
   # o `.\env\Scripts\activate` en Windows (cmd/powershell)
   ```

5. **Instala las Dependencias de Python:**

   ```bash
   pip install -r requirements.txt
   ```

## Configuración (`config.yaml`)

Antes de ejecutar, necesitas configurar `ClipAssistant`:

1. **Crea un archivo `config.yaml`** en el directorio raíz del proyecto. Puedes utilizar el archivo que viene por defecto.

2. **Modifica `text_model`** para que coincida con el modelo que descargaste con Ollama.

3. **Personaliza los `prompts`**:
   - Añade, elimina o modifica acciones.
   - Cambia los `shortcut` (la tecla que usarás con `Ctrl`).
   - Ajusta las plantillas (`template`) para darle las instrucciones precisas al LLM. La variable `$text` será reemplazada por el contenido de tu portapapeles.

## Uso

1. **Asegúrate de que Ollama esté corriendo** en segundo plano.
2. **Navega a la carpeta** donde clonaste `ClipAssistant` en tu terminal.
3. **Activa tu entorno virtual** (ej. `source env/bin/activate`).
4. **Ejecuta el script:**

   ```bash
   python main.py
   ```

   Verás un mensaje indicando que está escuchando atajos. La terminal permanecerá ocupada por el script.

5. **¡Úsalo!**

   - Selecciona cualquier texto en cualquier aplicación (navegador, editor, etc.).
   - Presiona la combinación de teclas `Ctrl + [shortcut]` que definiste en `config.yaml` (ej. `Ctrl + 1` para arreglar texto, `Ctrl + 2` para mejorarlo, según el ejemplo anterior).
   - Espera un momento mientras ClipAssistant contacta a Ollama.
   - El texto seleccionado será reemplazado automáticamente por la respuesta procesada por el LLM.

6. **Para detener ClipAssistant:** Vuelve a la terminal donde se está ejecutando y presiona `Ctrl + C`.

## Contribuciones

Las contribuciones son bienvenidas. Por favor, abre un _issue_ para discutir cambios importantes antes de crear un _pull request_.

---

_Esta documentación fue parcialmente escrita y refinada con la ayuda de ClipAssistant._

