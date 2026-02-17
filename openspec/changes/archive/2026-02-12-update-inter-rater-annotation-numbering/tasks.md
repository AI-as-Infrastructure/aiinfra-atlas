# Implementation Tasks

## 1. Query Existing Inter-Rater Count
- [x] 1.1 Update `get_inter_rater_count()` in `phoenix_client.py` to return count before current submission
- [x] 1.2 Pass span_id to the feedback recording function to enable count query
- [x] 1.3 Add error handling for Phoenix API query failures

## 2. Update Annotation Naming Function
- [x] 2.1 Modify `get_annotation_name()` in `backend/telemetry/feedback.py` to accept inter_rater_number parameter
- [x] 2.2 Update function to format annotation name as `[inter-rating-N]` where N is the rater number
- [x] 2.3 Ensure original (non-inter-rater) feedback continues to use base name without prefix

## 3. Wire Up Inter-Rater Number Determination
- [x] 3.1 Query inter-rater count before creating annotation data
- [x] 3.2 Calculate next inter-rater number (count + 1)
- [x] 3.3 Pass inter-rater number to `get_annotation_name()` function
- [x] 3.4 Handle edge cases (concurrent submissions, Phoenix API errors)

## 4. Testing
- [x] 4.1 Test first inter-rater submission shows `[inter-rating-1]`
- [x] 4.2 Test second inter-rater submission shows `[inter-rating-2]`
- [x] 4.3 Test third inter-rater submission shows `[inter-rating-3]`
- [x] 4.4 Test original feedback has no inter-rating prefix
- [x] 4.5 Test Phoenix query error handling (fallback behavior)

## 5. Validation
- [x] 5.1 Verify annotations appear correctly in Phoenix UI (verified in production)
- [x] 5.2 Verify Inter-Rater Dashboard displays numbered annotations (verified in production)
- [x] 5.3 Ensure backward compatibility with existing `[Inter-rater]` annotations (verified)
