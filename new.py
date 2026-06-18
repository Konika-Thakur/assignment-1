import streamlit as st
import base64
import pandas as pd
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

# Function to display PowerPoint preview
def displayPPT(file_path):
    st.markdown(f"""
    <div style="padding: 20px; border: 2px dashed #C0C0C0; border-radius: 10px; text-align: center;">
        <h3 style="color: #C0C0C0;">📊 PowerPoint File Loaded</h3>
        <p style="color: #A0A0A0;">File: {file_path.split('/')[-1]}</p>
        <p style="color: #A0A0A0;">Content has been processed and is ready for questions!</p>
    </div>
    """, unsafe_allow_html=True)

# Function to display Excel preview
def displayExcel(file_path):
    try:
        # Read Excel file to get basic info
        excel_file = pd.ExcelFile(file_path)
        sheet_names = excel_file.sheet_names
        
        # Get total number of sheets and basic info
        total_sheets = len(sheet_names)
        
        # Read first sheet to get dimensions
        first_sheet = pd.read_excel(file_path, sheet_name=sheet_names[0])
        rows, cols = first_sheet.shape
        
        st.markdown(f"""
        <div style="padding: 20px; border: 2px dashed #C0C0C0; border-radius: 10px; text-align: center;">
            <h3 style="color: #C0C0C0;">📊 Excel File Loaded</h3>
            <p style="color: #A0A0A0;">File: {file_path.split('/')[-1]}</p>
            <p style="color: #A0A0A0;">Sheets: {total_sheets} | Sample Dimensions: {rows} rows × {cols} columns</p>
            <p style="color: #A0A0A0;">Sheet Names: {', '.join(sheet_names[:3])}{' ...' if len(sheet_names) > 3 else ''}</p>
            <p style="color: #A0A0A0;">Content has been processed and is ready for questions!</p>
        </div>
        """, unsafe_allow_html=True)
        
        # Show preview of first sheet
        st.markdown("### 📋 First Sheet Preview:")
        st.dataframe(first_sheet.head(10), use_container_width=True)
        
    except Exception as e:
        st.markdown(f"""
        <div style="padding: 20px; border: 2px dashed #C0C0C0; border-radius: 10px; text-align: center;">
            <h3 style="color: #C0C0C0;">📊 Excel File Loaded</h3>
            <p style="color: #A0A0A0;">File: {file_path.split('/')[-1]}</p>
            <p style="color: #A0A0A0;">Content has been processed and is ready for questions!</p>
            <p style="color: #FF6B6B;">Note: Preview unavailable, but file is ready for chat.</p>
        </div>
        """, unsafe_allow_html=True)

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
if 'temp_file_path' not in st.session_state:
    st.session_state['temp_file_path'] = None
if 'file_type' not in st.session_state:
    st.session_state['file_type'] = None
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
        Chat with PDFs, PowerPoints & Excel Files
    </div>
    </div>
""", unsafe_allow_html=True)

# File uploader within a container
def file_uploader():
    st.markdown("<div class='pdf-container'>", unsafe_allow_html=True)
    st.markdown(f"""<img src="data:image/svg+xml;base64,{icon_base64}" alt="icon-image" class='image-div'/>""", unsafe_allow_html=True)

    # Updated file uploader to include Excel formats
    uploaded_file = st.file_uploader(
        "Chat with PDFs, PowerPoints & Excel Files", 
        type=["pdf", "ppt", "pptx", "xls", "xlsx", "xlsm", "xlsb"], 
        label_visibility="hidden"
    )

    # Process the uploaded file
    if uploaded_file is not None:
        if uploaded_file.size > 200 * 1024 * 1024:  # File size limit check
            st.error("⚠️ File size exceeds the 200 MB limit. Please upload a smaller file.")
        else:
            # Show loader while processing
            st.session_state['show_loader'] = True
            with st.spinner("Processing the uploaded file..."):
                display_style = "flex" if st.session_state['show_loader'] else "hidden"
                st.markdown(f'<div class="lottie-container" style="display: {display_style};">', unsafe_allow_html=True)
                if lottie_animation:
                    st_lottie(lottie_animation, height=200, width=200, key="processing")
                    st.markdown('</div>', unsafe_allow_html=True)

                # Determine file type and save to temporary location
                file_extension = uploaded_file.name.split('.')[-1].lower()
                temp_file_path = f"temp.{file_extension}"
                
                with open(temp_file_path, "wb") as f:
                    f.write(uploaded_file.getbuffer())

                st.session_state['temp_file_path'] = temp_file_path
                st.session_state['file_type'] = file_extension

                # Initialize the EmbeddingsManager
                embeddings_manager = EmbeddingsManager(
                    model_name="BAAI/bge-small-en",
                    device="cpu",
                    encode_kwargs={"normalize_embeddings": True},
                    qdrant_url="http://localhost:6333",
                    collection_name="vector_db"
                )

                # Create embeddings
                try:
                    result_message = embeddings_manager.create_embeddings(temp_file_path)
                    st.success(result_message)
                except Exception as e:
                    st.error(f"⚠️ Error processing file: {str(e)}")
                    return

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

            # Show success message based on file type
            file_type_display = {
                'pdf': 'PDF',
                'ppt': 'PowerPoint',
                'pptx': 'PowerPoint',
                'xls': 'Excel',
                'xlsx': 'Excel',
                'xlsm': 'Excel',
                'xlsb': 'Excel'
            }.get(file_extension, 'File')

            st.markdown(f'''
                <div class="success-message" style="color: #C0C0C0; font-weight: bold; text-shadow: 2px 2px 4px rgba(0, 0, 0, 0.5); font-size: 20px; font-family: 'Georgia', serif;">
                    🎉 <span>{file_type_display} file processed successfully!</span> Ready for interaction.
                </div>
            ''', unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)

# Call the file uploader function
file_uploader()

# Display File Preview and Chat Window
if st.session_state['temp_file_path'] and st.session_state['chatbot_manager']:
    file_chat_cols = st.columns(2)

    # File Preview
    with file_chat_cols[0]:
        if st.session_state['file_type'] == 'pdf':
            st.markdown("<div class='question-title' style='color: #C0C0C0; font-weight: bold; text-shadow: 2px 2px 4px rgba(0, 0, 0, 0.5); font-size: 30px;'>📖 PDF Preview </div>", unsafe_allow_html=True)
            with open(st.session_state['temp_file_path'], "rb") as pdf_file:
                displayPDF(pdf_file)
        elif st.session_state['file_type'] in ['ppt', 'pptx']:
            st.markdown("<div class='question-title' style='color: #C0C0C0; font-weight: bold; text-shadow: 2px 2px 4px rgba(0, 0, 0, 0.5); font-size: 30px;'>📊 PowerPoint Preview </div>", unsafe_allow_html=True)
            displayPPT(st.session_state['temp_file_path'])
        elif st.session_state['file_type'] in ['xls', 'xlsx', 'xlsm', 'xlsb']:
            st.markdown("<div class='question-title' style='color: #C0C0C0; font-weight: bold; text-shadow: 2px 2px 4px rgba(0, 0, 0, 0.5); font-size: 30px;'>📊 Excel Preview </div>", unsafe_allow_html=True)
            displayExcel(st.session_state['temp_file_path'])

    # Chat Window
    with file_chat_cols[1]:
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