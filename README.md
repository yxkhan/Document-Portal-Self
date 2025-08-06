# Project description

## Document Analysis, Chat & Comparison Portal with Advanced RAGx
```
 In this module, you'll dive into building a robust, interactive portal for document analysis and
 intelligent chat using advanced RAG pipelines. You'll learn to ingest and index documents,
 implement semantic search, and create conversational interfaces for both single and multiple
 documents. I have explored optimization with local LLMs, caching strategies, and reranking
 techniques. Additionally full-stack deployment using FastAPI and Streamlit,
 alongside CI/CD and AWS deployment with GitHub Actions and Fargate.
 ```



#### Create a new project folder

```
mkdir <project_folder_name>
```

#### Move into the project folder

```
cd <project_folder_name>
```

#### Open the folder in VS Code

```
code .
```

#### Create a new environment with Python 3.10

```
py -3.10 -m venv env10
```

#### Activate the environment (use full path to the environment)

```
conda activate <path_of_the_env>
```

#### Install dependencies from requirements.txt

```
pip install -r requirements.txt
```

#### Initialize Git

```
git init
```

#### Stage all files

```
git add .
```

#### Commit changes

```
git commit -m "<write your commit message>"
```

#### Push to remote (after adding remote origin)

```
git push
```

#### Cloning the repository

```
git clone https://github.com/yxkhan/document-portal.git
```


#### minimum requirements for the project
1. LLM Model ##groq(freely), openai(paid), gemini, claude, Hugingface

2. Embedding Model #openai, hf, gemini

3. Vector Database ##inmemory, ##ondisk, ##claudebased 