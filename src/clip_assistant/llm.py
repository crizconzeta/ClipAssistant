import logging

import ollama

from .config import OllamaConfig


def call_ollama(
    prompt: str,
    config: OllamaConfig,
    images: list[str] | None = None,
) -> str | None:
    """Sends this poor soul's request into the digital void"""
    model = config.vision_model if images else config.text_model
    logging.info("Contacting the ollama... (Model: %s)", model)

    try:
        # The options are a pact with the machine
        # Let's hope it honors it
        response = ollama.generate(
            model=model,
            prompt=prompt,
            images=images or [],
            options={
                "keep_alive": config.keep_alive,
                "stream": config.stream,
                "temperature": 0.1,
                # I Love avant-garde movies, but llms responses has to be deterministic, not avant-garde
            },
        )
        result = response.get("response", "").strip()

        if not result:
            # Sometimes the API just sends back... nothin'. We'll just return None.
            logging.warning("Ollama returned an empty void. Deep")
            return None

        return result

    except ollama.ResponseError as e:
        logging.error("Ollama is having a moment. Status %s: %s", e.status_code, e.error)
        return None
    except Exception as e:
        # We've failed. It's not you, it's me. And this exception.
        logging.error("An existential error occurred while talking to Ollama: %s", e)
        return None
