from mcp.server.fastmcp import FastMCP

mcp = FastMCP("DocumentMCP", log_level="ERROR")


docs = {
    "deposition.md": "This deposition covers the testimony of Angela Smith, P.E.",
    "report.pdf": "The report details the state of a 20m condenser tower.",
    "financials.docx": "These financials outline the project's budget and expenditures.",
    "outlook.pdf": "This document presents the projected future performance of the system.",
    "plan.md": "The plan outlines the steps for the project's implementation.",
    "spec.txt": "These specifications define the technical requirements for the equipment.",
}

@mcp.tool()
def read_doc(doc_id: str) -> str:
    """Read the content of a document by its ID."""
    if doc_id not in docs:
        return f"Error: document '{doc_id}' not found."
    return docs[doc_id]


@mcp.tool()
def edit_doc(doc_id: str, new_content: str) -> str:
    """Edit the content of an existing document by its ID."""
    if doc_id not in docs:
        return f"Error: document '{doc_id}' not found."
    docs[doc_id] = new_content
    return f"Document '{doc_id}' updated successfully."


@mcp.resource("docs://documents")
def list_documents() -> list[str]:
    """Return all document IDs available."""
    return list(docs.keys())


@mcp.resource("docs://documents/{doc_id}")
def get_document(doc_id: str) -> str:
    """Return the content of a particular document."""
    if doc_id not in docs:
        return f"Error: document '{doc_id}' not found."
    return docs[doc_id]
# TODO: Write a prompt to rewrite a doc in markdown format
# TODO: Write a prompt to summarize a doc


if __name__ == "__main__":
    mcp.run(transport="stdio")
