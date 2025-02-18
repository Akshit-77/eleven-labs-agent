from flask import Flask, request, send_file
from twilio.twiml.voice_response import VoiceResponse, Gather
from twilio.rest import Client
import os
from dotenv import load_dotenv
import speech_recognition as sr
import sounddevice as sd
import scipy.io.wavfile as wav
import numpy as np
from elevenlabs.client import ElevenLabs
from elevenlabs import play
import google.generativeai as genai
from app_backup import generate_gemini_response
from pyngrok import ngrok, conf
import time

# Load environment variables
load_dotenv()

app = Flask(__name__)

# Extract Twilio credentials from environment variables
TWILIO_ACCOUNT_SID = os.getenv('TWILIO_ACCOUNT_SID')
TWILIO_AUTH_TOKEN = os.getenv('TWILIO_AUTH_TOKEN')
TWILIO_PHONE_NUMBER = os.getenv('TWILIO_PHONE_NUMBER')
TARGET_PHONE_NUMBER = os.getenv('TARGET_PHONE_NUMBER')

# Initialize Twilio client
client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

def get_ngrok_url():
    """Get the public URL from ngrok"""
    tunnels = ngrok.get_tunnels()
    return tunnels[0].public_url if tunnels else None

def text_to_speech(text, model="eleven_multilingual_v2"):
    """
    Converts text to speech using ElevenLabs and returns the audio data
    """
    client = ElevenLabs(api_key=os.getenv("ELEVENLABS_API_KEY"))
    try:
        audio = client.text_to_speech.convert(
            text=text,
            voice_id="JBFqnCBsd6RMkjVDRZzb",
            model_id="eleven_multilingual_v2",
            output_format="mp3_44100_128"
        )
        # Convert generator to bytes
        audio_bytes = b''.join(chunk for chunk in audio)
        
        # Save the audio to a temporary file that Twilio can access
        temp_filename = f"temp_audio_{os.urandom(4).hex()}.mp3"
        with open(temp_filename, 'wb') as f:
            f.write(audio_bytes)
        return temp_filename
    except Exception as e:
        print(f"Error generating speech: {e}")
        return None

@app.route("/answer", methods=['POST'])
def answer_call():
    """Handle the incoming call and gather speech input"""
    response = VoiceResponse()
    
    # Create a Gather verb to collect speech input
    gather = Gather(
        input='speech',
        action='/process_speech',
        method='POST',
        language='en-US',
        speechTimeout='auto'
    )
    
    # Add prompt to the Gather verb
    gather.say("Hello! I'm your AI assistant. How can I help you today?", voice='alice')
    
    # Add the Gather verb to the response
    response.append(gather)
    
    return str(response)

@app.route("/process_speech", methods=['POST'])
def process_speech():
    """Process the speech input and generate AI response"""
    # Get the speech input from Twilio
    user_speech = request.values.get('SpeechResult')
    print(f"Received speech: {user_speech}")  # Debug print
    
    response = VoiceResponse()
    
    # Check if user wants to end the conversation
    if user_speech and "see you later" in user_speech.lower():
        response.say("Thanks for chatting! Have a great day!", voice='alice')
        return str(response)
    
    if user_speech:
        try:
            # Generate AI response using Gemini
            ai_response = generate_gemini_response(user_speech)
            print(f"AI Response: {ai_response}")  # Debug print
            
            if ai_response:
                # Convert AI response to speech
                audio_file = text_to_speech(ai_response)
                
                if audio_file:
                    # Get the ngrok URL
                    ngrok_url = get_ngrok_url()
                    if ngrok_url:
                        # Play the generated audio file using the public URL
                        audio_url = f"{ngrok_url}/audio/{os.path.basename(audio_file)}"
                        response.play(audio_url)
                        # Clean up the temporary file after a delay
                        import threading
                        threading.Timer(3.0, lambda: os.remove(audio_file) if os.path.exists(audio_file) else None).start()
                        
                        # Add a pause for better conversation flow
                        response.pause(length=1)
                        
                        # Ask if they need anything else
                        response.say("May I help you with something else? Say 'see you later' when you're done.", voice='alice')
                    else:
                        response.say("Sorry, there was an error with the audio playback.", voice='alice')
                else:
                    response.say("Sorry, I couldn't convert my response to speech.", voice='alice')
            else:
                response.say("I couldn't generate a response. Please try again.", voice='alice')
            
            # Create a new Gather for continued conversation
            gather = Gather(
                input='speech',
                action='/process_speech',
                method='POST',
                language='en-US',
                speechTimeout='auto'
            )
            response.append(gather)
            
        except Exception as e:
            print(f"Error processing speech: {e}")
            response.say("Sorry, there was an error processing your request.", voice='alice')
    else:
        response.say("I didn't catch that. Please try again.", voice='alice')
        # Redirect to gather more input
        response.redirect('/answer')
    
    return str(response)

