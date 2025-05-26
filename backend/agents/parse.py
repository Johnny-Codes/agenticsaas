from typing import List

from pydantic import BaseModel
from pydantic_ai.models.openai import OpenAIModel
from pydantic_ai.providers.openai import OpenAIProvider
from pydantic_ai import Agent as PydanticAgent

provider = OpenAIProvider(base_url="http://host.docker.internal:11434/v1")
ollama_model = OpenAIModel(model_name="llama3.2:latest", provider=provider)


class PDFData(BaseModel):
    title: str
    authors: List[str]


pdf_metadata_agent = PydanticAgent(
    ollama_model,
    system_prompt=(
        "You are a master document searcher. Extract the title and authors of the document. "
        "Fix any formatting issues in the title (e.g., remove extra spaces, convert to title case, etc.). "
        "Fix any formatting issues in the authors (e.g., remove extra spaces, convert to title case, remove brackets, etc.). "
        "Your response must be a JSON object with the following format: "
        '{"title": "<title>", "authors": ["<author1>", "<author2>", ...]}. '
        "Do not include any additional text or explanation."
    ),
    output_type=PDFData,
)
