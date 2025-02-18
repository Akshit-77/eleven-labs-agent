from flask import Flask, render_template_string, request, redirect, url_for
from app_backup import speech_to_text, generate_gemini_response, text_to_speech
import time
app = Flask(__name__)

# HTML template for the voice assistant page.
template = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI Voice Assistant</title>
    <link href="https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;500;600&display=swap" rel="stylesheet">
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
            font-family: 'Poppins', sans-serif;
        }

        body {
            min-height: 100vh;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 20px;
            color: white;
        }

        .container {
            max-width: 800px;
            margin: 0 auto;
            padding: 2rem;
            text-align: center;
        }

        .glass-container {
            background: rgba(255, 255, 255, 0.1);
            backdrop-filter: blur(10px);
            border-radius: 20px;
            padding: 2rem;
            box-shadow: 0 8px 32px 0 rgba(31, 38, 135, 0.37);
            border: 1px solid rgba(255, 255, 255, 0.18);
            margin-top: 2rem;
        }

        h1 {
            font-size: 2.5rem;
            margin-bottom: 1rem;
            background: linear-gradient(to right, #fff, #e2e2e2);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }

        .assistant-image {
            width: 150px;
            height: 150px;
            margin: 1rem auto;
            border-radius: 50%;
            box-shadow: 0 4px 15px rgba(0,0,0,0.2);
        }

        .speak-btn {
            background: linear-gradient(45deg, #FF416C 0%, #FF4B2B 100%);
            border: none;
            color: white;
            width: 120px;
            height: 120px;
            border-radius: 50%;
            font-size: 1.1rem;
            font-weight: 500;
            cursor: pointer;
            transition: all 0.3s ease;
            box-shadow: 0 4px 15px rgba(0,0,0,0.2);
            margin: 2rem 0;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            position: relative;
            overflow: hidden;
        }

        .speak-btn:hover {
            transform: scale(1.05);
            box-shadow: 0 6px 20px rgba(0,0,0,0.3);
        }

        .speak-btn:active {
            transform: scale(0.95);
        }

        .response-container {
            background: rgba(255, 255, 255, 0.05);
            border-radius: 15px;
            padding: 1.5rem;
            margin-top: 1.5rem;
            text-align: left;
        }

        h2 {
            font-size: 1.5rem;
            margin-bottom: 0.5rem;
            color: #f0f0f0;
        }

        p {
            line-height: 1.6;
            margin-bottom: 1rem;
            color: #e0e0e0;
        }

        .pulse {
            animation: pulse 2s infinite;
        }

        @keyframes pulse {
            0% {
                box-shadow: 0 0 0 0 rgba(255, 65, 108, 0.4);
            }
            70% {
                box-shadow: 0 0 0 20px rgba(255, 65, 108, 0);
            }
            100% {
                box-shadow: 0 0 0 0 rgba(255, 65, 108, 0);
            }
        }

        .wave {
            position: fixed;
            bottom: 0;
            left: 0;
            width: 100%;
            height: 100px;
            background: url('https://assets.codepen.io/85648/wave.svg');
            background-size: 1000px 100px;
            opacity: 0.2;
        }

        .wave.wave1 {
            animation: animate 30s linear infinite;
            z-index: 1000;
            opacity: 0.2;
            animation-delay: 0s;
            bottom: 0;
        }

        .wave.wave2 {
            animation: animate2 15s linear infinite;
            z-index: 999;
            opacity: 0.1;
            animation-delay: -5s;
            bottom: 10px;
        }

        @keyframes animate {
            0% { background-position-x: 0; }
            100% { background-position-x: 1000px; }
        }

        @keyframes animate2 {
            0% { background-position-x: 0; }
            100% { background-position-x: -1000px; }
        }
    </style>
</head>
<body>
    <div class="container">
        <img src="https://cdn-icons-png.flaticon.com/512/4712/4712027.png" alt="AI Assistant" class="assistant-image">
        <h1>AI Voice Assistant</h1>
        
        <div class="glass-container">
            <p>Click the button and start speaking. I'm here to help!</p>
            <form action="{{ url_for('listen') }}" method="post">
                <button type="submit" class="speak-btn pulse">
                    Speak Now
                </button>
            </form>

            {% if transcript %}
            <div class="response-container">
                <h2>You said:</h2>
                <p>{{ transcript }}</p>
            </div>
            {% endif %}

            {% if response_text %}
            <div class="response-container">
                <h2>Response:</h2>
                <p>{{ response_text }}</p>
            </div>
            {% endif %}
        </div>
    </div>

    <div class="wave wave1"></div>
    <div class="wave wave2"></div>
</body>
</html>
'''

@app.route('/', methods=['GET'])
def index():
    """Renders the homepage with a button to start the voice dialogue."""
    return render_template_string(template)

@app.route('/listen', methods=['POST'])
def listen():
    """
    Continuously process the voice input until valid speech is captured:
    1. Repeatedly listen using speech_to_text.
    2. If no speech is detected, prompt again via text_to_speech.
    3. If the user says "see you later", provide a farewell.
    4. Otherwise, generate a Gemini response and speak it.
    """
    transcript = None

    # Loop until a valid transcript is obtained.
    while transcript is None:
        transcript = speech_to_text()
        
        if transcript is None:
            # Prompt user again if nothing was detected.
            prompt = "I did not catch that. Could you please speak again?"
            text_to_speech(prompt)

    # Process the valid transcript.
    if transcript.lower().strip() == "see you later":
        response_text = "Goodbye! You can ping me anytime if you have any questions."
        text_to_speech(response_text)
    else:
        response_text = generate_gemini_response(transcript)
        if response_text is None:
            response_text = "Sorry, I couldn't generate a response."
        time.sleep(1)
        text_to_speech(response_text)
        render_template_string(template, transcript=transcript, response_text=response_text)
        text_to_speech("Do you have any other questions?")
        listen()
        
    return render_template_string(template, transcript=transcript, response_text=response_text)

if __name__ == '__main__':
    # Run the server in debug mode to catch errors.
    app.run(debug=True) 