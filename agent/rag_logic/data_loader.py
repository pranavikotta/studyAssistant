import os

try:
    # Import loaders lazily to avoid static resolution errors
    from langchain_community.document_loaders import TextLoader, PyPDFLoader, Doc2txtLoader, WebBaseLoader
except Exception as e:
    print(f"Warning: Could not import from langchain_community: {e}")
    TextLoader = PyPDFLoader = Doc2txtLoader = WebBaseLoader = None

# Fallback: try to import PyPDFLoader from pypdf directly
if PyPDFLoader is None:
    try:
        from langchain.document_loaders import PyPDFLoader
        print("Successfully imported PyPDFLoader from langchain.document_loaders")
    except Exception as e:
        print(f"Warning: Could not import PyPDFLoader from langchain: {e}")
        PyPDFLoader = None

import importlib
# Try modern splitters package first (separate package), then fall back to langchain's older path
RecursiveCharacterTextSplitter = None
try:
    mod = importlib.import_module('langchain_text_splitters')
    RecursiveCharacterTextSplitter = getattr(mod, 'RecursiveCharacterTextSplitter')
except Exception:
    try:
        langchain_text_splitter = importlib.import_module('langchain.text_splitter')
        RecursiveCharacterTextSplitter = getattr(langchain_text_splitter, 'RecursiveCharacterTextSplitter')
    except Exception:
        RecursiveCharacterTextSplitter = None
try:
    from langchain_community.embeddings import HuggingFaceBgeEmbeddings
except Exception:
    HuggingFaceBgeEmbeddings = None

try:
    # langchain's standard huggingface wrapper
    from langchain.embeddings import HuggingFaceEmbeddings
except Exception:
    HuggingFaceEmbeddings = None

# loader for plain text
def load_text(file_path):
    if TextLoader is None:
        # fallback: read raw text and wrap in a minimal Document-like object
        class SimpleDoc:
            def __init__(self, text):
                self.page_content = text
                self.metadata = {}

        with open(file_path, 'r', encoding='utf-8') as f:
            text = f.read()
        return [SimpleDoc(text)]
    loader = TextLoader(file_path)
    return loader.load()
# loader for pdfs
def load_pdf(file_path):
    if PyPDFLoader is None:
        # Fallback: use pypdf directly
        try:
            from pypdf import PdfReader
            
            class SimpleDoc:
                def __init__(self, text, page_num):
                    self.page_content = text
                    self.metadata = {'page': page_num, 'source': file_path}
            
            reader = PdfReader(file_path)
            documents = []
            for i, page in enumerate(reader.pages):
                text = page.extract_text()
                if text.strip():  # Only add pages with content
                    documents.append(SimpleDoc(text, i))
            
            print(f"Loaded {len(documents)} pages from PDF using pypdf directly")
            return documents
        except Exception as e:
            raise RuntimeError(f"Could not load PDF. PyPDFLoader not available and pypdf fallback failed: {e}")
    
    loader = PyPDFLoader(file_path)
    return loader.load()
# loader for docx files
def load_docx(file_path):
    if Doc2txtLoader is None:
        raise RuntimeError("Doc2txtLoader (langchain_community) not available")
    loader = Doc2txtLoader(file_path)
    return loader.load()
# loader for web pages
def load_site(url):
    if WebBaseLoader is None:
        raise RuntimeError("WebBaseLoader (langchain_community) not available")
    loader = WebBaseLoader(url)
    return loader.load()
    
def load_all_documents_from_directory(source_dir):
    all_documents = []   
    # check if the directory exists
    if not os.path.isdir(source_dir):
        raise FileNotFoundError(f"Source directory not found: {source_dir}")
    # go through the directory and subdirectories
    for root, _, files in os.walk(source_dir):
        for file in files:
            file_path = os.path.join(root, file)
            # skip common hidden/temp files
            if file.startswith('.') or file.endswith('~'):
                continue     
            try:
                if file_path.endswith('.txt'):
                    documents = load_text(file_path)
                elif file_path.endswith('.pdf'):
                    documents = load_pdf(file_path)
                elif file_path.endswith('.docx') or file_path.endswith('.doc'):
                    documents = load_docx(file_path)
                elif file_path.startswith('http://') or file_path.startswith('https://'):
                    documents = load_site(file_path)
                else:
                    raise ValueError(f"Unsupported file type or URL: {file_path}")
                all_documents.extend(documents) #extend since its a load functions return list of document objects
            except ValueError as e:
                # Catch the unsupported file type error gracefully
                print(f"Skipping file {file_path}: {e}")
            except Exception as e:
                # Catch other potential loading errors (e.g., corrupted file)
                print(f"Error loading file {file_path}: {e}")
    return all_documents

# text splitter
def split_text(documents, chunk_size=1000, chunk_overlap=200):
    # If langchain's splitter isn't available, use a simple fallback that splits by characters
    if RecursiveCharacterTextSplitter is None:
        chunks = []
        for doc in documents:
            text = getattr(doc, 'page_content', str(doc))
            start = 0
            while start < len(text):
                end = min(start + chunk_size, len(text))
                chunk_text = text[start:end]
                # Create a minimal document-like object
                class SimpleDoc:
                    def __init__(self, text):
                        self.page_content = text
                        self.metadata = {}
                chunks.append(SimpleDoc(chunk_text))
                start = end - chunk_overlap if end < len(text) else end
        return chunks

    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        length_function=len,
    )
    return text_splitter.split_documents(documents)

# configure model and embedding function
model_name = os.getenv("EMBEDDING_MODEL", "BAAI/bge-base-en-v1.5")
model_kwargs = {'device': 'cpu'}
encode_kwargs = {'normalize_embeddings': True}


def create_embedding_function():
    """Return an embeddings instance. Falls back from HuggingFaceBgeEmbeddings to HuggingFaceEmbeddings when BGE is unavailable.
    """
    # Use production-grade embedding model
    model = os.getenv("EMBEDDING_MODEL", model_name)
    if HuggingFaceBgeEmbeddings is not None and "bge" in model.lower():
        return HuggingFaceBgeEmbeddings(model_name=model, model_kwargs=model_kwargs, encode_kwargs=encode_kwargs)
    # fallback to HuggingFaceEmbeddings if available
    if HuggingFaceEmbeddings is not None:
        return HuggingFaceEmbeddings(model_name=model)
    # last resort: error out with helpful message
    raise RuntimeError("No suitable embeddings class available. Install langchain (with huggingface support) or langchain-community with BGE embeddings.")
