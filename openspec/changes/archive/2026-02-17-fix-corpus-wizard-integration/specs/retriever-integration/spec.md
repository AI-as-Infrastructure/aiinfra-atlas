# Retriever Integration Specification

## Overview

This specification defines how the corpus wizard generates retrievers that properly integrate with the ATLAS system, ensuring filters and search functionality work correctly.

## MODIFIED Requirements

### Requirement: Retriever SHALL correctly read manifest structure

The generated retriever SHALL read filter information from the actual manifest structure rather than an assumed structure.

#### Scenario: Reading filter options from manifest

Given a manifest with filters defined at `fields.corpus.values`
When the retriever's `get_corpus_options()` method is called
Then it should return the correct filter options from that path
And include proper labels and values for the UI

#### Scenario: Supporting the 2-filter system

Given a corpus with filter_1 and filter_2 defined
When the retriever processes a query with filters
Then it should correctly apply both filter levels
And return only documents matching the filter criteria

### Requirement: Retriever template SHALL match manifest output

The retriever template used during corpus building SHALL be aligned with the manifest structure produced by the same build process.

#### Scenario: Template generation with correct paths

Given the corpus builder creates a manifest
When it generates the retriever from template
Then the retriever code should use the same paths as the manifest structure
And handle missing or optional fields gracefully

## ADDED Requirements

### Requirement: Retriever SHALL provide backward compatibility

The retriever SHALL work with both new manifest structures and any existing corpus formats.

#### Scenario: Handling legacy manifest formats

Given a corpus with an older manifest structure
When the retriever attempts to read filter information
Then it should fall back to alternative paths if primary paths fail
And log warnings about deprecated structures

### Requirement: Retriever SHALL expose filter metadata

The retriever SHALL provide metadata about available filters for the UI to consume.

#### Scenario: Providing filter labels and counts

Given a retriever with filter data
When the UI requests filter information
Then the retriever should return both filter labels and document counts
And indicate which filters are currently active