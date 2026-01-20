# Capability: Enhanced Build Progress Tracking

## ADDED Requirements

### Requirement: System requirements analysis
The system SHALL analyze hardware capabilities and provide build time estimates before starting corpus generation.

#### Scenario: Check system before GPU build
GIVEN a user is ready to build a corpus with 10,000 documents
WHEN the system checks requirements
THEN it displays:
  - CPU: 8 cores available
  - GPU: NVIDIA RTX 3080 with 10GB memory detected
  - RAM: 32GB total, 20GB available (8GB required)
  - Disk: 500GB free (estimated 5GB needed)
  - Estimated time: 25 minutes (GPU mode) vs 75 minutes (CPU mode)
AND warns if any requirements are not met
AND allows the user to choose processing mode

#### Scenario: Warn about insufficient resources
GIVEN a user attempts to build a large corpus
WHEN the system detects only 4GB RAM available but 8GB required
THEN it displays a warning:
  "Insufficient memory: 4GB available, 8GB recommended. Build may fail or be very slow."
AND offers options:
  - Continue anyway (at risk)
  - Reduce chunk size to lower memory usage
  - Cancel and free up memory

### Requirement: Real-time progress metrics
The system SHALL provide detailed real-time progress updates during vector store creation.

#### Scenario: Monitor detailed build progress
GIVEN a corpus build is in progress using GPU mode
WHEN the user views the progress screen
THEN they see real-time updates including:
  - Overall: 4,523/10,000 documents (45.23%)
  - Current: Processing document "darwin/1859/letter_2534.xml", chunk 12/18
  - Speed: 4.2 docs/sec current, 3.8 docs/sec average
  - Time: 19:45 elapsed, ~23:15 remaining
  - Memory: RAM 6.2/32GB, GPU 3.1/10GB
  - CPU: 45% usage, GPU: 78% usage
  - Per-filter progress: "1850s: 1,234/2,500", "Darwin: 2,100/4,000"
AND updates refresh at least every second
AND all metrics are accurate within 5%

### Requirement: Processing mode selection
The system SHALL support both CPU and GPU processing modes with clear trade-offs.

#### Scenario: Choose between CPU and GPU modes
GIVEN a system has both CPU and GPU available
WHEN the user reaches the build configuration step
THEN they can choose:
  - GPU Mode: Faster (3-5x), requires CUDA, uses more power
  - CPU Mode: Slower, more compatible, can run in background
AND the system shows estimated time for each mode
AND recommends the optimal choice based on corpus size

### Requirement: Pause and resume capability
The system SHALL allow pausing and resuming corpus builds without losing progress.

#### Scenario: Pause and resume build
GIVEN a corpus build is at 60% completion
WHEN the user clicks "Pause"
THEN the build stops after completing the current document
AND progress is saved to a checkpoint file
AND the user can close the wizard
AND when returning and clicking "Resume"
THEN the build continues from document 6,001 of 10,000
AND no work is repeated

#### Scenario: Recover from interruption
GIVEN a build was interrupted at 75% (power loss, crash, etc.)
WHEN the user returns to the wizard
THEN the system detects the incomplete build
AND offers to resume from the last checkpoint
AND shows what was completed vs remaining

### Requirement: Performance monitoring
The system SHALL monitor and display system performance metrics during builds.

#### Scenario: Track performance degradation
GIVEN a build is running for an extended time
WHEN performance drops below acceptable levels (< 1 doc/sec)
THEN the system displays a warning
AND suggests possible causes:
  - High memory usage (offer to reduce batch size)
  - CPU throttling (suggest cooling/break)
  - Disk I/O bottleneck (check disk space)
AND allows the user to pause and adjust settings

## MODIFIED Requirements

### Requirement: Build time estimation
The system SHALL provide accurate time estimates based on actual processing speed rather than fixed assumptions.

#### Scenario: Adaptive time estimation
GIVEN a build is in progress
WHEN the system has processed 100+ documents
THEN it calculates estimated time based on:
  - Actual processing rate so far
  - Document size distribution
  - Current system load
  - Processing mode (CPU/GPU)
AND updates the estimate every 30 seconds
AND shows confidence level (e.g., "±5 minutes")