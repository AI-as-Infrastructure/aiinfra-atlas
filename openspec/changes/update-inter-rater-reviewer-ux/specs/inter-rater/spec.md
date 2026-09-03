# inter-rater (delta)

## ADDED Requirements

### Requirement: Citation Hover Card Placement
The citation hover card in the inter-rating playback view SHALL be fully visible
whenever it is displayed, regardless of where its citation sits within the
citation list.

The card SHALL be positioned so that it remains within the viewport and within
its rendering container, rather than at a fixed offset relative to its trigger.
No ancestor container SHALL clip it.

#### Scenario: Card for the leftmost citation is fully visible
- **GIVEN** an answer whose citation list begins at the left edge of its column
- **WHEN** the reviewer hovers the first citation in the list
- **THEN** the entire hover card SHALL be visible
- **AND** no part of it SHALL be clipped by the viewport or by a container

#### Scenario: Card for the rightmost citation is fully visible
- **GIVEN** an answer whose citation list extends to the right edge of its column
- **WHEN** the reviewer hovers the last citation in the list
- **THEN** the entire hover card SHALL be visible

#### Scenario: Card does not obscure the answer being rated
- **GIVEN** a citation list rendered directly below the answer text
- **WHEN** the reviewer hovers a citation
- **THEN** the card SHALL NOT conceal the answer text the citation supports

### Requirement: Reviewer Rating History
A reviewer SHALL be able to view, read-only, the ratings they have already
submitted during the current run, so that they can check their own consistency
across items.

The history SHALL show, for each completed item, the prompt, the answer that was
rated, and the scores and fault tags the reviewer recorded.

The history SHALL be strictly limited to the requesting reviewer's own ratings.
A reviewer SHALL NOT be shown any other reviewer's ratings, scores, or identity.

The history SHALL NOT offer any path to alter a recorded rating: no editable
field, no re-submission, and no navigation from a history entry into a rating
form.

The history SHALL be reachable while the run is in progress, not only after the
reviewer's quota is complete, so that a reviewer who detects drift can correct
it in the items they have left. Opening it SHALL NOT consume, forfeit, or
reorder any remaining item, and the reviewer SHALL be able to return to the item
they were rating.

The history SHALL cover only the current run. It SHALL NOT expose ratings the
reviewer submitted in an earlier cohort or allocation.

The history SHALL be derived from the reviewer's recorded ratings rather than
from client-side storage, so that it survives a closed tab and is complete when
a reviewer resumes a part-finished run in a later sitting.

#### Scenario: History is available mid-run
- **GIVEN** a reviewer who has completed three of twenty items
- **WHEN** they open the rating history before finishing the remaining items
- **THEN** their three completed ratings SHALL be shown
- **AND** access SHALL NOT be withheld until the quota is complete

#### Scenario: Opening history does not disturb the run
- **GIVEN** a reviewer part-way through rating an item
- **WHEN** they open the rating history and then close it
- **THEN** they SHALL be returned to the item they were rating
- **AND** no remaining item SHALL be consumed, forfeited, or reordered

#### Scenario: Earlier runs are not exposed
- **GIVEN** a reviewer who rated items in a previous cohort
- **WHEN** they open the rating history during a new run
- **THEN** only the current run's completed items SHALL be listed

#### Scenario: Reviewer reviews their own completed ratings
- **GIVEN** a reviewer who has submitted three ratings in the current run
- **WHEN** they open the rating history
- **THEN** all three completed items SHALL be listed
- **AND** each SHALL show the prompt, the rated answer, and the scores and fault tags recorded

#### Scenario: Other reviewers' ratings are never shown
- **GIVEN** a prompt that has been rated by more than one reviewer
- **WHEN** a reviewer opens their rating history for that prompt
- **THEN** only their own scores SHALL be shown
- **AND** no other reviewer's scores or identity SHALL be disclosed

#### Scenario: History cannot be used to change a rating
- **GIVEN** a reviewer viewing a completed item in the rating history
- **WHEN** they attempt to alter a recorded score
- **THEN** no editable control SHALL be available
- **AND** no submission SHALL be sent

#### Scenario: History survives a closed tab
- **GIVEN** a reviewer who rated ten of twenty items, then closed the browser
- **WHEN** they resume the run in a new tab and open the rating history
- **THEN** all ten completed ratings SHALL be shown

#### Scenario: History unavailable is stated, not silently emptied
- **GIVEN** the reviewer's recorded ratings cannot be read
- **WHEN** the reviewer opens the rating history
- **THEN** the view SHALL state that history is unavailable
- **AND** it SHALL NOT present an empty or partial history as complete

### Requirement: Rated Sessions Are Not Re-Presented
Once a reviewer has submitted a rating for a prompt, that prompt SHALL NOT be
presented to them again as a ratable item for the remainder of the run.

This SHALL hold across browser history navigation, in-app navigation, and page
reload — not only for as long as the rating component remains mounted.

Where a duplicate submission nevertheless reaches the submission gate and is
refused, the reviewer SHALL be told that they have already rated that prompt.
It SHALL NOT be reported as the prompt being unavailable.

#### Scenario: Browser Back does not return a rated prompt
- **GIVEN** a reviewer who has just submitted a rating
- **WHEN** they press the browser Back button
- **THEN** the prompt they rated SHALL NOT be presented as a ratable item

#### Scenario: Reload does not return a rated prompt
- **GIVEN** a reviewer who has rated several prompts in the current run
- **WHEN** they reload the page
- **THEN** none of the prompts they have rated SHALL be presented as ratable items

#### Scenario: Refused duplicate is reported accurately
- **GIVEN** a submission for a prompt the reviewer has already rated
- **WHEN** the submission gate refuses it
- **THEN** the reviewer SHALL be told they have already rated that prompt
- **AND** the message SHALL NOT attribute the refusal to unavailability

### Requirement: Task State Survives In-App Navigation
A reviewer's allocation and progress SHALL be retained when they navigate to
another page within the application and return to the inter-rating task.

Returning SHALL NOT require the reviewer's allocation to be fetched again, and
SHALL NOT replace the task view with a full-page loading state when the
allocation is already known.

#### Scenario: Returning from FAQ resumes the task
- **GIVEN** a reviewer part-way through their allocation
- **WHEN** they navigate to the FAQ page and return via the site title link
- **THEN** the task SHALL resume at the item they were on
- **AND** their allocation SHALL NOT be refetched

#### Scenario: Returning does not blank the task view
- **GIVEN** a reviewer returning to the inter-rating task from another page
- **WHEN** the task view renders
- **THEN** the full-page loading state SHALL NOT be shown

#### Scenario: Progress is preserved across the round trip
- **GIVEN** a reviewer who has completed four of twenty items
- **WHEN** they visit the About page and return
- **THEN** their completed count SHALL still read four
- **AND** the four rated prompts SHALL NOT be presented again

### Requirement: Immediate Reviewer Count Refresh
The remaining-count indicator in the site header SHALL be refreshed after every
successful rating submission, not only when a reviewer completes their quota.

The header count and the count shown in the task view SHALL NOT disagree for
longer than it takes the refresh to complete.

#### Scenario: Count decrements on each submission
- **GIVEN** a header count reading `Inter-rate (12)`
- **WHEN** the reviewer submits one rating
- **THEN** the header count SHALL refresh without waiting for the polling interval
- **AND** it SHALL read `Inter-rate (11)`

#### Scenario: Header and task view agree
- **GIVEN** a reviewer who has just submitted a rating
- **WHEN** they compare the header count with the task view's completed count
- **THEN** the two SHALL be consistent with each other
