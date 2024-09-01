import requests
import os
from dotenv import load_dotenv
from langdetect import detect
from flask import Flask, render_template, request, session, redirect, url_for, jsonify
from supabase import create_client, Client
from gotrue.errors import AuthApiError
from functools import wraps

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY')  # Necessary for using session

supabase_url = os.getenv('SUPABASE_URL')
supabase_key = os.getenv('SUPABASE_KEY')
supabase: Client = create_client(supabase_url, supabase_key)

# Set your Tongyi Qwen API key here
QWEN_API_KEY = os.getenv('DASHSCOPE_API_KEY')
DATABASE_URL = os.getenv('DATABASE_URL')

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:  # Check if user_id is in session
            return redirect(url_for('login'))  # Redirect to login page if not logged in
        return f(*args, **kwargs)
    return decorated_function

def get_teacher_personalization(user_id):
    response = supabase.table('teacher_personalization').select('*').eq('user_id', user_id).execute()
    return response.data[0] if response.data else None

def has_personalized_teacher(user_id):
    response = supabase.table('teacher_personalization').select('*').eq('user_id', user_id).execute()
    return len(response.data) > 0

def generate_summary(conversation_history):
    summary = "This is a summarized version of your chat."
    for message in conversation_history:
        summary += f"\n{message['role']}: {message['content']}"
    return summary

def complete_level(user_id, level):
    supabase.table('user_progress').update({
        'level_completed': level + 1
    }).eq('user_id', user_id).lt('level_completed', level + 1).execute()

def update_user_level(user_id, new_level):
    supabase.table('user_progress').update({
        'level_completed': new_level
    }).eq('user_id', user_id).execute()

def save_message(session_id, role, content):
    print(f"Saving message for session_id: {session_id}")
    supabase.table('conversation_history').insert({
        'session_id': session_id,
        'role': role,
        'content': content
    }).execute()

def get_conversation_history(session_id):
    response = supabase.table('conversation_history').select('role', 'content').eq('session_id', session_id).order('timestamp').execute()
    return [{"role": row['role'], "content": row['content']} for row in response.data]

# Function to get a response from the Tongyi Qwen model using the appropriate endpoint
def get_qwen_response(messages=None, user_id=None):
    headers = {
        "Authorization": f"Bearer {QWEN_API_KEY}",
        "Content-Type": "application/json",
    }

    teacher_personalization = get_teacher_personalization(user_id) if user_id else None
    
    base_system_message = """
    You are an English tutor. Help the user learn and practice English by providing explanations, 
    correcting mistakes, and guiding them through exercises. The user likely uses the Indonesian Language. 
    You cant teach the user using English or Indonesian Language to correct mistakes or provide explanations where necessary. 
    For the response, speech recognition will be used, so make it like interactive talking with people.
    Your responses should be concise, avoiding unnecessary length, and should not include example answers unless specifically asked for. 
    Please refrain from using symbols like ** or \"\" unless they are necessary for formatting. 
    Begin by acknowledging the user's needs or questions, and then provide clear and straightforward advice.
    """

    if teacher_personalization:
        teaching_style = teacher_personalization.get('teaching_style', '').lower()
        if teaching_style == 'ramah':
            additional_instruction = "You must be a friendly teacher, that teaches the student slowly until they understand. You are also patient and supportive."
        elif teaching_style == 'disiplin':
            additional_instruction = "You are a strict and disciplined teacher. You set high expectations and push students to meet them. Your tone is firm but fair."
        elif teaching_style == 'interaktif':
            additional_instruction = "You are an interactive teacher. Always engage the student with questions and encourage active participation. Make the learning process dynamic and engaging."
        else:
            additional_instruction = ""

        system_message_content = f"{base_system_message}\n{additional_instruction}"
    else:
        system_message_content = base_system_message

    print(additional_instruction)

    system_message = {
        "role": "system",
        "content": system_message_content
    }

    if messages:
        messages.insert(0, system_message)
    else:
        messages = [system_message]

    data = {
        "model": "qwen-max",
        "input": {
            "messages": messages
        },
        "parameters": {
            "max_tokens": 300
        }
    }

    response = requests.post(
        "https://dashscope-intl.aliyuncs.com/api/v1/services/aigc/text-generation/generation", 
        headers=headers, 
        json=data
    )

    response_json = response.json()

    if response.status_code == 200:
        if "text" in response_json.get("output", {}):
            content = response_json["output"]["text"].strip()
            return content if content else "Maaf, saya tidak mengerti respon itu."
        else:
            return "Tidak ada respon, mohon di ulang."
    else:
        return f"Error: {response.status_code}, {response.text}"
    
@app.route("/")
def root():
    return redirect(url_for('dashboard'))

@app.route('/summarize_chat/<int:level>')
@login_required
def summarize_chat(level):
    user_id = session.get('user_id')
    session_id = f"{user_id}_level{level}"

    # Retrieve the conversation history for this session
    conversation_history = get_conversation_history(session_id)
    
    # Summarize the chat (This is a placeholder; you'll need to implement the actual summarization logic)
    summary = generate_summary(conversation_history)
    
    # Update the user's level in the database
    complete_level(user_id, level)
    
    # Redirect to the summary page or level selection with the summary
    return render_template('summary.html', summary=summary, next_level=level + 1)


