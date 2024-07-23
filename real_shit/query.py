from voyageai import Client
from qdrant_client import QdrantClient
from qdrant_client.http.models import ScoredPoint
from qdrant_client.models import Filter, FieldCondition, MatchValue
from typing import Any, List, Optional
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
import os

DIMENSION = 1024
vo = Client()

def embed(text, input_type="query"):
    try:
        result = vo.embed(text, model="voyage-multilingual-2", input_type=input_type)
        return result.embeddings[0]
    except Exception as e:
        raise

def rerank(query: str, documents: List[str], model: str, top_k: Optional[int] = None, truncation: bool = True):
    try:
        reranking_object = vo.rerank(
            query=query,
            documents=documents,
            model=model,
            top_k=top_k,
            truncation=truncation
        )
        return reranking_object.results
    except Exception as e:
        raise

def query_and_rerank(query_text, collection_name="legal_paragraphs_updated", top_n=100, rerank_top_k=5, qdrant_host="localhost", qdrant_port=6333):
    client = QdrantClient(host=qdrant_host, port=qdrant_port)
    
    try:
        # Embed the query
        query_embedding = embed(query_text)
        
        # Search for the top N most similar paragraphs
        search_result = client.search(
            collection_name=collection_name,
            query_vector=query_embedding,
            limit=top_n,
            query_filter=Filter(must=[
            FieldCondition(key="isValid", match=MatchValue(value=True))
        ])
        )

        # Prepare documents (as texts) for reranking
        documents = [point.payload["zneni"] for point in search_result]
        
        # Rerank the top N paragraphs and get the top K
        reranked_results = rerank(query_text, documents, model="rerank-1", top_k=rerank_top_k)

        # Map reranked results back to the original paragraphs
        top_paragraphs = [next(point for point in search_result if point.payload["zneni"] == result.document) for result in reranked_results]
        
        return top_paragraphs
    
    except Exception as e:
        raise

def run_gpt(question: str):
    llm = ChatOpenAI(model="gpt-4o", temperature=0.7)
    llm = ChatAnthropic(temperature=0.7, model_name="claude-3-5-sonnet-20240620")
    print(f"Původní dotaz: {question}")
    messages_query = [
        ("system", """You will get a question from a lawyer in Czech language who needs an answer to his question.
         In order to be able to answer him, you first need to know the relevant paragraphs from
         the relevant laws from czech law. Your task is to rephrase the query into a question, using which to further
         to find the relevant sections. Always answer a question with a rephrased question only no additional text!
         As a rule, answer in Czech language only."""),
         ("human", f"QUESTION: {question}"),
    ]
    updated_query = llm.invoke(messages_query).content
    print(f"\n\n\nPřeformulovaný dotaz: {updated_query}\n\n\n")

    top_paragraphs = query_and_rerank(updated_query, top_n=50, rerank_top_k=7)
    messages = [
    ("system", """You are a highly qualified lawyer with many years of experience.
     Your task is to answer the following question, to answer which you will be given
     the context of the relevant sections to the question along with its number,
     its wording and the law it is from. For your answer, use primarily the attached
     context. Always properly cite the law and the paragraph number that you used to 
     answer the question.
     
     You must always answer in Czech language only."""),
    ("human", f"""
     QUESTION: {question}
     CONTEXT: {top_paragraphs}
"""),
]
    response = llm.invoke(messages)

    print(response.content)

    print(f"\n\n\nNALEZENÉ RELEVANTNÍ PARAGRAFY:")
    for paragraph in top_paragraphs:
        print(f"§{paragraph.payload['cislo']}, {paragraph.payload['law_name'][:40]}...")
    return response.content

if __name__ == '__main__':
    query1_easy = "Ve kterém zákoně a v jakém paragrafu je upraveno parazitování na pověsti?"  # Replace with your actual query
    query2_easy = "Kolik hodin ročně lze maximálně odpracovat na dohodu o provedení práce? "
    query1_medium = "Jaká práva má společník ve společnosti s ručením omezeným?"
    query2_medium = "Jaký je rozdíl mezi nájmem a pachtem?"
    query1_hard = "Založil jsem si v České republice společnost s ručením omezeným a plánuji prodávat vybavení do domácnosti, zejména do koupelen a kuchyní. Budu prodávat také elektrická zařízení jako světla, žárovky a lampy. Detailně mi popiš, jaké povinnosti musím splnit dle zákona o odpadech a zákona a obalech."
    query2_hard = "Za splnění jakých podmínek nemusím platit daň z příjmu jakožto fyzická osoba při prodeji nemovité věci? Nemovitou věc jsem si zakoupil v dubnu 2022. "
    query3_hard = "Může společník s.r.o. poskytnout své společnosti bezúročnou zápůjčku?"
    query4_hard = "Napiš mi jednotlivé kroky likvidace s.r.o"
    query_random = "Kdy a jak se změnil zákon o obchodních společnostech a družstvech, tak aby společník nově mohl poskytnout bezúročnou zápůjčku své společnosti?"
    query = query4_hard
    
    response = run_gpt(query)
    