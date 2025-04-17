import os
import base64
import time
# Replace direct dotenv import with our environment manager
from env_manager import load_environment_variables
import requests
from typing import Dict, List, Union, Optional

import openai
import anthropic  # Add import for Anthropic

# Get the logger
from log_manager import get_logger
logger = get_logger("CoachAI_LLM_helpers")

# Create cache for memoization
import diskcache  # Import the module directly
cache = diskcache.Cache("llm_cache_folder")  # Use the module directly

# OPENAI API configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_API_BASE_URL = os.getenv("OPENAI_API_BASE_URL", "https://api.openai.com/v1/")

# Anthropic API configuration
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
ANTHROPIC_MODEL_ID = os.getenv("ANTHROPIC_MODEL_ID", "claude-3-5sonnet--20241022")  # "claude-3-haiku-20240229"  # "claude-3-haiku-20240229"

# DeepSeek API configuration
DS_API_KEY = os.getenv("DS_API_KEY")
DS_API_BASE_URL = os.getenv("DS_API_BASE_URL", "https://api.deepseek.com/v1")

# local LM Studio API configuration
LM_API_KEY = os.getenv("LM_API_KEY", "LM_STUDIO_NO_API_KEY")
LM3_API_BASE_URL = os.getenv("LM3_API_BASE_URL", "http://192.168.0.183:1234/v1")
LM4_API_BASE_URL = os.getenv("LM4_API_BASE_URL", "http://mbpm4.local:1234/v1")
LM_MODEL_ID = os.getenv("LM_MODEL_ID", "deepseek-r1-distill-llama-8b")  # "deepseek-r1-distill-qwen-32b"
LM_API_BASE_URL = LM3_API_BASE_URL # Choose LM3_API_BASE_URL or LM4_API_BASE_URL

# local ollam API configuration
OLM_API_KEY = os.getenv("OLM_API_KEY", "LM_STUDIO_NO_API_KEY")
OLM_API_BASE_URL = os.getenv("OLM_API_BASE_URL", "http://192.168.0.183:11434/v1")
OLM_MODEL_ID = os.getenv("OLM_MODEL_ID", "llama3.2")

# Default Parameter to select which LLM to use:
# Defaults to "1" if no environment variable is set
# Possible values 1: OpenAI, 2: Anthropic, 3: DeepSeek API, 4: local LM Studio, 5: local Ollama
LLM_CHOICE = int(os.getenv("LLM_CHOICE", "1"))

def memoize(func):
    """Memoize decorator to cache function results"""
    def wrapper(*args, **kwargs):
        key = (args, tuple(sorted(kwargs.items())))
        logger.info(f"Memoize: Caching result for {func.__name__}")
        if key in cache:
            return cache[key]
        result = func(*args, **kwargs)
        cache[key] = result
        return result
    return wrapper

def clear_llm_cache():
    """Clear the entire memoization cache for LLM queries"""
    try:
        cache_size_before = len(cache)
        cache.clear()
        logger.info(f"Cache cleared: removed {cache_size_before} cached items")
        return f"Cache cleared: removed {cache_size_before} cached items"
    except Exception as e:
        logger.error(f"Error clearing cache: {e}")
        return f"Error clearing cache: {e}"