@app.route("/chat/<int:level>", methods=["GET", "POST"])
@login_required
def chat(level):
    user_id = session.get("user_id")
    session_id = f"{user_id}_level{level}"

    # Retrieve conversation history from session or database
    conversation_history = get_conversation_history(session_id)

    if request.method == "POST":
        user_input = request.form.get("user_input")
        input_method = request.form.get("input_method")

        # Add user input to the conversation history
        conversation_history.append({"role": "user", "content": user_input})
        save_message(session_id, "user", user_input)

        # Process the user input and get the AI response, passing the user_id
        ai_response = get_qwen_response(conversation_history, user_id)

        # Save AI response in the conversation history
        conversation_history.append({"role": "assistant", "content": ai_response})
        save_message(session_id, "assistant", ai_response)

        # Return the response as JSON
        return jsonify({"assistant_response": ai_response})

    template = f"level{level}.html"
    return render_template(template, conversation_history=conversation_history, level=level)

@app.route("/new_session", methods=["POST"])
@login_required
def new_session():
    session.pop("session_id", None)
    return '', 204  # Return no content

@app.route("/choose_level", methods=["GET", "POST"])
@login_required
def chooselevel():
    user_id = session.get('user_id')
    
    response = supabase.table('user_progress').select('level_completed').eq('user_id', user_id).execute()
    user_level = response.data[0]['level_completed'] if response.data else 1

    return render_template('chooselevel.html', user_level=user_level)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        
        try:
            # Attempt to sign up the user
            response = supabase.auth.sign_up({
                'email': email,
                'password': password
            })

            # If registration is successful but requires email confirmation
            if response.user and not response.user.confirmed_at:
                return render_template('confirm_email.html', email=email)

            # If registration is successful and email is confirmed
            return redirect(url_for('login'))

        except AuthApiError as e:
            # Specific handling for email rate limit exceeded
            if "Email rate limit exceeded" in str(e):
                return render_template('error.html', message="Email rate limit exceeded. Please try again later.")
            # Handle other AuthApiError exceptions
            return render_template('error.html', message=str(e))
        except Exception as e:
            # General exception handling (for any other unforeseen errors)
            return render_template('error.html', message="An unexpected error occurred: " + str(e))

    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        
        try:
            response = supabase.auth.sign_in_with_password({
                'email': email,
                'password': password
            })

            if response.user:
                user_id = response.user.id
                session['user_id'] = user_id
                session['user_email'] = response.user.email
                session['access_token'] = response.session.access_token
                
                user_progress = supabase.table('user_progress').select('*').eq('user_id', user_id).execute()
                if not user_progress.data:
                    supabase.table('user_progress').insert({
                        'user_id': user_id,
                        'level_completed': 1
                    }).execute()

                # Check if the user has personalized their teacher
                if not has_personalized_teacher(user_id):
                    return redirect(url_for('personalize_teacher'))
                else:
                    return redirect(url_for('dashboard'))

            return render_template('error.html', message="Login failed. Please check your credentials.")

        except AuthApiError as e:
            return render_template('error.html', message=f"Auth error: {str(e)}")

        except Exception as e:
            return render_template('error.html', message=f"An unexpected error occurred: {str(e)}")

    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    session.pop('user', None)  # Remove the user from session
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    user_id = session.get('user_id')
    user_email = session.get('user_email')
    
    # Render the dashboard with user-specific content
    return render_template('dashboard.html', user_email=user_email)

@app.route('/personalize_teacher', methods=['GET', 'POST'])
@login_required
def personalize_teacher():
    user_id = session['user_id']
    
    if request.method == 'POST':
        name = request.form.get('name', '')
        teaching_style = request.form.get('teaching_style', '')
        avatar_url = request.form.get('avatar_url', '')
        added_description = request.form.get('added_description', '')
        
        try:
            # Check if a record already exists for this user
            existing_record = supabase.table('teacher_personalization').select('*').eq('user_id', user_id).execute()
            
            if existing_record.data:
                # If a record exists, update it
                supabase.table('teacher_personalization').update({
                    'name': name,
                    'avatar_url': avatar_url,
                    'teaching_style': teaching_style,
                    'added_description': added_description
                }).eq('user_id', user_id).execute()
            else:
                # If no record exists, insert a new one
                supabase.table('teacher_personalization').insert({
                    'user_id': user_id,
                    'name': name,
                    'avatar_url': avatar_url,
                    'teaching_style': teaching_style,
                    'added_description': added_description
                }).execute()
            
            # After successful personalization, redirect to dashboard
            return redirect(url_for('dashboard'))
        except Exception as e:
            return render_template('error.html', message=str(e))

    # For GET request, fetch existing personalization if any
    try:
        response = supabase.table('teacher_personalization').select('*').eq('user_id', user_id).execute()
        personalization = response.data[0] if response.data else None
        return render_template('generate-teacher.html', personalization=personalization)
    except Exception as e:
        return render_template('error.html', message=str(e))

@app.route('/chat/level1')
@login_required
def chat_level1():
    return redirect(url_for('chat', level=1))

@app.route('/chat/level2')
@login_required
def chat_level2():
    return redirect(url_for('chat', level=2))

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8000)
