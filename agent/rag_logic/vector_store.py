import os
try:
    import chromadb
    from chromadb.config import Settings
    from chromadb.utils import embedding_functions
except Exception:
    chromadb = None
    Settings = None
    embedding_functions = None
from .data_loader import create_embedding_function, split_text, load_text, load_pdf, load_docx, load_site


class SimpleRetriever:
    def __init__(self, collection, embedding_function, k=4):
        # collection: chromadb collection or in-memory collection
        self.collection = collection
        # embedding_function: a callable/factory that returns an embedder instance
        self.embedding_function = embedding_function
        self.k = k

    def get_relevant_documents(self, query):
        # embedding_function may be a factory (callable) or an instance with embed/embed_query
        ef = self.embedding_function
        embedder = ef() if callable(ef) and not hasattr(ef, 'embed') else ef
        if hasattr(embedder, 'embed_query'):
            emb = embedder.embed_query(query)
        else:
            emb = embedder.embed([query])[0]
        results = self.collection.query(query_embeddings=[emb], n_results=self.k)
        docs = []
        for doc in results['documents'][0]:
            class SimpleDoc:
                def __init__(self, text):
                    self.page_content = text
            docs.append(SimpleDoc(doc))
        return docs


def create_vector_store(documents, persist_directory="vector_store"):
    # build chroma client with local persistence if available
    if chromadb is None:
        # Provide minimal in-memory collection as fallback
        class InMemoryCollection:
            def __init__(self):
                self._docs = []

            def add(self, ids, documents):
                for i, doc in enumerate(documents):
                    self._docs.append((ids[i], doc))

            @property
            def client(self):
                return self

            def query(self, query_embeddings=None, n_results=4):
                # naive retrieval: return first n_results documents
                docs = [d for (_id, d) in self._docs][:n_results]
                return {"documents": [docs]}

        collection = InMemoryCollection()
    else:
        # By default reuse an existing persistent store so once a vector store is
        # created it will be used. If you explicitly want to force recreation during
        # tests, set the environment variable FORCE_RECREATE_VECTORSTORE=1.
        import shutil
        if os.getenv('FORCE_RECREATE_VECTORSTORE') == '1' and os.path.exists(persist_directory):
            try:
                shutil.rmtree(persist_directory)
            except Exception:
                # If removal fails, proceed and let chromadb raise a clearer error
                pass
        client = chromadb.PersistentClient(path=persist_directory)
        collection = client.get_or_create_collection(name="study_assistant")

    # get embedding function callable or instance that accepts texts
    embed_fn = create_embedding_function()
    # normalize to an embedder instance with .embed / .embed_query
    embedder = embed_fn() if callable(embed_fn) and not hasattr(embed_fn, 'embed') else embed_fn

    # add docs (compute embeddings to ensure collection dimension matches)
    texts = [getattr(d, 'page_content', str(d)) for d in documents]
    ids = [f"doc_{i}" for i in range(len(texts))]
    try:
        embeddings = embedder.embed(texts)
    except Exception:
        # fallback: compute per-item embed_query if embed isn't available
        embeddings = [embedder.embed_query(t) if hasattr(embedder, 'embed_query') else embedder.embed([t])[0] for t in texts]

    collection.add(ids=ids, documents=texts, embeddings=embeddings)
    return collection


def create_retriever(collection, embedding_function_factory, search_kwargs={"k": 4}):
    """Create a SimpleRetriever using an embedding factory (callable that returns an embedder instance).

    The SimpleRetriever expects an embedding factory so it can create fresh embedders when needed.
    """
    return SimpleRetriever(collection, embedding_function_factory, k=search_kwargs.get('k', 4))


def get_retriever(persist_directory="vector_store", embedding_function=None):
    # embedding_function may be either an embedding factory (callable) or None
    if embedding_function is None:
        embedding_function = create_embedding_function

    if os.path.exists(persist_directory):
        client = chromadb.PersistentClient(path=persist_directory)
        collection = client.get_or_create_collection(name="study_assistant")
    else:
        raise FileNotFoundError(f"Vector store not found at {persist_directory}. Please create the vector store first.")

    return create_retriever(collection, embedding_function)
