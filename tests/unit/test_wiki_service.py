from pathlib import Path

from platform_core.rag.wiki import WikiService


def test_wiki_persists_pages_and_retrieves_relevant_chunks(tmp_path: Path) -> None:
    config_path = tmp_path / "wiki.json"
    wiki = WikiService(config_path)
    wiki.create_page(title="Observabilidade", content="O Langfuse registra traces e observações dos agentes.")
    wiki.create_page(title="Bancos", content="O PostgreSQL armazena sessões e memória conversacional.")

    reloaded = WikiService(config_path)
    results = reloaded.retrieve("Como funcionam os traces no Langfuse?")

    assert len(reloaded.list_pages()) == 2
    assert results[0].source.startswith("Observabilidade#")
    assert "traces" in results[0].content


def test_wiki_updates_and_deletes_page(tmp_path: Path) -> None:
    wiki = WikiService(tmp_path / "wiki.json")
    page = wiki.create_page(title="Rascunho", content="Conteúdo inicial", tags=["Docs"])

    updated = wiki.update_page(page.id, title="Guia", content="Conteúdo final", tags=["docs", "RAG"])
    wiki.delete_page(page.id)

    assert updated.tags == ["docs", "rag"]
    assert wiki.list_pages() == []