# Testing code for Single Document Chat using LLMs (CHATGPT code)

import sys
from pathlib import Path
from langchain_community.vectorstores import FAISS
from src.single_document_chat.data_ingestion import SingleDocIngestor
from src.single_document_chat.retrieval import ConversationalRAG
from utils.model_loader import ModelLoader

# Path to FAISS index folder
FAISS_INDEX_PATH = Path("faiss_index")

def test_conversational_rag_on_pdf(pdf_path: str, question: str):
    try:
        model_loader = ModelLoader()
        embeddings = model_loader.load_embeddings()

        # Define expected FAISS index files
        index_faiss = FAISS_INDEX_PATH / "index.faiss"
        index_pkl = FAISS_INDEX_PATH / "index.pkl"

        # Case 1: Load existing FAISS index if both files are present
        if index_faiss.exists() and index_pkl.exists():
            print("Loading existing FAISS index...")
            vectorstore = FAISS.load_local(
                folder_path=str(FAISS_INDEX_PATH),
                embeddings=embeddings,
                allow_dangerous_deserialization=True
            )
            retriever = vectorstore.as_retriever(
                search_type="similarity", search_kwargs={"k": 5}
            )

        # Case 2: Ingest PDF and create new FAISS index if missing
        else:
            print("FAISS index not found. Ingesting PDF and creating index...")
            with open(pdf_path, "rb") as f:
                uploaded_files = [f]
                ingestor = SingleDocIngestor()
                retriever = ingestor.ingest_files(uploaded_files)
            print(f"FAISS index created and saved at: {FAISS_INDEX_PATH}")

        # Run Conversational RAG
        print("Running Conversational RAG...")
        session_id = "test_conversational_rag"
        rag = ConversationalRAG(retriever=retriever, session_id=session_id)

        response = rag.invoke(question)
        print(f"\nQuestion: {question}\nAnswer: {response}")

    except Exception as e:
        print(f"Test failed: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    # Example PDF path and question
    pdf_path = "data/single_document_chat/NIPS-2017-attention-is-all-you-need-Paper.pdf"
    question = "What is the main topic of the document?"

    # Check PDF existence before proceeding
    if not Path(pdf_path).exists():
        print(f"PDF file does not exist at: {pdf_path}")
        sys.exit(1)

    # Run the test
    test_conversational_rag_on_pdf(pdf_path, question)