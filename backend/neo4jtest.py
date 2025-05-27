import os
import asyncio  # Import asyncio

from langchain_neo4j import Neo4jGraph
from langchain_experimental.graph_transformers import LLMGraphTransformer
from langchain_openai import ChatOpenAI
from langchain_core.documents import Document

# docs https://python.langchain.com/docs/how_to/graph_constructing/#llm-graph-transformer

openai_api_key = os.getenv("OPENAI_API_KEY")
if not openai_api_key:
    raise ValueError("OPENAI_API_KEY environment variable not set.")

os.environ["NEO4J_URI"] = "bolt://neo4j:7687"
os.environ["NEO4J_USERNAME"] = "neo4j"
os.environ["NEO4J_PASSWORD"] = "testpassword"

graph = Neo4jGraph(refresh_schema=False)

llm = ChatOpenAI(
    temperature=0, model_name="gpt-4.1"
)  # Assuming you meant gpt-4 or similar, adjust if needed
llm_transformer = LLMGraphTransformer(llm=llm)


async def main():  # Define an async function
    text = """
Marie Curie, born in 1867, was a Polish and naturalised-French physicist and chemist who conducted pioneering research on radioactivity.
She was the first woman to win a Nobel Prize, the first person to win a Nobel Prize twice, and the only person to win a Nobel Prize in two scientific fields.
Her husband, Pierre Curie, was a co-winner of her first Nobel Prize, making them the first-ever married couple to win the Nobel Prize and launching the Curie family legacy of five Nobel Prizes.
She was, in 1906, the first woman to become a professor at the University of Paris.
"""
    documents = [Document(page_content=text)]
    graph_documents = await llm_transformer.aconvert_to_graph_documents(documents)
    print(f"Nodes:{graph_documents[0].nodes}")
    print(f"Relationships:{graph_documents[0].relationships}")

    # Add the graph documents to Neo4j
    graph.add_graph_documents(graph_documents)
    print("Graph documents added to Neo4j.")

    asyncio.run(main())  # Run the async functionif __name__ == "__main__":


if __name__ == "__main__":
    asyncio.run(main())  # Run the async function
