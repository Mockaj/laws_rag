import os
import asyncio
import streamlit as st
from embeddings.utils import embed, rerank
from dotenv import load_dotenv
from qdrant_client import QdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchValue
from langchain_openai import ChatOpenAI
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

async def query_and_rerank(query_text, collection_name="legal_paragraphs_updated", neighbours_paragraph=1, top_n=100, rerank_top_k=5):
    client = QdrantClient(url=QDRANT_HOST, api_key=QDRANT_API_KEY)
    query_embedding = await embed(query_text)
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
    reranked_results = await rerank(query_text, documents, model="rerank-1", top_k=rerank_top_k)
    
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
async def run_gpt(question: str, model_name: str, messages: list):
    llm = ChatOpenAI(model=model_name, temperature=0.7)
    # Rephrase the question
    rephrase_prompt = [
        {"role": "system", "content": """You will get a question from a lawyer in Czech language who needs an answer to his question.
In order to be able to answer him, you first need to know the relevant paragraphs from
the relevant laws from Czech law. Your task is to rephrase the query into a question, using which to further
to find the relevant sections. Always answer a question with a rephrased question only, no additional text!
As a rule, answer in Czech language only."""},
        {"role": "user", "content": question}
    ]
    rephrased_question = llm.invoke(rephrase_prompt).content
    
    top_paragraphs, extended_paragraphs = await query_and_rerank(rephrased_question, top_n=50, rerank_top_k=3)
    # Remove duplicates
    top_paragraphs = remove_duplicates(top_paragraphs)
    return rephrased_question, top_paragraphs, extended_paragraphs

# Streamlit app
async def main():
    st.title("Legal Query Assistant")

    # Move model selection to sidebar
    with st.sidebar:
        st.write("Model Selection")
        model_choice = st.radio("Choose the model:", ("gpt-4o", "gpt-4o-mini"))

    st.write("Enter your legal question in Czech:")

    # Initialize chat history
    if "messages" not in st.session_state:
        st.session_state.messages = []

    # Display chat history
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # Accept user input
    if prompt := st.chat_input("What is up?"):
        with st.chat_message("user"):
            st.markdown(prompt)
        st.session_state.messages.append({"role": "user", "content": prompt})

        # Rephrase the question and fetch relevant paragraphs
        rephrased_question, top_paragraphs, extended_paragraphs = await run_gpt(prompt, model_choice, st.session_state.messages)

        # Format the response with context
        context_str = "\n".join([f"""
paragraph
§{p.payload['cislo']}
cislo zakona
{p.payload['staleURL'].rsplit('/', 1)[0]}
jmeno zakona
{p.payload['law_name']}
zneni zakona
{p.payload['zneni']}
---------------------------------
""" for p in top_paragraphs])

        # Prepare the final response including the rephrased question and the answer
        final_response = f"Přeformulovaný dotaz: {rephrased_question}\n\n"

        with st.chat_message("assistant"):
            assistant_placeholder = st.empty()
            assistant_placeholder.markdown("...")

        # Answer the question using the found paragraphs
        model = ChatOpenAI(model=model_choice, temperature=0.6)
        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    """You are a highly qualified lawyer with many years of experience.
                    Your task is to answer the following question, to answer which you will be given
                    the context of the relevant sections to the question along with its number,
                    its wording and the law it is from. For your answer, use exclusively the attached
                    context. Always properly cite the law and the paragraph number that you used to 
                    answer the question. Make sure that the answer includes only the information that is
                    relevant to the question.
                    
                    You must always answer in Czech language only.""",
                ),
                ("human", f"QUESTION: {rephrased_question}\nCONTEXT: {context_str}"),
            ]
        )
        runnable = prompt | model | StrOutputParser()

        # Stream the LLM response
        llm_response = ""
        for chunk in runnable.stream({"question": rephrased_question, "context": context_str}, config=RunnableConfig()):
            llm_response += chunk
            assistant_placeholder.markdown(f"{final_response}\n\n{llm_response}")

        # Combine the final response and the LLM response
        complete_response = f"{final_response}{llm_response}"
        relevant_paragraphs_numbering = []
        for p in top_paragraphs:
            parts = p.payload['staleURL'].split("/")
            numbering = "/".join(parts[-3:-1][::-1])
            relevant_paragraphs_numbering.append(numbering)
        # Append the final response and the relevant paragraphs to the chat history
        relevant_paragraphs_str = "\n\n".join([f"§ {par.payload['cislo']} zákona č. {num} Sb." for (par, num) in zip(top_paragraphs, relevant_paragraphs_numbering)])
        complete_response += f"\n\nNALEZENÉ RELEVANTNÍ PARAGRAFY:\n\n{relevant_paragraphs_str}"
        st.session_state.messages.append({"role": "assistant", "content": complete_response})

        # Update the chat history display
        st.experimental_rerun()

if __name__ == "__main__":
    asyncio.run(main())
