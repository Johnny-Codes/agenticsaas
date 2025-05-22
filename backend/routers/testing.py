import os
from fastapi import APIRouter


router = APIRouter(
    prefix="/testing",
    tags=["Testing"],
)

testing_agent_prompt = (
    "You are a requirements engineer expert. Extract all requirements from the document and return a list of strings. Do not include any additional text or explanation but you can reformat the text to make it readable.",
)


@router.post("/test/")
def test():
    # Read the actual PDF text (or any text file) instead of passing the file path
    file_path = "./uploads/routputchunks.txt"
    if not os.path.exists(file_path):
        return {"error": f"File not found: {file_path}"}
    with open(file_path, "r", encoding="utf-8") as f:
        document_text = f.read()

    testing_agent = Agent(
        model=phi_model,
        system_prompt=testing_agent_prompt,
    )
    requirements = phi_agent.run_sync(document_text)
    return {"requirements": requirements}
