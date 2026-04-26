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
    """Return the full text of a document from the in-memory document store.

    WHEN TO USE: the user asks for the content of a specific known document by
    its ID (e.g. "show me report.pdf", "what does plan.md say"). If you do not
    know the exact ID, list the resource ``docs://documents`` first.

    Args:
        doc_id: The exact document ID, e.g. "report.pdf", "plan.md", "spec.txt".

    Returns:
        The document text, or an error string if the ID does not exist.

    Examples:
        - "Read deposition.md"
        - "What's in financials.docx?"
    """
    if doc_id not in docs:
        return f"Error: document '{doc_id}' not found."
    return docs[doc_id]


@mcp.tool()
def edit_doc(doc_id: str, new_content: str) -> str:
    """Replace the entire text of a document in the in-memory document store.

    WHEN TO USE: the user asks to update, rewrite, or overwrite a known
    document. This tool only does FULL replacement — for partial edits, call
    ``read_doc`` first, modify the text yourself, then pass the complete new
    text here.

    Args:
        doc_id: The exact document ID to edit.
        new_content: The complete new text that replaces the current content.

    Returns:
        Confirmation message, or an error string if the ID does not exist.

    Examples:
        - "Update plan.md to say 'Phase 1 complete'"
        - "Rewrite spec.txt with the following: ..."
    """
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
