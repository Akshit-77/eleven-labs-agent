import speech_recognition as sr
import os
import google.generativeai as genai
import os
# from elevenlabs import generate, set_api_key
import sounddevice as sd
import scipy.io.wavfile as wav
import numpy as np
from dotenv import load_dotenv
from elevenlabs.client import ElevenLabs
from elevenlabs import play


load_dotenv()


def speech_to_text():
    """Converts speech from the microphone to text and prints it."""
    r = sr.Recognizer()
    with sr.Microphone() as source:
        print("Speak now...")
        r.adjust_for_ambient_noise(source)  # Optional: Adjust for background noise
        audio = r.listen(source, timeout=10)  # Set a timeout

    try:
        text = r.recognize_google(audio)  # Online recognition
        print("You said: " + text)  # Print the recognized text immediately
        return text
    except sr.UnknownValueError:
        print("Could not understand audio")
        return None
    except sr.RequestError as e:
        print(f"Could not request results from Google Speech Recognition service; {e}")
        return None
    except sr.WaitTimeoutError:
        print("Timeout: No speech detected.")
        return None
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return None


def generate_gemini_response(text, model="gemini-2.0-flash-lite-preview-02-05"):  # Default to gemini-pro
    """
    Generates a response from Gemini based on the given text.

    Args:
        text: The input text to Gemini.
        model: The name of the Gemini model to use (e.g., "gemini-pro").

    Returns:
        The generated response text, or None if an error occurs.
    """
    try:
        # Set your Gemini API key.  Best practice: store in environment variables.
        genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))  # Use your actual API Key

        # Construct the prompt (you might need to adjust this depending on the model)
        prompt = f"Here is the text I want you to respond to in one line only:\n\n{text}"
        model = genai.GenerativeModel("gemini-2.0-flash")
        # Generate the response
        response = model.generate_content(prompt)

        generated_text = response.text  # Access the generated text
        return generated_text

    except Exception as e:
        print(f"Error generating Gemini response: {e}")
        return None



def text_to_speech(text, model="eleven_multilingual_v2"):
    """
    Converts text to speech using ElevenLabs conversational AI models and plays the audio.

    Args:
        text: The text to convert to speech.
        voice: The name of the voice to use (e.g., "eleven_monolingual_v1").
        model: The name of the model to use (e.g., "eleven_multilingual_v1").
    """
    client = ElevenLabs(api_key=os.getenv("ELEVENLABS_API_KEY"))
    try:
        audio = client.text_to_speech.convert(
        text=text,
        voice_id="JBFqnCBsd6RMkjVDRZzb",
        model_id="eleven_multilingual_v2",
        output_format="mp3_44100_128",)
        play(audio)# Wait until audio playback is finished

    except Exception as e:
        print(f"Error generating or playing speech: {e}")
        



if __name__ == "__main__":
    while True:
        transcribed_text = speech_to_text()
        
        if transcribed_text and transcribed_text.lower().strip() == "see you later":
            print("Goodbye!")
            text_to_speech("Goodbye!, you can ping me anytime if you have any questions")
            break
            
        gemini_response = generate_gemini_response(transcribed_text)
        
        if transcribed_text:
            print("You said:", transcribed_text)
        if gemini_response:
            print("Gemini response:", gemini_response)
            text_to_speech(gemini_response)