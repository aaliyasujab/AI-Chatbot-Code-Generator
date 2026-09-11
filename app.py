
import streamlit as st
import ollama
import os
import tempfile
import json
import subprocess
import shutil

from prompts import SYSTEM_PROMPT
from rag import load_document, create_vector_database


# =========================================================
# CONFIGURATION
# =========================================================

MODEL_NAME = "llama3.2"
APP_VERSION = "3.1 RAG"
RECENT_SEARCH_FILE = "recent_searches.json"
MAX_RECENT_SEARCHES = 10


# =========================================================
# PAGE CONFIGURATION
# =========================================================

st.set_page_config(
    page_title="Alpha",
    page_icon=None,
    layout="wide"
)


# =========================================================
# BLACK THEME
# =========================================================

st.markdown("""
<style>

    .stApp {
        background-color: #000000;
        color: #ffffff;
    }

    .main {
        background-color: #000000;
    }

    section[data-testid="stSidebar"] {
        background-color: #000000;
        border-right: 1px solid #222222;
    }

    section[data-testid="stSidebar"] * {
        color: #ffffff !important;
    }

    h1, h2, h3, h4 {
        color: #ffffff !important;
    }

    p, label, span {
        color: #ffffff;
    }

    div[data-baseweb="select"] > div {
        background-color: #111111;
        border: 1px solid #333333;
        color: #ffffff;
    }

    div[data-baseweb="select"] * {
        color: #ffffff !important;
    }

    textarea {
        background-color: #111111 !important;
        color: #ffffff !important;
        border: 1px solid #333333 !important;
        border-radius: 8px !important;
    }

    textarea::placeholder {
        color: #777777 !important;
    }

    div[data-testid="stChatInput"] {
        background-color: #000000;
    }

    div[data-testid="stChatInput"] textarea {
        background-color: #111111 !important;
        color: #ffffff !important;
        border: 1px solid #333333 !important;
    }

    .stButton > button {
        background-color: #111111;
        color: #ffffff;
        border: 1px solid #333333;
        border-radius: 7px;
    }

    .stButton > button:hover {
        background-color: #222222;
        border-color: #555555;
    }

    section[data-testid="stFileUploaderDropzone"] {
        background-color: #111111;
        border: 1px dashed #444444;
    }

    div[data-testid="stAlert"] {
        background-color: #111111;
        border: 1px solid #333333;
        color: #ffffff;
    }

    hr {
        border-color: #222222;
    }

    div[data-testid="stChatMessage"] {
        background-color: #000000;
    }

    pre {
        background-color: #111111 !important;
        border: 1px solid #333333;
    }

    code {
        color: #ffffff !important;
    }

    /* ALPHA LOGO */

    .alpha-logo {
        display: flex;
        align-items: center;
        gap: 10px;
        margin-bottom: 5px;
    }

    .alpha-symbol {
        width: 34px;
        height: 34px;
        border: 2px solid #ffffff;
        border-radius: 8px;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 17px;
        font-weight: 700;
        letter-spacing: -1px;
    }

    .alpha-name {
        font-size: 23px;
        font-weight: 700;
        letter-spacing: 2px;
    }

    .alpha-tagline {
        color: #777777 !important;
        font-size: 12px;
        margin-top: 2px;
        margin-bottom: 15px;
    }

    /* Recent search items */

    .recent-title {
        font-size: 13px;
        color: #888888 !important;
        margin-bottom: 8px;
    }

    .recent-item {
        background-color: #0d0d0d;
        border: 1px solid #222222;
        border-radius: 6px;
        padding: 8px 10px;
        margin-bottom: 6px;
        font-size: 12px;
        color: #cccccc !important;
        overflow: hidden;
        white-space: nowrap;
        text-overflow: ellipsis;
    }

</style>
""", unsafe_allow_html=True)


# =========================================================
# MODEL FUNCTION
# =========================================================

def get_model():
    """
    Central model configuration.
    Change the model here if needed.
    """
    return MODEL_NAME


# =========================================================
# CODE EXECUTION FUNCTION
# =========================================================

