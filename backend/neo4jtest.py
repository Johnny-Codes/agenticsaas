import os
import asyncio
import openai
import fitz  # PyMuPDF
import pymupdf4llm

from langchain_neo4j import Neo4jGraph
from langchain_experimental.graph_transformers import LLMGraphTransformer
from langchain_openai import ChatOpenAI
from langchain_core.documents import Document

from pdf2image import convert_from_path
import pytesseract

openai_api_key = os.getenv("OPENAI_API_KEY")
if not openai_api_key:
    raise ValueError("OPENAI_API_KEY environment variable not set.")
openai.api_key = openai_api_key

os.environ["NEO4J_URI"] = "bolt://neo4j:7687"
os.environ["NEO4J_USERNAME"] = "neo4j"
os.environ["NEO4J_PASSWORD"] = "testpassword"

graph = Neo4jGraph(refresh_schema=False)

llm = ChatOpenAI(
    temperature=0,
    model_name="gpt-4.1",  # Or your preferred model
)
llm_transformer = LLMGraphTransformer(llm=llm)


def extract_text_from_pdf(pdf_path):
    doc = pymupdf4llm.to_markdown(pdf_path)
    return doc


def extract_text_with_ocr(pdf_path):
    pages = convert_from_path(pdf_path)
    text = ""
    for page in pages:
        text += pytesseract.image_to_string(page)
    return text


async def main():
    pdf_path = "036_ISA_Project_Air_Traffic_Requirements.pdf"
    md_text = extract_text_from_pdf(pdf_path)
    ocr_text = extract_text_with_ocr(pdf_path)

    PROMPT = """
You are an expert Requirements Engineer, trained in NASA's guidelines for writing good requirements (see Appendix C: "How to Write a Good Requirement—Checklist"). Your task is to analyze the provided document and:

1. **Rewrite every requirement** you find so that it is a properly written requirement according to NASA's guidelines. Each requirement must be clear, complete, verifiable, and use the correct structure: <Entity> <shall/will/should> <action/condition/constraint>. Use "shall" for mandatory requirements, "will" for statements of fact, and "should" for goals or recommendations.

2. **Organize the requirements into a hierarchy of entities**:
    - The top-level entity is the main system (e.g., "Transport Modelling System").
    - If an entity is composed of sub-entities (e.g., subsystems, components, modules), show this hierarchy.
    - Each entity and sub-entity should have its requirements directly connected to its node.
    - All entities must ultimately connect back to the main system, unless there is a clear reason for an entity to be isolated.

3. **Output Format:**
    - For each entity, list:
        - The entity name.
        - Its parent entity (if any).
        - A list of requirements for that entity, each in the form: <Entity> <shall/will/should> <requirement text>.
    - Show the hierarchy as a list or tree, and ensure every requirement is attached to the correct entity.

**Example Output:**
Main System: Transport Modelling System
  - Requirement: Transport Modelling System shall provide a user interface for scenario selection.
  - Sub-Entity: User Interface
      - Requirement: User Interface shall allow the user to select a scenario.
      - Requirement: User Interface shall display error messages for invalid input.
  - Sub-Entity: Data Management
      - Requirement: Data Management shall store simulation results for at least 10 years.

**Important:**
- Rewrite requirements to be clear, concise, and verifiable, following NASA's checklist.
- Do not omit any requirements from the document.
- Ensure all entities are connected in the hierarchy, with requirements attached at the correct level.
- Use as many layers of entities as needed to reflect the document's structure.

1. OCR extraction (may contain errors or missing formatting)
2. Markdown extraction (may miss some text, but preserves structure)
    Your task:
    - Carefully compare both versions.
    - Merge them to produce a complete, accurate, and well-structured set of requirements.
    - Rewrite every requirement according to NASA's guidelines: <Entity> <shall/will/should> <requirement>.
    - Organize requirements into a hierarchy of entities, as previously described.
"""

    response = openai.chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "system",
                "content": "You are an expert Requirements Engineer, trained in NASA's guidelines for writing good requirements. Your task is to analyze the provided document and",
            },
            {
                "role": "user",
                "content": PROMPT
                + f"OCR extraction (may contain errors or missing formatting) {ocr_text}"
                + f"Markdown extraction (may miss some text, but preserves structure) {md_text}",
            },
        ],
        temperature=0,
    )
    output = response.choices[0].message.content
    print("GPT Output:\n", output)

    documents = [Document(page_content=output)]
    graph_documents = await llm_transformer.aconvert_to_graph_documents(documents)
    print(f"Nodes: {graph_documents[0].nodes}")
    print(f"Relationships: {graph_documents[0].relationships}")

    graph.add_graph_documents(graph_documents)
    print("Graph documents added to Neo4j.")

    # Extract both versions
    # ocr_text = extract_text_with_ocr(pdf_path)
    # md_text = extract_text_from_pdf(pdf_path)

    # # Combine for reconciliation
    # combined_prompt = f"""
    # You are an expert Requirements Engineer. You have two versions of extracted requirements from the same document:
    # 1. OCR extraction (may contain errors or missing formatting)
    # 2. Markdown extraction (may miss some text, but preserves structure)

    # Your task:
    # - Carefully compare both versions.
    # - Merge them to produce a complete, accurate, and well-structured set of requirements.
    # - Rewrite every requirement according to NASA's guidelines: <Entity> <shall/will/should> <requirement>.
    # - Organize requirements into a hierarchy of entities, as previously described.

    # OCR Extraction:
    # {ocr_text}

    # Markdown Extraction:
    # {md_text}
    # """

    # response = openai.chat.completions.create(
    #     model="gpt-4o",
    #     messages=[
    #         {"role": "system", "content": "You are a helpful assistant."},
    #         {"role": "user", "content": combined_prompt},
    #     ],
    #     temperature=0,
    # )
    # output = response.choices[0].message.content
    # print("GPT Output:\n", output)

    # documents = [Document(page_content=output)]
    # graph_documents = await llm_transformer.aconvert_to_graph_documents(documents)
    # print(f"Nodes: {graph_documents[0].nodes}")
    # print(f"Relationships: {graph_documents[0].relationships}")

    # graph.add_graph_documents(graph_documents)
    # print("Graph documents added to Neo4j.")


if __name__ == "__main__":
    asyncio.run(main())