@app.route("/audio/<filename>")
def serve_audio(filename):
    """Serve the temporary audio files"""
    try:
        return send_file(filename, mimetype='audio/mpeg')
    except Exception as e:
        print(f"Error serving audio file: {e}")
        return "Error serving audio file", 404

@app.route("/make_call", methods=['POST'])
def make_call():
    """Initiate a call to the target number"""
    try:
        # Get the ngrok URL
        ngrok_url = get_ngrok_url()
        if not ngrok_url:
            return {"error": "Ngrok tunnel not available"}, 400
            
        # Make the call using the ngrok URL
        call = client.calls.create(
            to=TARGET_PHONE_NUMBER,
            from_=TWILIO_PHONE_NUMBER,
            url=f"{ngrok_url}/answer",
            method='POST'
        )
        
        return {"message": "Call initiated", "call_sid": call.sid}, 200
    
    except Exception as e:
        print(f"Error making call: {e}")
        return {"error": str(e)}, 400

@app.route("/", methods=['GET'])
def index():
    """Modern interface to initiate calls"""
    ngrok_url = get_ngrok_url()
    return f'''
    <html>
    <head>
        <title>AI Voice Assistant</title>
        <style>
            @keyframes wave {{
                0% {{ transform: translateY(0); }}
                50% {{ transform: translateY(-15px); }}
                100% {{ transform: translateY(0); }}
            }}
            
            @keyframes gradient {{
                0% {{ background-position: 0% 50%; }}
                50% {{ background-position: 100% 50%; }}
                100% {{ background-position: 0% 50%; }}
            }}
            
            body {{
                font-family: 'Segoe UI', Arial, sans-serif;
                background: linear-gradient(-45deg, #FF6B6B, #4ECDC4, #45B7D1, #96E6B3);
                background-size: 400% 400%;
                animation: gradient 15s ease infinite;
                color: #ffffff;
                margin: 0;
                padding: 0;
                min-height: 100vh;
                display: flex;
                justify-content: center;
                align-items: center;
                position: relative;
                overflow: hidden;
            }}
            
            .wave {{
                position: fixed;
                bottom: 0;
                left: 0;
                width: 100%;
                height: 100px;
                background: url('data:image/svg+xml,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1440 320"><path fill="%234ECDC4" fill-opacity="0.3" d="M0,96L48,112C96,128,192,160,288,160C384,160,480,128,576,112C672,96,768,96,864,112C960,128,1056,160,1152,160C1248,160,1344,128,1392,112L1440,96L1440,320L1392,320C1344,320,1248,320,1152,320C1056,320,960,320,864,320C768,320,672,320,576,320C480,320,384,320,288,320C192,320,96,320,48,320L0,320Z"></path></svg>');
                background-size: 1440px 100px;
                animation: wave 10s linear infinite;
            }}
            
            .wave:nth-child(2) {{
                bottom: 10px;
                opacity: 0.5;
                animation: wave 7s linear infinite;
            }}
            
            .wave:nth-child(3) {{
                bottom: 20px;
                opacity: 0.2;
                animation: wave 5s linear infinite;
            }}
            
            .container {{
                background: rgba(255, 255, 255, 0.15);
                backdrop-filter: blur(10px);
                border-radius: 20px;
                padding: 3rem;
                box-shadow: 0 8px 32px 0 rgba(31, 38, 135, 0.37);
                width: 90%;
                max-width: 600px;
                text-align: center;
                position: relative;
                z-index: 1;
                border: 1px solid rgba(255, 255, 255, 0.18);
            }}
            
            h1 {{
                color: #ffffff;
                font-size: 2.8rem;
                margin-bottom: 1.5rem;
                text-shadow: 2px 2px 4px rgba(0, 0, 0, 0.2);
            }}
            
            .status {{
                background: rgba(255, 255, 255, 0.1);
                padding: 1.2rem;
                border-radius: 15px;
                margin-bottom: 2rem;
                font-size: 1rem;
                color: #ffffff;
                border: 1px solid rgba(255, 255, 255, 0.1);
            }}
            
            .button {{
                background: linear-gradient(45deg, #FF6B6B, #FF8E8E);
                color: white;
                border: none;
                padding: 1.2rem 2.5rem;
                border-radius: 30px;
                font-size: 1.2rem;
                cursor: pointer;
                transition: all 0.3s ease;
                box-shadow: 0 4px 15px rgba(255, 107, 107, 0.4);
                position: relative;
                overflow: hidden;
            }}
            
            .button:hover {{
                transform: translateY(-3px);
                box-shadow: 0 6px 20px rgba(255, 107, 107, 0.6);
            }}
            
            .button:active {{
                transform: translateY(1px);
            }}
            
            .icon {{
                font-size: 5rem;
                margin-bottom: 1.5rem;
                color: #ffffff;
                animation: wave 3s ease-in-out infinite;
            }}
            
            .status p {{
                margin: 0.5rem 0;
                display: flex;
                align-items: center;
                justify-content: center;
                gap: 10px;
            }}
            
            .status i {{
                font-size: 1.2rem;
            }}
            
            @keyframes wave {{
                0%, 100% {{
                    transform: translateY(0);
                }}
                50% {{
                    transform: translateY(-10px);
                }}
            }}
        </style>
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
    </head>
    <body>
        <div class="wave"></div>
        <div class="wave"></div>
        <div class="wave"></div>
        <div class="container">
            <div class="icon">
                <i class="fas fa-robot"></i>
            </div>
            <h1>AI Voice Assistant</h1>
            <div class="status">
                <p><i class="fas fa-link"></i> Server Status: Connected</p>
                <p><i class="fas fa-server"></i> Server URL: {ngrok_url}</p>
            </div>
            <form action="/make_call" method="POST">
                <button type="submit" class="button">
                    <i class="fas fa-phone-alt"></i> Start Call
                </button>
            </form>
        </div>
    </body>
    </html>
    '''