def extract_code(text):
    """Extract clean executable code from AI response."""

    text = text.strip()

    # If the AI used a Markdown code block
    if "```" in text:
        parts = text.split("```")

        if len(parts) >= 2:
            code = parts[1].strip()
            lines = code.splitlines()

            # Remove language name such as python, py, java, etc.
            if lines and lines[0].strip().lower() in {
                "python",
                "py",
                "java",
                "c",
                "cpp",
                "c++",
                "javascript",
                "js",
                "markdown"
            }:
                lines = lines[1:]

            return "\n".join(lines).strip()

    # Handle responses where the model accidentally starts with
    # "markdown" without using ``` blocks.
    lines = text.splitlines()

    while lines and lines[0].strip().lower() in {
        "markdown",
        "python",
        "py",
        "javascript",
        "js",
        "java",
        "c",
        "cpp",
        "c++"
    }:
        lines.pop(0)

    return "\n".join(lines).strip()

def run_code(code, language, user_input=""):
    """Run generated code locally and return its output."""
    code = extract_code(code)
    user_input = user_input or ""

    try:
        if language == "Python":
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".py", delete=False, encoding="utf-8"
            ) as file:
                file.write(code)
                file_path = file.name

            try:
                result = subprocess.run(
                    ["python", file_path],
                    input=user_input,
                    capture_output=True,
                    text=True,
                    timeout=10
                )
            finally:
                if os.path.exists(file_path):
                    os.remove(file_path)

        elif language == "JavaScript":
            if not shutil.which("node"):
                return "Node.js is not installed or is not in PATH."

            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".js", delete=False, encoding="utf-8"
            ) as file:
                file.write(code)
                file_path = file.name

            try:
                result = subprocess.run(
                    ["node", file_path],
                    input=user_input,
                    capture_output=True,
                    text=True,
                    timeout=10
                )
            finally:
                if os.path.exists(file_path):
                    os.remove(file_path)

        elif language in ("C", "C++"):
            compiler = "gcc" if language == "C" else "g++"
            if not shutil.which(compiler):
                return f"{compiler} is not installed or is not in PATH."

            suffix = ".c" if language == "C" else ".cpp"

            with tempfile.TemporaryDirectory() as temp_dir:
                source_file = os.path.join(temp_dir, "program" + suffix)
                executable = os.path.join(
                    temp_dir, "program.exe" if os.name == "nt" else "program"
                )

                with open(source_file, "w", encoding="utf-8") as file:
                    file.write(code)

                compile_result = subprocess.run(
                    [compiler, source_file, "-o", executable],
                    capture_output=True,
                    text=True,
                    timeout=10
                )

                if compile_result.returncode != 0:
                    return "Compilation Error:\n" + (
                        compile_result.stderr or compile_result.stdout
                    )

                result = subprocess.run(
                    [executable],
                    input=user_input,
                    capture_output=True,
                    text=True,
                    timeout=10
                )

        elif language == "Java":
            if not shutil.which("javac") or not shutil.which("java"):
                return "Java/Javac is not installed or is not in PATH."

            with tempfile.TemporaryDirectory() as temp_dir:
                source_file = os.path.join(temp_dir, "Main.java")

                with open(source_file, "w", encoding="utf-8") as file:
                    file.write(code)

                compile_result = subprocess.run(
                    ["javac", source_file],
                    capture_output=True,
                    text=True,
                    timeout=10,
                    cwd=temp_dir
                )

                if compile_result.returncode != 0:
                    return "Compilation Error:\n" + (
                        compile_result.stderr or compile_result.stdout
                    )

                result = subprocess.run(
                    ["java", "Main"],
                    input=user_input,
                    capture_output=True,
                    text=True,
                    timeout=10,
                    cwd=temp_dir
                )

        else:
            return "Unsupported programming language."

        if result.returncode != 0:
            return "Runtime Error:\n" + (
                result.stderr or result.stdout or "Unknown error."
            )

        return result.stdout if result.stdout else "Program executed successfully with no output."

    except subprocess.TimeoutExpired:
        return "Execution stopped: the program took longer than 10 seconds."
    except Exception as e:
        return f"Execution error: {e}"


# =========================================================
# RECENT SEARCH FUNCTIONS
# =========================================================

