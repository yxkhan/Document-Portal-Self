import os
import sys
from dotenv import load_dotenv
from utils.config_loader import load_config

from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_groq import ChatGroq
#from langchain_openai import ChatOpenAI

from logger.custom_logger import CustomLogger
#from logger import GLOBAL_LOGGER as log
from exception.custom_exception import DocumentPortalException

# Loading the file name for the logger
log = CustomLogger().get_logger(__file__)     #We were passing __file__ to get the current file name for logging, but since we are importing the class from different file, we to use the __name__ to the file name.

class ModelLoader:

    """
    A utility class to load embedding models and LLM models.
    """

    def __init__(self):
        load_dotenv()
        self._validate_env()
        self.config=load_config()
        log.info("Configuration loaded successfully", config_keys=list(self.config.keys())) #saving the log as well showing it on console

    def _validate_env(self):
        """
        Validate necessary environment variables.
        Ensure API keys exist.
        """
        required_keys = ["GOOGLE_API_KEY", "GROQ_API_KEY"]
        self.api_keys={key:os.getenv(key) for key in required_keys} #Iterating through the required keys and getting the values from the environment variables
        missing = [k for k, v in self.api_keys.items() if not v]  #To check if any key is missing
        if missing:
            log.error("Missing environment variables", missing_vars=missing) #If any this is missing, log the error
            raise DocumentPortalException("Missing environment variables", sys) #Raise the exception
        log.info("Environment variables validated", available_keys=[k for k in self.api_keys if self.api_keys[k]]) #if everything fine, log it
        

    def load_embeddings(self):
        """
        Load and return the embedding model.
        """
        try:
            log.info("Loading embedding model...") #To show the message over the console as well as save the log
            model_name = self.config["embedding_model"]["model_name"] #load the model config from the config file
            return GoogleGenerativeAIEmbeddings(model=model_name) #load the actual model
        except Exception as e:
            log.error("Error loading embedding model", error=str(e)) #If any error occurs, log it
            raise DocumentPortalException("Failed to load embedding model", sys) #Raise the exception

    
    def load_llm(self):
        """
        Load and return the LLM model.
        """
        """Load LLM dynamically based on provider in config."""
        
        llm_block = self.config["llm"]

        log.info("Loading LLM...")

        provider_key = os.getenv("LLM_PROVIDER", "google")  # Default google, but you can type SET LLM_PROVIDER=groq(or anything in the Terminal) in the env variable to change the provider
        if provider_key not in llm_block:
            log.error("LLM provider not found in config", provider_key=provider_key)
            raise ValueError(f"Provider '{provider_key}' not found in config")

        llm_config = llm_block[provider_key]
        provider = llm_config.get("provider")
        model_name = llm_config.get("model_name")
        temperature = llm_config.get("temperature", 0.2)
        max_tokens = llm_config.get("max_output_tokens", 2048)
        
        log.info("Loading LLM", provider=provider, model=model_name, temperature=temperature, max_tokens=max_tokens)

        if provider == "google":
            llm=ChatGoogleGenerativeAI(
                model=model_name,
                temperature=temperature,
                max_output_tokens=max_tokens
            )
            return llm

        elif provider == "groq":
            llm=ChatGroq(
                model=model_name,
                api_key=self.api_keys["GROQ_API_KEY"], #type: ignore
                temperature=temperature,
            )
            return llm
            
        # elif provider == "openai":
        #     return ChatOpenAI(
        #         model=model_name,
        #         api_key=self.api_keys["OPENAI_API_KEY"],
        #         temperature=temperature,
        #         max_tokens=max_tokens
        #     )
        else:
            log.error("Unsupported LLM provider", provider=provider)
            raise ValueError(f"Unsupported LLM provider: {provider}")


if __name__ == "__main__":
    loader = ModelLoader()
    
    # Test embedding model loading
    embeddings = loader.load_embeddings()
    print(f"Embedding Model Loaded: {embeddings}")
    
    # Test the ModelLoader
    result=embeddings.embed_query("Hello, how are you?")
    print(f"Embedding Result: {result}")
    
    # Test LLM loading based on YAML config
    llm = loader.load_llm()
    print(f"LLM Loaded: {llm}")
    
    # Test the ModelLoader
    result=llm.invoke("Hello, how are you?")
    print(f"LLM Result: {result.content}")