import os
import fitz  
import docx
import pdfplumber
from fpdf import FPDF
import streamlit as st
from transformers import pipeline
import google.generativeai as genai
from tempfile import NamedTemporaryFile


os.environ["GOOGLE_API_KEY"] = "AIzaSyDHWcf9xQYvSWt9rIVlOevATtsrzFCOid4"
genai.configure(api_key=os.environ["GOOGLE_API_KEY"])
model = genai.GenerativeModel("models/gemini-1.5-pro")

@st.cache_resource
def load_summarizer():
    return pipeline("summarization", model="facebook/bart-large-cnn")

summarizer = load_summarizer()



def extract_text_from_pdf(file):
    text = ""
    pdf = fitz.open(stream=file.read(), filetype="pdf")
    for page in pdf:
        text += page.get_text()
    return text

def extract_text_from_docx(file):
    doc = docx.Document(file)
    return ' '.join([para.text for para in doc.paragraphs])

def extract_text(file, ext):
    if ext == 'pdf':
        return extract_text_from_pdf(file)
    elif ext == 'docx':
        return extract_text_from_docx(file)
    elif ext == 'txt':
        return file.read().decode('utf-8')
    return ""

def split_text(text, max_length=1024):
    sentences = text.split('. ')
    chunks = []
    current_chunk = ''
    for sentence in sentences:
        if len(current_chunk) + len(sentence) <= max_length:
            current_chunk += sentence + '. '
        else:
            chunks.append(current_chunk.strip())
            current_chunk = sentence + '. '
    if current_chunk:
        chunks.append(current_chunk.strip())
    return chunks

def summarize_text(text):
    chunks = split_text(text)
    summary = ""
    for chunk in chunks:
        result = summarizer(chunk, max_length=150, min_length=40, do_sample=False)
        summary += result[0]['summary_text'] + "\n"
    return summary.strip()

def generate_mcqs(input_text, num_questions):
    prompt = f"""
You are an AI assistant helping the user generate multiple-choice questions (MCQs) based on the following text:
'{input_text}'
Please generate {num_questions} MCQs from the text. Each question should have:
- A clear question
- Four answer options (labeled A, B, C, D)
- The correct answer clearly indicated
Format:
## MCQ
Question: [question]
A) [option A]
B) [option B]
C) [option C]
D) [option D]
Correct Answer: [correct option]
"""
    response = model.generate_content(prompt).text.strip()
    return response

def create_pdf(mcqs):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    for mcq in mcqs.split("## MCQ"):
        if mcq.strip():
            pdf.multi_cell(0, 10, mcq.strip())
            pdf.ln(5)
    temp_file = NamedTemporaryFile(delete=False, suffix=".pdf")
    pdf.output(temp_file.name)
    return temp_file.name


st.title("📚 PDF/DOCX Summarizer & MCQ Generator")


mode = st.radio(
    "What would you like to do?",
    ("Summarize Document", "Generate MCQs", "Both")
)


uploaded_file = st.file_uploader("Upload a PDF, DOCX, or TXT file", type=["pdf", "docx", "txt"])

if uploaded_file:
    file_extension = uploaded_file.name.rsplit('.', 1)[-1].lower()
    text = extract_text(uploaded_file, file_extension)

    if text.strip() == "":
        st.warning("No readable text found in the uploaded file.")
    else:
        st.success("Text extracted successfully!")

        summary = text
        mcqs = ""

        
        if mode in ["Summarize Document", "Both"]:
            with st.spinner("Summarizing..."):
                summary = summarize_text(text)
            st.subheader(" Summary")
            st.text_area("Summarized Text", summary, height=200)
            st.download_button("Download Summary", summary, file_name="summary.txt", mime="text/plain")

        if mode in ["Generate MCQs", "Both"]:
            st.subheader("Generate MCQs")
            num_questions = st.number_input("Number of MCQs to generate", min_value=1, max_value=20, value=5)

            if st.button("Generate MCQs"):
                with st.spinner("Generating MCQs..."):
                    mcqs = generate_mcqs(summary if mode == "Both" else text, num_questions)

                st.subheader("Generated MCQs")
                st.text_area("MCQs", mcqs, height=300)

                st.download_button(
                    label="Download as TXT",
                    data=mcqs,
                    file_name="generated_mcqs.txt",
                    mime="text/plain"
                )

                pdf_path = create_pdf(mcqs)
                with open(pdf_path, "rb") as f:
                    st.download_button("Download as PDF", f, file_name="generated_mcqs.pdf", mime="application/pdf")