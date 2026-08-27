# Tasks

Spec-only change. No code or operational steps.

## 1. Spec

- [x] **Task 1.1**: Add the `post-deployment` capability delta with requirements
      for tag/commit correspondence, release artifact consistency, provenance
      before collection, export before reset, and tracked completion
- [x] **Task 1.2**: Validate strictly (`openspec validate add-post-deployment-spec --strict`)

## 2. Adoption

- [ ] **Task 2.1**: Run the v0.4.0 release through the sequence and note anything
      the spec does not cover — first real use is the test of whether these
      requirements are complete
- [ ] **Task 2.2**: If gaps are found, amend this change before archiving rather
      than working around them in the release change
- [ ] **Task 2.3**: Once `release-inter-rater-v0-4-0` is archived, confirm its
      §5–7 steps map onto these requirements, so the next release can start from
      the spec instead of copying the previous release's tasks

## 3. Archive

- [ ] **Task 3.1**: Archive this change
      (`openspec archive add-post-deployment-spec`). Archive only after Task 2.1,
      so the spec is validated against one real release first
