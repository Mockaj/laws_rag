import os
import streamlit as st
from voyageai import Client
from dotenv import load_dotenv
from qdrant_client import QdrantClient
from qdrant_client.http.models import ScoredPoint
from qdrant_client.models import Filter, FieldCondition, MatchValue
from typing import Any, List, Optional
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain.prompts import ChatPromptTemplate
from langchain.schema import StrOutputParser
from langchain.schema.runnable import Runnable
from langchain.schema.runnable.config import RunnableConfig

load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
LANGCHAIN_API_KEY = os.getenv("LANGCHAIN_API_KEY")
LANGCHAIN_TRACING_V2 = os.getenv("LANGCHAIN_TRACING_V2")
LANGCHAIN_ENDPOINT = os.getenv("LANGCHAIN_ENDPOINT")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY", None)
QDRANT_HOST = os.getenv("QDRANT_HOST", "localhost")
# Initialize VoyageAI Client
vo = Client()

# Embedding function
def embed(text, input_type="query"):
    result = vo.embed(text, model="voyage-multilingual-2", input_type=input_type)
    return result.embeddings[0]

# Reranking function
def rerank(query: str, documents: List[str], model: str, top_k: Optional[int] = None, truncation: bool = True):
    reranking_object = vo.rerank(
        query=query,
        documents=documents,
        model=model,
        top_k=top_k,
        truncation=truncation
    )
    return reranking_object.results

def remove_duplicates(paragraphs):
    seen = set()
    unique_paragraphs = []

    for paragraph in paragraphs:
        zneni = paragraph.payload['zneni']
        if zneni not in seen:
            seen.add(zneni)
            unique_paragraphs.append(paragraph)

    return unique_paragraphs

def query_paragraph_range(client, staleURL, cislo, collection_name="legal_paragraphs_updated"):
    extended_paragraphs = []
    for cislo in range(cislo - 2, cislo + 3):
        scroll_filter = Filter(must=[
            FieldCondition(key="staleURL", match=MatchValue(value=staleURL)),
            FieldCondition(key="cislo", match=MatchValue(value=str(cislo)))
        ])
        offset = None
        while True:
            search_result, offset = client.scroll(
                collection_name=collection_name,
                scroll_filter=scroll_filter,
                with_vectors=False,
                with_payload=True,
                limit=1,
                offset=offset   
            )
            extended_paragraphs.extend(search_result)
            if offset is None:
                break
    return extended_paragraphs

def query_and_rerank(query_text, collection_name="legal_paragraphs_updated", neighbours_paragraph=1, top_n=100, rerank_top_k=5):
    client = QdrantClient(url=QDRANT_HOST, api_key=QDRANT_API_KEY)
    query_embedding = embed(query_text)
    search_result = client.search(
        collection_name=collection_name,
        query_vector=query_embedding,
        limit=top_n,
        query_filter=Filter(must=[
            FieldCondition(key="isValid", match=MatchValue(value=True))
        ]),
        with_payload=True
    )

    documents = [point.payload["zneni"] for point in search_result]
    reranked_results = rerank(query_text, documents, model="rerank-1", top_k=rerank_top_k)
    
    top_paragraphs = [next(point for point in search_result if point.payload["zneni"] == result.document) for result in reranked_results]
    
    # Fetch the paragraphs around each found paragraph
    extended_paragraphs = []
    # for point in top_paragraphs:
    #     cislo = int(point.payload["cislo"])
    #     staleURL = point.payload["staleURL"]
    #     extended_paragraphs.extend(query_paragraph_range(client, staleURL, cislo))

    # # Remove duplicates from extended paragraphs
    # extended_paragraphs = remove_duplicates(extended_paragraphs)
    return top_paragraphs, extended_paragraphs

# Function to run GPT model
def run_gpt(question: str, model_name: str):
    llm = ChatOpenAI(model=model_name, temperature=0.7)
    messages_query = [
        ("system", """You will get a question from a lawyer in Czech language who needs an answer to his question.
         In order to be able to answer him, you first need to know the relevant paragraphs from
         the relevant laws from Czech law. Your task is to rephrase the query into a question, using which to further
         to find the relevant sections. Always answer a question with a rephrased question only, no additional text!
         As a rule, answer in Czech language only."""),
        ("human", f"QUESTION: {question}"),
    ]
    updated_query = llm.invoke(messages_query).content
    top_paragraphs, extended_paragraphs = query_and_rerank(updated_query, top_n=50, rerank_top_k=7)
    # Remove duplicates
    top_paragraphs = remove_duplicates(top_paragraphs)
    return updated_query, top_paragraphs, extended_paragraphs

# Streamlit app
def main():
    st.title("Legal Query Assistant")
    st.write("Enter your legal question in Czech:")
    
    # Model selection
    model_choice = st.radio("Choose the model:", ("gpt-4o", "gpt-4o-mini"))
    
    original_question = st.text_area("Question:")

    if st.button("Submit"):
        if original_question:
            # Rephrase the question and fetch relevant paragraphs
            rephrased_question, top_paragraphs, extended_paragraphs = run_gpt(original_question, model_choice)

            # Format the response with context
            context_str = "\n".join([f"""
                                     
### paragraph
§{p.payload['cislo']}
### cislo zakona
{p.payload['staleURL'].rsplit('/', 1)[0]}
### jmeno zakona
{p.payload['law_name']}
### zneni zakona
{p.payload['zneni']}
---------------------------------
""" for i, p in enumerate(top_paragraphs)])

            st.write(f"Přeformulovaný dotaz: {rephrased_question}")

            # Answer the question using the found paragraphs
            model = ChatOpenAI(model=model_choice, temperature=0.0)
            prompt = ChatPromptTemplate.from_messages(
                [
                    (
                        "system",
                        """You are a highly qualified lawyer with many years of experience.
                        Your task is to answer the following question, to answer which you will be given
                        the context of the relevant sections to the question along with its number,
                        its wording and the law it is from. For your answer, use exclusively the attached
                        context. Always properly cite the law and the paragraph number that you used to 
                        answer the question.
                        
                        You must always answer in Czech language only.""",
                    ),
                    ("human", f"QUESTION: {rephrased_question}\nCONTEXT: {context_str}"),
                ]
            )
            runnable = prompt | model | StrOutputParser()

            # Stream the LLM response
            response_placeholder = st.empty()
            llm_response = ""
            for chunk in runnable.stream({"question": rephrased_question, "context": context_str}, config=RunnableConfig()):
                llm_response += chunk
                response_placeholder.write(llm_response)  # Overwrite with new content

            # Stream the relevant paragraphs found by vector search
            relevant_paragraphs = "\n\n\n".join([f"§{p.payload['cislo']}, {p.payload['staleURL'].rsplit('/', 1)[0]}, {p.payload['law_name']}" for p in top_paragraphs])
            st.write("NALEZENÉ RELEVANTNÍ PARAGRAFY:")
            st.write(relevant_paragraphs)

if __name__ == "__main__":
    main()
