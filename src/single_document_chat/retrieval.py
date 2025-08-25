# import uuid
# from pathlib import Path
# import sys
# from datetime import datetime, timezone
# from langchain_community.document_loaders import PyPDFLoader
# from langchain_text_splitters import RecursiveCharacterTextSplitter
# from langchain_community.vectorstores import FAISS
# from logger.custom_logger import CustomLogger
# from exception.custom_exception import DocumentPortalException
# from utils.model_loader import ModelLoader


# class SingleDocIngestor:
#     def __init__(self,data_dir: str = "data/single_document_chat", faiss_dir : str = "faiss_index"):
#         try:
#             self.log = CustomLogger().get_logger(__name__)
#             self.data_dir = Path (data_dir)
#             self.data_dir.mkdir(parents=True, exist_ok=True)

#             self.faiss_dir = Path (faiss_dir)
#             self.faiss_dir.mkdir(parents=True, exist_ok=True)

#             self.model_loader = ModelLoader()

#             self.log.info("SingleDocIngestor initialized successfully", temp_path=str(self.data_dir), faiss_path=str(self.faiss_dir))

#         except Exception as e:
#             self.log.error("Failed to initialize SingleDocIngestor", error=str(e))
#             raise DocumentPortalException("Initialization error in SingleDocIngestor", sys)
        
#     def ingest_files(self,uploaded_files):
#         try:
#             documents= []
#             for uploaded_file in uploaded_files:
#                 unique_filename = f"session_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}.pdf"
#                 temp_path = self.data_dir / unique_filename

#                 with open(temp_path, "wb") as f:
#                     f.write(uploaded_file.read())
#                 self.log.info("File saved successfully", filename=unique_filename)
#                 loader = PyPDFLoader(str(temp_path))
#                 docs = loader.load()
#                 documents.extend(docs)
#             self.log.info("Pdf files loaded successfully", count=len(documents))
#             return self._create_retriever(documents)

#         except Exception as e:
#             self.log.error("Document ingestion failed", error=str(e))
#             raise DocumentPortalException("Error during file ingestion", sys)
        
#     def _create_retriever(self):
#         try:
#             splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=300)
#             chunks = splitter.split_documents(documents)
#             self.log.info("Documents split into chunks", chunk_count=len(chunks))

#             embeddings = self.model_loader.load_embeddings()
#             vectorstore = FAISS.from_documents(documents=chunks, embedding=embeddings)

#             #Save Faiss index
#             vectorstore.save_local(str(self.faiss_dir))
#             self.log.info("FAISS index created and saved", faiss_path=str(self.faiss_dir))

#             retriver = vectorstore.as_retriever(search_type= "similarity" ,search_kwargs={"k":3})
#             self.log.info("Retriever created from FAISS index", retriever_type=str(type(retriver)))
#             return retriver

#         except Exception as e:
#             self.log.error("Retriever creation failed", error=str(e))
#             raise DocumentPortalException("Error creating FAISS retriever", sys)


import sys
import os
import streamlit as st
from dotenv import load_dotenv
from langchain_core.chat_history import BaseChatMessageHistory
from langchain_community.chat_message_histories import ChatMessageHistory
from prompt.prompt_library import PROMPT_REGISTRY
from model.models import PromptType
from logger.custom_logger import CustomLogger
from exception.custom_exception import DocumentPortalException
from utils.model_loader import ModelLoader
from langchain_core.runnables import RunnableWithMessageHistory
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain.chains import create_retrieval_chain, create_history_aware_retriever

load_dotenv()

class ConversationalRAG:
    def __init__(self, session_id: str, retriever):
        self.log = CustomLogger().get_logger(__name__)
        self.session_id = session_id
        self.retriever = retriever

        try:
            self.llm = self._load_llm()
            self.contextualize_prompt = PROMPT_REGISTRY[PromptType.CONTEXTUALIZE_QUESTION.value]
            self.qa_prompt = PROMPT_REGISTRY[PromptType.CONTEXT_QA.value]

            #this is to persist the memory of the chat/RAG
            self.history_aware_retriever = create_history_aware_retriever(
                self.llm, self.retriever, self.contextualize_prompt
            )
            self.log.info("Created history-aware retriever", session_id=session_id)

            #This is raw of creating chain instead of using LCEL            
            self.qa_chain = create_stuff_documents_chain(self.llm, self.qa_prompt)
            self.rag_chain = create_retrieval_chain(self.history_aware_retriever, self.qa_chain)
            self.log.info("Created RAG chain", session_id=session_id)

            self.chain = RunnableWithMessageHistory(
                self.rag_chain,
                self._get_session_history,      #this is for streamlit ui, will be used there
                input_messages_key="input",
                history_messages_key="chat_history",
                output_messages_key="answer"
            )
            self.log.info("Wrapped chain with message history", session_id=session_id)

        except Exception as e:
            self.log.error("Error initializing ConversationalRAG", error=str(e), session_id=session_id)
            raise DocumentPortalException("Failed to initialize ConversationalRAG", sys)
        
    

    def _load_llm(self):
        try:
            
            llm = ModelLoader().load_llm()
            self.log.info("LLM loaded successfully", class_name=llm.__class__.__name__)
            return llm
        except Exception as e:
            self.log.error("Error loading LLM via ModelLoader", error=str(e))
            raise DocumentPortalException("Failed to load LLM", sys)
        


    def _get_session_history(self, session_id: str) -> BaseChatMessageHistory:
        try:
            
            if "store" not in st.session_state:
                st.session_state.store = {}

            if session_id not in st.session_state.store:
                st.session_state.store[session_id] = ChatMessageHistory()
                self.log.info("New chat session history created", session_id=session_id)

            return st.session_state.store[session_id]
        except Exception as e:
            self.log.error("Failed to access session history", session_id=session_id, error=str(e))
            raise DocumentPortalException("Failed to retrieve session history", sys)
        


    def load_retriever_from_faiss(self, index_path: str):
        try:
            
        
            embeddings = ModelLoader().load_embeddings()
            if not os.path.isdir(index_path):
                raise FileNotFoundError(f"FAISS index directory not found: {index_path}")

            vectorstore = FAISS.load_local(index_path, embeddings)
            self.log.info("Loaded retriever from FAISS index", index_path=index_path)
            return vectorstore.as_retriever(search_type="similarity", search_kwargs={"k": 5})

        except Exception as e:
            self.log.error("Failed to load retriever from FAISS", error=str(e))
            raise DocumentPortalException("Error loading retriever from FAISS", sys)



    def invoke(self, user_input: str) -> str:
        try:
            pass
            response = self.chain.invoke(
                {"input": user_input},
                config={"configurable": {"session_id": self.session_id}} #This configuration is memory as per sunny
            )
            answer = response.get("answer", "No answer.")

            if not answer:
                self.log.warning("Empty answer received", session_id=self.session_id)

            self.log.info("Chain invoked successfully", session_id=self.session_id, user_input=user_input, answer_preview=answer[:150])
            return answer

        except Exception as e:
            self.log.error("Failed to invoke conversational RAG", error=str(e), session_id=self.session_id)
            raise DocumentPortalException("Failed to invoke RAG chain", sys)