def load_recent_searches():

    if not os.path.exists(RECENT_SEARCH_FILE):
        return []

    try:

        with open(
            RECENT_SEARCH_FILE,
            "r",
            encoding="utf-8"
        ) as file:

            searches = json.load(file)

        if isinstance(searches, list):
            return searches

        return []

    except Exception:

        return []


def save_recent_search(search):

    search = search.strip()

    if not search:
        return

    searches = load_recent_searches()

    # Remove duplicate
    searches = [
        item for item in searches
        if item != search
    ]

    # Add newest search at beginning
    searches.insert(0, search)

    # Keep only recent searches
    searches = searches[:MAX_RECENT_SEARCHES]

    try:

        with open(
            RECENT_SEARCH_FILE,
            "w",
            encoding="utf-8"
        ) as file:

            json.dump(
                searches,
                file,
                indent=4,
                ensure_ascii=False
            )

    except Exception as e:

        print(
            f"Could not save recent search: {e}"
        )


# =========================================================
# SESSION STATE
# =========================================================

if "messages" not in st.session_state:
    st.session_state.messages = []

if "vector_db" not in st.session_state:
    st.session_state.vector_db = None

if "uploaded_documents" not in st.session_state:
    st.session_state.uploaded_documents = []

if "recent_searches" not in st.session_state:
    st.session_state.recent_searches = load_recent_searches()

if "generated_code" not in st.session_state:
    st.session_state.generated_code = ""

if "generated_language" not in st.session_state:
    st.session_state.generated_language = ""

if "program_input" not in st.session_state:
    st.session_state.program_input = ""

if "program_output" not in st.session_state:
    st.session_state.program_output = ""


# =========================================================
# SIDEBAR
# =========================================================

with st.sidebar:

    # -----------------------------------------------------
    # ALPHA LOGO
    # -----------------------------------------------------

    st.markdown("""
    <div class="alpha-logo">
        <div class="alpha-symbol">A</div>
        <div class="alpha-name">ALPHA</div>
    </div>

    <div class="alpha-tagline">
        AI Development Assistant
    </div>
    """, unsafe_allow_html=True)

    st.markdown("---")


    # =====================================================
    # MODE
    # =====================================================

    st.write("### Mode")

    mode = st.radio(
        "Select mode",
        [
            "AI Assistant",
            "Code Generator"
        ],
        label_visibility="collapsed"
    )

    st.markdown("---")


    # =====================================================
    # AI ASSISTANT DOCUMENT UPLOAD
    # =====================================================

    if mode == "AI Assistant":

        st.write("### Upload Documents")

        uploaded_files = st.file_uploader(
            "Upload PDF, TXT or DOCX files",
            type=["pdf", "txt", "docx"],
            accept_multiple_files=True
        )

        if uploaded_files:

            if st.button(
                "Process Documents",
                use_container_width=True
            ):

                with st.spinner(
                    "Processing documents..."
                ):

                    all_documents = []
                    new_document_names = []

                    try:

                        for uploaded_file in uploaded_files:

                            suffix = os.path.splitext(
                                uploaded_file.name
                            )[1]

                            with tempfile.NamedTemporaryFile(
                                delete=False,
                                suffix=suffix
                            ) as temp_file:

                                temp_file.write(
                                    uploaded_file.getbuffer()
                                )

                                temp_path = temp_file.name


                            documents = load_document(
                                temp_path
                            )


                            for document in documents:

                                document.metadata[
                                    "source"
                                ] = uploaded_file.name


                            all_documents.extend(
                                documents
                            )

                            new_document_names.append(
                                uploaded_file.name
                            )


                        st.session_state.vector_db = (
                            create_vector_database(
                                all_documents
                            )
                        )


                        st.session_state.uploaded_documents = (
                            new_document_names
                        )


                        st.success(
                            f"{len(new_document_names)} "
                            "document(s) processed."
                        )


                    except Exception as e:

                        st.error(
                            f"Error: {e}"
                        )


        # -------------------------------------------------
        # DOCUMENT LIST
        # -------------------------------------------------

        if st.session_state.uploaded_documents:

            st.markdown("---")

            st.write("### Uploaded Documents")

            for filename in (
                st.session_state.uploaded_documents
            ):

                st.caption(
                    filename
                )


    # =====================================================
    # CODE GENERATOR SETTINGS
    # =====================================================

    else:

        st.write("### Code Settings")

        programming_language = st.selectbox(
            "Programming Language",
            [
                "Python",
                "Java",
                "C",
                "C++",
                "JavaScript"
            ]
        )

        difficulty = st.selectbox(
            "Difficulty",
            [
                "Beginner",
                "Intermediate",
                "Advanced"
            ]
        )


    # =====================================================
    # RECENT SEARCHES
    # =====================================================

    st.markdown("---")

    st.write("### Recent Searches")

    recent_searches = st.session_state.recent_searches

    if recent_searches:

        for index, search in enumerate(
            recent_searches
        ):

            short_search = search

            if len(short_search) > 45:
                short_search = (
                    short_search[:42] + "..."
                )

            if st.button(
                short_search,
                key=f"recent_{index}",
                use_container_width=True
            ):

                st.session_state.selected_search = search

                st.rerun()

    else:

        st.caption(
            "No recent searches yet."
        )


    # =====================================================
    # CLEAR CHAT
    # =====================================================

    st.markdown("---")

    if st.button(
        "Clear Chat",
        use_container_width=True
    ):

        st.session_state.messages = []

        st.rerun()


