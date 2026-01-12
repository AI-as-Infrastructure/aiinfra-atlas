# Change: Update Inter-Rater Annotation Numbering

## Why
Currently, the system appends `[Inter-rater]` to feedback annotation names, which only supports a single inter-rating label. When multiple raters provide feedback on the same session, all annotations appear with the same prefix, making it difficult to distinguish between different raters and track individual inter-rater contributions.

## What Changes
- Update annotation naming to use numbered format: `[inter-rating-1]`, `[inter-rating-2]`, etc.
- Determine the inter-rater number by counting existing inter-rater annotations for the span
- Modify the `get_annotation_name()` function in `backend/telemetry/feedback.py`
- Ensure the numbering is consistent and sequential for each new inter-rater

## Impact
- Affected specs: `feedback` capability (to be created)
- Affected code:
  - `backend/telemetry/feedback.py:318-322` - `get_annotation_name()` function
  - `backend/services/phoenix_client.py` - May need helper method to count inter-rater annotations
- Affected UI: Inter-Rater Dashboard will display numbered annotations instead of generic `[Inter-rater]` prefix
- **Non-breaking**: Existing `[Inter-rater]` annotations will remain unchanged; new annotations will use numbered format