def kill_existing_tunnels():
    """Kill all existing ngrok tunnels and processes"""
    try:
        # Kill any existing ngrok processes
        if os.name == 'nt':  # Windows
            os.system('taskkill /f /im ngrok.exe')
        else:  # Linux/Mac
            os.system('pkill ngrok')
            
        # Wait for processes to be killed
        time.sleep(2)
        
        try:
            # Try to kill any remaining tunnels through the API
            tunnels = ngrok.get_tunnels()
            for tunnel in tunnels:
                print(f"Closing tunnel: {tunnel.public_url}")
                ngrok.disconnect(tunnel.public_url)
        except:
            pass  # If no tunnels exist, that's fine
            
        # Kill the ngrok process completely
        try:
            ngrok.kill()
        except:
            pass
            
        print("All existing tunnels and processes closed")
        time.sleep(5)  # Wait for everything to clean up
        
    except Exception as e:
        print(f"Error killing tunnels: {e}")

def start_ngrok():
    """Start ngrok tunnel after killing existing ones"""
    try:
        # Kill existing tunnels first
        kill_existing_tunnels()
        
        # Set up ngrok configuration
        ngrok.set_auth_token(os.getenv('NGROK_AUTH_TOKEN'))
        
        # Configure ngrok (optional settings)
        conf.get_default().region = 'us'  # or your preferred region
        
        # Start new tunnel
        public_url = ngrok.connect(5000, bind_tls=True)
        print(f' * Tunnel URL: {public_url}')
        
        # Verify the tunnel is working
        tunnels = ngrok.get_tunnels()
        if tunnels:
            print(f' * Active tunnels: {len(tunnels)}')
            for tunnel in tunnels:
                print(f' * {tunnel.public_url}')
        else:
            print(" * Warning: No active tunnels found after connection")
            
    except Exception as e:
        print(f"Error starting ngrok: {e}")
        raise  # Re-raise the exception to prevent the server from starting with no tunnel

if __name__ == "__main__":
    try:
        # Start ngrok when running the server
        start_ngrok()
        # Run the Flask app
        app.run(debug=True)
    except Exception as e:
        print(f"Failed to start server: {e}")
