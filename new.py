import streamlit as st
import base64
from vectors import EmbeddingsManager  # Import the EmbeddingsManager class
from chatbot import ChatbotManager     # Import the ChatbotManager class
import requests  # For Qdrant health checks
import streamlit.components.v1 as components
from streamlit_lottie import st_lottie  # Import Lottie animation component
import json

# Function to load Lottie animation from file
def load_lottie_json(filepath: str):
    with open(filepath, "r") as f:
        return json.load(f)

# Function to display the PDF of a given file
def displayPDF(file):
    base64_pdf = base64.b64encode(file.read()).decode('utf-8')
    pdf_display = f'''
    <style>
        .pdf-container {{
            border-radius: 17px;
            overflow: hidden;
            box-shadow: 0 4px 8px rgba(0, 0, 0, 0);
        }}
    </style>
    <div class="pdf-container">
        <iframe src="data:application/pdf;base64,{base64_pdf}" width="100%" height="1000" type="application/pdf"></iframe>
    </div>
    '''
    st.markdown(pdf_display, unsafe_allow_html=True)

# Function to load an image as base64
def get_base64_image(image_path):
    with open(image_path, "rb") as img_file:
        return base64.b64encode(img_file.read()).decode("utf-8")

# Load the CSS file
def load_css(css_file_path):
    with open(css_file_path, 'r') as f:
        css_content = f.read()
        st.markdown(f"<style>{css_content}</style>", unsafe_allow_html=True)

# Initialize session state variables
if 'temp_pdf_path' not in st.session_state:
    st.session_state['temp_pdf_path'] = None
if 'chatbot_manager' not in st.session_state:
    st.session_state['chatbot_manager'] = None
if 'messages' not in st.session_state:
    st.session_state['messages'] = []
if 'show_loader' not in st.session_state:
    st.session_state['show_loader'] = False

# Set the page configuration
st.set_page_config(page_title="Doc Talk", layout="wide", initial_sidebar_state="expanded")

# Load external CSS
load_css("style.css")

# Encode the image as base64
icon_base64 = get_base64_image("icon.svg")
# Load the Lottie animation JSON
lottie_animation = load_lottie_json("loader.json")

# Page Title
st.markdown(f"""
    <link href="https://fonts.googleapis.com/icon?family=Material+Icons" rel="stylesheet">
    <div>
    <div class='stTitle' style='font-size: 72px; font-weight: bold; color: #000;'>
        <i class="material-icons" style="font-size:64px;vertical-align:middle;">description</i>
        Doc Talk
    </div>
    <div class='sub-heading'>
        Chat with PDFs
    </div>
    </div>
""", unsafe_allow_html=True)

# File uploader within a container
def pdf_uploader():
    st.markdown("<div class='pdf-container'>", unsafe_allow_html=True)
    st.markdown(f"""<img src="data:image/svg+xml;base64,{icon_base64}" alt="icon-image" class='image-div'/>""", unsafe_allow_html=True)

    uploaded_file = st.file_uploader("Chat with PDFs", type=["pdf"], label_visibility="hidden")

    # Process the uploaded file
    if uploaded_file is not None:
        if uploaded_file.size > 200 * 1024 * 1024:  # File size limit check
            st.error("⚠️ File size exceeds the 200 MB limit. Please upload a smaller file.")
        else:
            # Show loader while processing
            st.session_state['show_loader'] = True
            with st.spinner("Processing the uploaded PDF..."):
                display_style = "flex" if st.session_state['show_loader'] else "hidden"
                st.markdown(f'<div class="lottie-container" style="display: {display_style};">', unsafe_allow_html=True)
                if lottie_animation:
                    st_lottie(lottie_animation, height=200, width=200, key="processing")
                    st.markdown('</div>', unsafe_allow_html=True)

                # Save the uploaded file to a temporary location
                temp_pdf_path = "temp.pdf"
                with open(temp_pdf_path, "wb") as f:
                    f.write(uploaded_file.getbuffer())

                st.session_state['temp_pdf_path'] = temp_pdf_path

                # Initialize the EmbeddingsManager
                embeddings_manager = EmbeddingsManager(
                    model_name="BAAI/bge-small-en",
                    device="cpu",
                    encode_kwargs={"normalize_embeddings": True},
                    qdrant_url="http://localhost:6333",
                    collection_name="vector_db"
                )

                # Create embeddings
                embeddings_manager.create_embeddings(temp_pdf_path)

                # Initialize the ChatbotManager
                st.session_state['chatbot_manager'] = ChatbotManager(
                    model_name="BAAI/bge-small-en",
                    device="cpu",
                    encode_kwargs={"normalize_embeddings": True},
                    llm_model="llama3.2-vision",
                    llm_temperature=0.7,
                    qdrant_url="http://localhost:6333",
                    collection_name="vector_db"
                )

            # Hide loader after processing
            st.session_state['show_loader'] = False

            st.markdown('''
                <div class="success-message" style="color: #C0C0C0; font-weight: bold; text-shadow: 2px 2px 4px rgba(0, 0, 0, 0.5); font-size: 20px; font-family: 'Georgia', serif;">
                    🎉 <span>File processed successfully!</span> Ready for interaction.
                </div>
            ''', unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)

# Call the PDF uploader function
pdf_uploader()

# Display PDF and Chat Window
if st.session_state['temp_pdf_path'] and st.session_state['chatbot_manager']:
    pdf_chat_cols = st.columns(2)

    # PDF Preview
    with pdf_chat_cols[0]:
        st.markdown("<div class='question-title' style='color: #C0C0C0; font-weight: bold; text-shadow: 2px 2px 4px rgba(0, 0, 0, 0.5); font-size: 30px;'>📖 PDF Preview </div>", unsafe_allow_html=True)
        with open(st.session_state['temp_pdf_path'], "rb") as pdf_file:
            displayPDF(pdf_file)

    # Chat Window
    with pdf_chat_cols[1]:
        st.markdown("<div class='question-title' style='color: #C0C0C0; font-weight: bold; text-shadow: 2px 2px 4px rgba(0, 0, 0, 0.5); font-size: 30px;'>📑 Question & Answer</div>", unsafe_allow_html=True)
        # Display existing messages
        for msg in st.session_state['messages']:
            st.chat_message(msg['role']).markdown(msg['content'])

        # User input
        if user_input := st.chat_input("Ask a question about the document...", key="user_input"):
            st.markdown('''
                <style>
                    .st-chat-input {
                        color: #C0C0C0; /* Metallic Silver */
                        text-shadow: 1px 1px 2px rgba(0, 0, 0, 0.5); /* Shadow effect */
                        font-size: 18px;
                        font-weight: bold;
                        font-family: 'Arial', sans-serif;
                        border: 1px solid #C0C0C0;
                        border-radius: 8px;
                        padding: 10px;
                    }
                </style>
            ''', unsafe_allow_html=True)

            # Display user message
            st.chat_message("user").markdown(user_input)
            st.session_state['messages'].append({"role": "user", "content": user_input})

            with st.spinner("🤖 Generating response..."):
                try:
                    # Get the chatbot response using the ChatbotManager
                    answer = st.session_state['chatbot_manager'].get_response(user_input)
                except Exception as e:
                    answer = f"⚠️ An error occurred while processing your request: {e}"

            # Display chatbot message
            solution_box_html = f"""
                <div class='solution-box'>
                    {answer}
                </div>
            """
            st.markdown(solution_box_html, unsafe_allow_html=True)
            st.session_state['messages'].append({"role": "assistant", "content": answer})