@memoize
def send_query_to_llm(system_message, query, llm_choice = None):
    """Send a query to the selected LLM and return the response"""
    max_attempts = 3
    attempt = 0
    reply = None

    OPENAI_MODEL_ID = os.getenv("OPENAI_MODEL_ID", "chatgpt-4o-latest")  # o1-mini gpt-4o chatgpt-4o-latest gpt-4-turbo
    ANTHROPIC_MODEL_ID = os.getenv("ANTHROPIC_MODEL_ID", "claude-3-5sonnet--20241022")  # "claude-3-haiku-20240229"  # "claude-3-haiku-20240229"
    DS_MODEL_ID = os.getenv("DS_MODEL_ID", "deepseek-reasoner")

    while attempt < max_attempts:
        try:
            if not llm_choice:
                llm_choice = LLM_CHOICE

            if llm_choice == 1:
                client_openai = openai.OpenAI(api_key=OPENAI_API_KEY, base_url=OPENAI_API_BASE_URL)
                model_id = OPENAI_MODEL_ID
                use_anthropic = False
            elif llm_choice == 2:
                # Anthropic API setup
                client_anthropic = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
                model_id = ANTHROPIC_MODEL_ID
                use_anthropic = True
            elif llm_choice == 3:
                client_openai = openai.OpenAI(api_key=DS_API_KEY, base_url=DS_API_BASE_URL)
                model_id = DS_MODEL_ID
                use_anthropic = False
            elif llm_choice == 4:
                client_openai = openai.OpenAI(api_key=LM_API_KEY, base_url=LM_API_BASE_URL)
                model_id = LM_MODEL_ID
                use_anthropic = False
            elif llm_choice == 5:
                client_openai = openai.OpenAI(api_key=OLM_API_KEY, base_url=OLM_API_BASE_URL)
                model_id = OLM_MODEL_ID
                use_anthropic = False
            else:
                raise ValueError(f"Invalid LLM choice: {llm_choice}")

            logger.info(f"LLM details : model {model_id}")
            if not use_anthropic:
                logger.info(f"API base URL: {client_openai.base_url}")

            logger.info(f"LLM query : {system_message + ' ' + query}")

            start_time = time.time()

            if use_anthropic:
                # Handle Anthropic API
                response = client_anthropic.messages.create(
                    model=model_id,
                    system=system_message,
                    messages=[
                        {"role": "user", "content": system_message + " " + query}
                    ],
                    max_tokens=200000
                )
                reply = response.content[0].text
            elif model_id == "o1-mini":
                # o1-mini model does not support role system or max_tokens
                logger.warning(f"No support for role system or max_tokens in model {model_id}.")
                response = client_openai.chat.completions.create(
                    model=model_id,
                    messages=[
                        {"role": "user", "content": system_message + " " + query},
                    ],
                    max_completion_tokens=1000,
                )
                if response and response.choices:
                    reply = (getattr(response.choices[0].message, "content", "") or "").strip()
            else:
                response = client_openai.chat.completions.create(
                    model=model_id,
                    messages=[
                        {"role": "system", "content": system_message},
                        {"role": "user", "content": query},
                    ],
                    max_tokens=16384,
                )
                if response and response.choices:
                    reply = (getattr(response.choices[0].message, "content", "") or "").strip()

            end_time = time.time()
            if use_anthropic:
                logger.info(f"Anthropic {model_id} response in {end_time - start_time:.2f} sec")
            else:
                logger.info(f"LLM {model_id} at {client_openai.base_url} response in {end_time - start_time:.2f} sec : {response}")

            if reply:
                print(f"Received response in {end_time - start_time:.2f} sec ")
                break  # Exit loop if a non-empty reply is obtained
            else:
                attempt += 1
                logger.warning(f"Empty reply received. Retrying... (attempt {attempt}/{max_attempts})")
                time.sleep(1)  # wait for 1 second before retrying

        except (openai.OpenAIError, anthropic.APIError) as e:
            logger.error(f"An error occurred with model {model_id}: {e} for query : {query}")
            attempt += 1
            time.sleep(1)

    if not reply:
        logger.warning("No content received after retries.")
    return reply

def send_query_to_llm_assistant(system_message, query, timeout=120, initial_backoff=1, max_backoff=8):
    """
    Send a query to the OpenAI Assistant API with improved polling mechanism.

    Args:
        system_message: Context or system instructions
        query: The user's query
        timeout: Maximum time to wait for response in seconds (default: 120)
        initial_backoff: Starting backoff time in seconds (default: 1)
        max_backoff: Maximum backoff time in seconds (default: 8)

    Returns:
        Assistant's response text or None if failed
    """
    # Your existing assistant ID
    assistant_id = "asst_wVAbvVr13ugq6taXj7jfquAX"

    # Step 1: Create a new thread
    thread = openai.beta.threads.create()
    logger.info(f"Thread ID: {thread.id}")

    # Step 2: Send a message to the thread
    user_message = "Your context: " + system_message + "  My query : " + query

    # Set your OpenAI API key
    openai.api_key = OPENAI_API_KEY  # Replace with your key

    try:
        # Create message in thread
        openai.beta.threads.messages.create(
            thread_id=thread.id,
            role="user",
            content=user_message
        )
        logger.info(f"User: {user_message}")

        # Step 3: Run the assistant
        run = openai.beta.threads.runs.create(
            thread_id=thread.id,
            assistant_id=assistant_id
        )

        # Step 4: Wait for the run to complete with exponential backoff
        logger.info("Waiting for assistant to respond...")
        start_time = time.time()
        current_backoff = initial_backoff

        while True:
            # Check if we've exceeded timeout
            if time.time() - start_time > timeout:
                logger.error(f"Assistant API timeout after {timeout} seconds")
                return None

            # Get current run status
            run_status = openai.beta.threads.runs.retrieve(
                thread_id=thread.id,
                run_id=run.id
            )

            if run_status.status == "completed":
                logger.info(f"Assistant run completed in {time.time() - start_time:.2f} seconds")
                break
            elif run_status.status == "requires_action":
                # Handle tool calls if needed in the future
                logger.error("Run requires action, but tool handling not implemented")
                return None
            elif run_status.status in ["failed", "cancelled", "expired"]:
                error_details = getattr(run_status, "last_error", "No error details available")
                logger.error(f"Run failed. Error details: {error_details}")
                logger.error(f"Run ended with status: {run_status.status}")
                return None

            # Sleep with exponential backoff
            logger.debug(f"Waiting {current_backoff}s for assistant response...")
            time.sleep(current_backoff)
            current_backoff = min(current_backoff * 2, max_backoff)

        # Step 5: Retrieve and log the assistant's response
        messages = openai.beta.threads.messages.list(thread_id=thread.id)

        # Show the latest assistant reply
        for msg in messages.data[::-1]:  # Reverse to get latest first
            if msg.role == "assistant":
                logger.info(f"\nAssistant response received")
                return msg.content[0].text.value

        logger.warning("No assistant response found.")
        return None

    except openai.OpenAIError as e:
        logger.error(f"OpenAI API error: {str(e)}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error in send_query_to_llm_assistant: {str(e)}", exc_info=True)
        return None