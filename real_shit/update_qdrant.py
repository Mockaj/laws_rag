import os
import chainlit as cl
from voyageai import Client
from qdrant_client import QdrantClient
from qdrant_client.http.models import Filter, FieldCondition, MatchValue
from qdrant_client.http.models.payload import PayloadSelectorInclude
from typing import Any, List, Optional
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain.prompts import ChatPromptTemplate
from langchain.schema import StrOutputParser
from langchain.schema.runnable import Runnable
from langchain.schema.runnable.config import RunnableConfig

# Ensure your API keys are set in the environment variables
os.environ["OPENAI_API_KEY"] = "your_openai_api_key"
os.environ["ANTHROPIC_API_KEY"] = "your_anthropic_api_key"

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

def remove_duplicates(top_paragraphs):
    seen = set()
    unique_paragraphs = []

    for paragraph in top_paragraphs:
        zneni = paragraph.payload['zneni']
        if zneni not in seen:
            seen.add(zneni)
            unique_paragraphs.append(paragraph)

    return unique_paragraphs

async def query_paragraph_range(client, staleURL, cislo_range, collection_name="legal_paragraphs_updated"):
    extended_paragraphs = []
    for cislo in cislo_range:
        filter_conditions = [
            FieldCondition(key="staleURL", match=MatchValue(value=staleURL)),
            FieldCondition(key="cislo", match=MatchValue(value=cislo))
        ]
        search_result = await client.query_points(
            collection_name=collection_name,
            query_filter=Filter(must=filter_conditions),
            limit=10,
            with_payload=True
        )
        extended_paragraphs.extend(search_result.result)
    return extended_paragraphs

async def query_and_rerank(query_text, collection_name="legal_paragraphs_updated", neighbours_paragraph=2, top_n=100, rerank_top_k=5, qdrant_host="localhost", qdrant_port=6333):
    client = QdrantClient(host=qdrant_host, port=qdrant_port)
    query_embedding = embed(query_text)
    search_result = await client.query_points(
        collection_name=collection_name,
        query=query_embedding,
        limit=top_n,
        query_filter=Filter(must=[FieldCondition(key="isValid", match=MatchValue(value=True))]),
        with_payload=True
    )

    documents = [point.payload["zneni"] for point in search_result.result]
    reranked_results = rerank(query_text, documents, model="rerank-1", top_k=rerank_top_k)
    
    top_paragraphs = [next(point for point in search_result.result if point.payload["zneni"] == result.document) for result in reranked_results]
    
    # Fetch the paragraphs around each found paragraph
    extended_paragraphs = []
    for point in top_paragraphs:
        cislo = int(point.payload["cislo"])
        staleURL = point.payload["staleURL"]
        cislo_range = range(max(1, cislo - 3), cislo + 4)  # Assuming paragraphs start from 1
        extended_paragraphs.extend(await query_paragraph_range(client, staleURL, cislo_range))

    # Remove duplicates from extended paragraphs
    extended_paragraphs = remove_duplicates(extended_paragraphs)
    
    return extended_paragraphs

# Function to run GPT model
async def run_gpt(question: str):
    llm = ChatOpenAI(model="gpt-4o", temperature=0.7)
    messages_query = [
        ("system", """You will get a question from a lawyer in Czech language who needs an answer to his question.
         In order to be able to answer him, you first need to know the relevant paragraphs from
         the relevant laws from Czech law. Your task is to rephrase the query into a question, using which to further
         to find the relevant sections. Always answer a question with a rephrased question only, no additional text!
         As a rule, answer in Czech language only."""),
        ("human", f"QUESTION: {question}"),
    ]
    updated_query = llm.invoke(messages_query).content
    top_paragraphs = await query_and_rerank(updated_query, top_n=50, rerank_top_k=7)
    # Remove duplicates
    top_paragraphs = remove_duplicates(top_paragraphs)
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
    response = llm.invoke(messages_query)
    return response.content, top_paragraphs

@cl.on_message
async def on_message(message: cl.Message):
    original_question = message.content

    # Rephrase the question and fetch relevant paragraphs
    rephrased_question, top_paragraphs = await run_gpt(original_question)

    # Format the response with context
    context_str = "\n\n".join([f"§{p.payload['cislo']}, {p.payload['staleURL'].rsplit('/', 1)[0]}, {p.payload['law_name']}" for p in top_paragraphs])
    response_msg_content = f"Přeformulovaný dotaz: {rephrased_question}\n\n"
    response_msg = cl.Message(content=response_msg_content)
    await response_msg.send()

    # Answer the question using the found paragraphs
    model = ChatOpenAI(model="gpt-4o", temperature=0.0)
    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                """You are a highly qualified lawyer with many years of experience.
                Your task is to answer the following question, to answer which you will be given
                the context of the relevant sections to the question along with its number,
                its wording and the law it is from. For your answer, use primarily the attached
                context. Always properly cite the law and the paragraph number that you used to 
                answer the question.
                
                You must always answer in Czech language only.""",
            ),
            ("human", f"QUESTION: {original_question}\nCONTEXT: {context_str}"),
        ]
    )
    runnable = prompt | model | StrOutputParser()

    # Stream the LLM response
    llm_response_msg = cl.Message(content="")
    await llm_response_msg.send()
    async for chunk in runnable.astream(
        {"question": original_question},
        config=RunnableConfig(callbacks=[cl.LangchainCallbackHandler()]),
    ):
        await llm_response_msg.stream_token(chunk)

    # Stream the relevant paragraphs
    relevant_paragraphs = f"NALEZENÉ RELEVANTNÍ PARAGRAFY:\n{context_str}"
    paragraphs_msg = cl.Message(content=relevant_paragraphs)
    await paragraphs_msg.send()
