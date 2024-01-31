import json
import time
import streamlit as st
from openai import OpenAI
from io import BytesIO
import os

temperature=0.0
max_tokens=1000
frequency_penalty=0.0

saved_api_key=None
client = None

def initialize_openai_client(api_key):
    print("initialize_openai_client with "+api_key)
    return OpenAI(api_key=api_key)

default_prompt = "Résume ce pdf pour un post LinkedIn, ne retourne que le post avec les #."

def create_assistant(model):
    global client
    assistant = client.beta.assistants.create(
    name = "LinkedIn assistant",
    instructions = "You are a helpful assistant that can read PDFs and create linkedIn posts with great impact",
    tools = [{"type":"code_interpreter"}, {"type": "retrieval"}],
    model = model
    )
    return assistant

def show_json(obj):
    print(json.dumps(json.loads(obj.model_dump_json()), indent=4))

def submit_message(assistant_id, thread, user_message):
    global client
    client.beta.threads.messages.create(
        thread_id=thread.id, role="user", content=user_message
    )
    return client.beta.threads.runs.create(
        thread_id=thread.id,
        assistant_id=assistant_id,
    )

def wait_on_run(run, thread):
    global client
    while run.status == "queued" or run.status == "in_progress":
        run = client.beta.threads.runs.retrieve(
            thread_id=thread.id,
            run_id=run.id,
        )
        time.sleep(0.5)
    return run

def get_response(thread):
    global client
    return client.beta.threads.messages.list(thread_id=thread.id, order="asc")

def pretty_print(messages):
    responses = []
    for m in messages:
        if m.role == "assistant":
            responses.append(m.content[0].text.value)
    return "\n".join(responses)

def main():
    global client, saved_api_key
    st.title("Post LinkedIn à partir d'un pdf et d'un prompt")
    entered_api_key = st.sidebar.text_input("OpenAI API key", type="password")

    if entered_api_key and entered_api_key != saved_api_key:
        with st.spinner('Initialisation OpenAI...'):
            saved_api_key = entered_api_key
            client = initialize_openai_client(saved_api_key)

    model_choice = st.sidebar.selectbox("Choisis un modèle", ["gpt-3.5-turbo-1106", "gpt-4-turbo-preview"])
    user_query = st.text_input(label="Ton prompt",value=default_prompt)
    uploaded_file = st.file_uploader("Upload du pdf", type=["pdf"], accept_multiple_files=False)
    
    if saved_api_key is not None and model_choice is not None and uploaded_file is not None and user_query:
        with st.spinner('Je travaille...'):
            temp_dir = "temp"
            if not os.path.exists(temp_dir):
                os.makedirs(temp_dir)

            temp_file_path = os.path.join(temp_dir, uploaded_file.name)
            with open(temp_file_path, "wb") as f:
                f.write(uploaded_file.getbuffer())

            try:
                file_response = client.files.create(
                    file=open(temp_file_path, "rb"),
                    purpose="assistants",
                )
                assistant = create_assistant(model_choice)
            
                assistant_id = assistant.id
                thread = client.beta.threads.create()
                assistant = client.beta.assistants.update(
                    assistant_id,
                    file_ids=[file_response.id],
                )
                run = submit_message(assistant_id, thread, user_query)

                run = wait_on_run(run, thread)

                response_messages = get_response(thread)
                response = pretty_print(response_messages)
                st.text_area("Response:", value=response, height=300)
                #        file = client.files.create( file=open("file.pdf", "rb"), purpose="fine-tune" ) 
            except Exception as e:
                st.error(f"An error occurred: {e}")
                

if __name__ == "__main__":
    main()
