# AI Chatbot & Code Generator

An AI-powered development assistant built with Python and Streamlit. The application combines an AI chatbot, Retrieval-Augmented Generation (RAG) for document-based question answering, and an AI code generator with code execution.

## Features

### AI Assistant
- Conversational AI assistant powered by Llama 3.2
- Simple and user-friendly Streamlit interface
- Maintains conversation history
- Recent search history

### RAG Document Question Answering
- Upload PDF, TXT, and DOCX documents
- Extract and process document content
- Create a vector database from uploaded documents
- Retrieve relevant document sections using similarity search
- Generate answers using retrieved context

### AI Code Generator
- Generate code from natural-language prompts
- Supports:
  - Python
  - Java
  - C
  - C++
  - JavaScript
- Difficulty levels:
  - Beginner
  - Intermediate
  - Advanced
- Generates complete executable code
- Supports program input and output
- Executes generated programs and displays the result
- Handles compilation and runtime errors

## Technologies Used

- Python
- Streamlit
- Ollama
- Llama 3.2
- LangChain
- Retrieval-Augmented Generation (RAG)
- Vector Database
- Document Processing
- Natural Language Processing

## Project Structure

```text
AI-Chatbot-Code-Generator/
│
├── app.py
├── rag.py
├── prompts.py
├── requirements.txt
├── .gitignore
└── README.md
