import os
import asyncio
import openai
import fitz  # PyMuPDF

from langchain_neo4j import Neo4jGraph
from langchain_experimental.graph_transformers import LLMGraphTransformer
from langchain_openai import ChatOpenAI
from langchain_core.documents import Document

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

PROMPT = """
You are an expert Requirements Engineer and Knowledge Graph specialist, meticulously trained on the principles of good requirements as outlined in NASA's guidelines (specifically Appendix C: "How to Write a Good Requirement— Checklist"). Your task is to extract a comprehensive, *fully interconnected* knowledge graph from the provided PDF document, which contains software/system requirements.

**Understanding "Good Requirements" (Reference: NASA Appendix C Applied Generically):**
* **Normative Statements:** Identify explicit statements that define system behavior, characteristics, or constraints. Look for keywords like "shall" (definitive requirement), "will" (fact or declaration of purpose), and "should" (goal or objective).
* **Clear Subject & Predicate:** Requirements typically describe *who/what* (subject) *shall/will/should* (predicate) *do something*.
* **What vs. How:** Requirements state *WHAT* is needed, not *HOW* it should be implemented, nor do they typically assign personnel tasks.
* **Attributes of Goodness:** Evaluate extracted elements for clarity, conciseness, completeness, consistency, traceability, correctness, and verifiability, and reflect these where possible in descriptions or relationships.

**Objective:**
Construct a comprehensive and *interconnected* knowledge graph from the requirements specified in the PDF. Every identified entity (requirements, system components, actors, functionalities, constraints, data, etc.) must be related to at least one other entity, ultimately forming chains that link back to the core system, its mission, or other fundamental components. The graph should represent **all explicit and reasonably inferred relationships and requirement chains**.

**Output Format:**
Represent the knowledge graph as:
1.  A list of **Knowledge Graph Triples** `(Subject_Name, Predicate_Phrase, Object_Name_or_Value)`
2.  A list of **Entities** with their types and descriptions.

**1. Knowledge Graph Triples Format:**
Each triple must strictly follow the format: `(Subject_Name, Predicate_Phrase, Object_Name_or_Value)`.
* **Subject_Name:** The `name` of an extracted entity (e.g., "User Authentication Module", "SR-001").
* **Predicate_Phrase:** A concise, active phrase describing the relationship between the Subject and Object. Use precise verbs.
* **Object_Name_or_Value:** The `name` of another extracted entity, or a direct value (e.g., a quoted requirement text, a quantitative value like "100 ms").

**Key Predicates (Prioritize these, infer others as appropriate):**
* `specifies` / `defines` / `describes` (e.g., Document specifies System, Feature describes Functionality)
* `textually states` (for linking an entity to its verbatim requirement, fact, or goal text)
* `is composed of` / `includes` / `contains` (for hierarchical structures)
* `has capability` / `provides capability` (e.g., System has capability User Authentication)
* `implements` / `supports` (e.g., Component implements Feature, System supports Service)
* `is performed by` / `interacts with` (e.g., Feature is performed by Actor, System interacts with Interface)
* `requires` / `depends on` (e.g., Feature requires DataElement, Requirement depends on Requirement)
* `has property` / `has characteristic` (e.g., System has property Mass, Data has characteristic Format)
* `has constraint` / `is subject to` (e.g., Requirement has constraint Performance, System is subject to Security)
* `has metric` / `measures` (e.g., Performance has metric Response Time)
* `has value` / `is estimated at` (for quantitative data, e.g., Response Time has value "100 ms", Bandwidth is estimated at "64 Kbps")
* `is traceable to` / `derived from` (for hierarchical traceability)
* `governs` (e.g., Business Rule governs Requirement)
* `relates to` (general catch-all, use more specific predicates first)

**2. Entity Format:**
Each unique entity identified should be represented as a JSON object:
```json
{
  "name": "Entity Name",
  "type": "EntityType",
  "description": "Brief description of the entity as derived from the document."
}
"""


def extract_text_from_pdf(pdf_path):
    doc = fitz.open(pdf_path)
    text = ""
    for page in doc:
        text += page.get_text()
    return text


async def main():
    pdf_path = "010_Transport_Modelling_System_User_Requirements.pdf"  # <-- Change this to your PDF path
    pdf_text = extract_text_from_pdf(pdf_path)

    # Send prompt + PDF text to OpenAI (text-only, for GPT-4o/4 Vision see OpenAI docs)
    user_content = PROMPT + "\n\n" + pdf_text

    response = openai.chat.completions.create(
        model="gpt-4o",  # Use "gpt-4-vision-preview" if you want vision support
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": user_content},
        ],
        temperature=0,
    )
    output = response.choices[0].message.content
    print("GPT Output:\n", output)

    # Optionally, parse output and convert to Document(s) for LangChain
    documents = [Document(page_content=output)]

    # Generate graph documents and add to Neo4j
    graph_documents = await llm_transformer.aconvert_to_graph_documents(documents)
    print(f"Nodes: {graph_documents[0].nodes}")
    print(f"Relationships: {graph_documents[0].relationships}")

    graph.add_graph_documents(graph_documents)
    print("Graph documents added to Neo4j.")


if __name__ == "__main__":
    asyncio.run(main())
