# Fix UI Polish and Metadata Gaps

## Summary

Address five issues identified during manual testing: (1) the Vector Store Overview lacks build environment metadata needed for transparency and reproducibility, (2) citation metadata is limited and does not surface the source URL, (3) VITE_SITE_TITLE may not correctly reflect the corpus display name after build, (4) the "Multi Corpus Vectorstore" label in the Test Target box is redundant, and (5) the Export Config and Export Session buttons have inconsistent styling and layout.

## Motivation

ATLAS is a research tool where transparency and reproducibility are paramount. The Vector Store Overview currently shows basic corpus statistics but omits critical context about the hardware, software, and build environment used to create the vector store. Without this, a researcher cannot determine whether results might differ due to GPU vs CPU embedding, different PyTorch versions, or different hardware. This undermines the FAIR data principles the project follows.

Similarly, citation metadata needs to provide complete provenance for retrieved documents. The source URL is stored in document metadata but not surfaced to the user, reducing the utility of citations for scholarly referencing.

The UI issues (site title, redundant label, button layout) are minor polish items that affect the overall quality and clarity of the interface.

## Detailed Design

### 1. Vector Store Build Metadata (Transparency & Reproducibility)

Extend manifest.json (bump to v1.4) with a new `build` section capturing the environment at build time. The data is already collectible via `SystemRequirementsChecker.get_system_info()` in `backend/modules/system_requirements.py:206-241` but is not called during manifest generation.

**New manifest fields:**
```json
{
  "build": {
    "mode": "gpu|cpu",
    "duration_seconds": 123.4,
    "python_version": "3.10.19",
    "pytorch_version": "2.1.0",
    "cuda_version": "12.1",
    "platform": "Linux 6.6.87",
    "machine": "x86_64",
    "gpu_name": "NVIDIA RTX 4090",
    "gpu_memory_gb": 24.0,
    "gpu_used": true,
    "cpu_cores": 16,
    "system_ram_gb": 64.0,
    "builder_version": "1.4"
  }
}
```

Update the `/api/vector-store-info` endpoint and `VectorStoreInfo.vue` to display this section.

Think carefully about what fields genuinely aid reproducibility vs adding noise. The goal is to help a researcher understand whether their results could differ due to environment differences.

### 2. Citation Metadata Improvements

The `source_url` field is stored in document metadata by `CitationEnricher` (`backend/modules/citation_enricher.py:55-56`) but is not explicitly surfaced in the citation object returned by `format_document_for_citation()` (`backend/retrievers/base_retriever.py:329-344`).

**Changes needed:**
- Add `source_url` as an explicit field in the citation response object
- Compare with main branch citation handling to ensure feature parity
- Determine which additional metadata fields should be explicitly surfaced vs left in the raw metadata dict

### 3. VITE_SITE_TITLE Build Integration

The corpus wizard updates `VITE_SITE_TITLE` in `.env.development` after build (`backend/routers/corpus_wizard.py:1540-1598`), using the corpus `display_name` from the manifest. Verify this works correctly end-to-end:
- Confirm `display_name` is written correctly from the build process
- Confirm the .env file is updated with the correct value
- Confirm the frontend reads the updated value after restart
- Document the requirement that a frontend restart is needed

### 4. Remove Redundant "Multi Corpus Vectorstore" Label

In `frontend/src/components/TestTargetBox.vue:44`, the display name `'Multi Corpus Vectorstore'` is redundant within the context of the Test Target box. Either remove the field entirely from the display or rename it to something concise like `'Multi-Corpus'`.

### 5. Export Button Layout Consistency

Currently in `frontend/src/components/ChatContainer.vue:27-35`:
- `ConfigurationExportButton` has a gear icon and styled layout
- `ExportButton` (Export Session) is a plain text button

**Changes needed:**
- Place both buttons side by side at the same level
- Remove the icon from Export Config button for consistency
- Both buttons should be plain Bulma-styled buttons with consistent sizing

## Scope

This proposal covers UI polish and metadata improvements only. No changes to core RAG pipeline, build logic, or security posture. All changes are additive to existing functionality.

## Risks

- Bumping manifest version to 1.4 requires backward compatibility in manifest readers
- Adding build metadata increases manifest size (minor)
- VITE_SITE_TITLE investigation may reveal a bug requiring a separate fix
