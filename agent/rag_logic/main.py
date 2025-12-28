import dotenv
from .data_loader import load_all_documents_from_directory, split_text
from .vector_store import create_vector_store

# load google api key for LLM use
def load_environment_variables():
    dotenv.load_dotenv()
    print("Environment variables loaded.") #to test for now

SOURCE_DIRECTORY = "./docs"

if __name__ == '__main__':
    load_environment_variables()
    documents = load_all_documents_from_directory(SOURCE_DIRECTORY)

    if not documents:
        print(f"No documents found in {SOURCE_DIRECTORY}.")
    else: #chunk and save to vector store
        print(f"Loaded {len(documents)} raw documents.")
        split_doc = split_text(documents)
        print(f"Split into {len(split_doc)} chunks.")
        create_vector_store(split_doc)
        print("Vector store successfully created and persisted to disk!")