# =========================================================
# MAIN TITLE
# =========================================================

if mode == "AI Assistant":

    st.title("Alpha")

    st.caption(
        "Your Personal AI Assistant"
    )

else:

    st.title("Alpha Code Generator")

    st.caption(
        "Generate code using AI"
    )


# =========================================================
# CODE GENERATOR SETTINGS
# =========================================================

if mode == "Code Generator":

    col1, col2 = st.columns(2)

    with col1:

        programming_language = st.selectbox(
            "Language",
            [
                "Python",
                "Java",
                "C",
                "C++",
                "JavaScript"
            ],
            key="main_language"
        )

    with col2:

        difficulty = st.selectbox(
            "Difficulty",
            [
                "Beginner",
                "Intermediate",
                "Advanced"
            ],
            key="main_difficulty"
        )

    st.markdown("")


# =========================================================
# DISPLAY CHAT HISTORY
# =========================================================

for message in st.session_state.messages:

    with st.chat_message(
        message["role"]
    ):

        st.markdown(
            message["content"]
        )


# =========================================================
# SELECTED RECENT SEARCH
# =========================================================

selected_search = st.session_state.pop(
    "selected_search",
    None
)


if selected_search:

    st.info(
        f"Selected recent search: {selected_search}"
    )


# =========================================================
# USER INPUT
# =========================================================

if mode == "AI Assistant":

    placeholder = "Ask Alpha anything..."

else:

    placeholder = (
        "Describe the program you want to create..."
    )


prompt = st.chat_input(
    placeholder
)


# =========================================================
# USE RECENT SEARCH
# =========================================================

if selected_search and not prompt:

    prompt = selected_search


# =========================================================
# PROCESS USER INPUT
# =========================================================

if prompt:

    # -----------------------------------------------------
    # SAVE SEARCH
    # -----------------------------------------------------

    save_recent_search(prompt)

    st.session_state.recent_searches = (
        load_recent_searches()
    )


    # -----------------------------------------------------
    # USER MESSAGE
    # -----------------------------------------------------

    with st.chat_message("user"):

        st.markdown(prompt)


    st.session_state.messages.append(
        {
            "role": "user",
            "content": prompt
        }
    )


    # =====================================================
    # CODE GENERATOR
    # =====================================================

    if mode == "Code Generator":

        code_prompt = f"""
You are an expert software developer.

Generate {programming_language} code based on the user's requirement.

Programming Language:
{programming_language}

Difficulty:
{difficulty}

USER REQUIREMENT:
{prompt}

Instructions:
1. Understand the requirement carefully.
2. Generate correct and runnable code.
3. Follow the selected programming language.
4. Keep the solution appropriate for the selected difficulty.
5. Use good programming practices.
6. Include useful comments where appropriate.
7. Provide the complete code.
8. Return ONLY the code inside ONE Markdown code block.
9. Do NOT write "markdown", "python", "java", or any other language name outside the code block.
10. Do NOT provide explanations before or after the code.
11. Make sure the generated code can be executed directly.
12. For Java, use `public class Main`.
"""

        with st.chat_message("assistant"):
            with st.spinner("Generating code..."):
                response = ollama.chat(
                    model=get_model(),
                    messages=[
                        {
                            "role": "system",
                            "content": code_prompt
                        }
                    ]
                )

                answer = response["message"]["content"]

            generated_code = extract_code(answer)

            st.session_state.generated_code = generated_code
            st.session_state.generated_language = programming_language
            st.session_state.program_output = ""
            st.session_state.program_input = ""

            st.markdown("### Generated Code")
            st.code(generated_code, language=programming_language.lower())

        st.session_state.messages.append(
            {
                "role": "assistant",
                "content": answer
            }
        )


    # =====================================================
    # AI ASSISTANT / RAG
    # =====================================================

    else:

        context = ""

        sources = []


        # -------------------------------------------------
        # RETRIEVE RELEVANT DOCUMENTS
        # -------------------------------------------------

        if st.session_state.vector_db:

            results = (
                st.session_state.vector_db
                .similarity_search(
                    prompt,
                    k=4
                )
            )


            context_parts = []


            for result in results:

                source = result.metadata.get(
                    "source",
                    "Unknown"
                )


                context_parts.append(
                    f"""
SOURCE: {source}

CONTENT:
{result.page_content}
"""
                )


                if source not in sources:

                    sources.append(
                        source
                    )


            context = "\n\n".join(
                context_parts
            )


        # -------------------------------------------------
        # RAG PROMPT
        # -------------------------------------------------

        if context:

            rag_prompt = f"""
{SYSTEM_PROMPT}

Use the following retrieved documents
to answer the user's question.

DOCUMENT CONTEXT:

{context}

USER QUESTION:

{prompt}

Important instructions:

- Prefer information from the documents.
- Do not invent information.
- If the answer is not available in the
  documents, say so clearly.
"""


        else:

            rag_prompt = f"""
{SYSTEM_PROMPT}

USER QUESTION:

{prompt}
"""


        # -------------------------------------------------
        # GENERATE RESPONSE
        # -------------------------------------------------

        with st.chat_message("assistant"):

            with st.spinner(
                "Alpha is thinking..."
            ):

                response = ollama.chat(
                    model=get_model(),
                    messages=[
                        {
                            "role": "system",
                            "content": rag_prompt
                        }
                    ]
                )


                answer = (
                    response["message"]["content"]
                )


           


            # -------------------------------------------------
            # SOURCES
            # -------------------------------------------------

            if sources:

                st.markdown(
                    "**Sources**"
                )

                for source in sources:

                    st.caption(
                        source
                    )


        # -------------------------------------------------
        # SAVE RESPONSE
        # -------------------------------------------------

        st.session_state.messages.append(
            {
                "role": "assistant",
                "content": answer
            }
        )

# =========================================================
## =========================================================
# CODE EXECUTION PANEL
# =========================================================

if mode == "Code Generator" and st.session_state.generated_code:

    st.markdown("---")
    st.markdown("### Run Generated Code")

    st.text_area(
        "Program Input",
        key="program_input",
        height=120,
        placeholder="Example:\n10\n20",
        help="Enter one input value per line, in the same order requested by the program."
    )

    if st.button(
        "Run Code",
        use_container_width=True,
        key="execute_generated_code"
    ):
        with st.spinner("Running code..."):

            st.session_state.program_output = run_code(
                st.session_state.generated_code,
                st.session_state.generated_language,
                st.session_state.program_input
            )

    # -----------------------------------------------------
    # EXECUTION RESULT
    # -----------------------------------------------------

    if st.session_state.program_output:

        st.markdown("### Execution Result")

        col_input, col_output = st.columns(2)

        # INPUT
        with col_input:
            st.markdown("#### Input")

            st.code(
                st.session_state.program_input,
                language="text"
            )

        # OUTPUT
        with col_output:
            st.markdown("#### Output")

            st.code(
    st.session_state.program_output
    .replace("Enter the first number: ", "")
    .replace("Enter the second number: ", "")
    .replace("The sum is: ", "")
    .replace(".0", ""),
    language="text"
)