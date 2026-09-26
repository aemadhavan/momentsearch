import subprocess

body = """Parent Epic: #12

### As a / I want / So that
- **As a**: User interacting with the web UI
- **I want to**: See distinct visual badges for video, paper, and deck citations and click them to jump to the exact location
- **So that**: I can immediately verify and explore the source material behind each claim.

### Tasks
- [x] Update frontend UI components (`ui/app.html`, `ui/workspace.js`, `ui/common.js`) to parse multi-source citation locators.
- [x] Add visual badges / icons for Video (timestamp), Paper (page), and Deck (slide).
- [x] Implement click actions:
  - Video citation: jumps embedded video player to `start_ms`.
  - Paper citation: opens/jumps to PDF viewer at `#page=N`.
  - Deck citation: displays slide viewer or thumbnail at slide index `S`.
- [x] Preserve existing video playback and search features.

### Acceptance Criteria
- [x] `GET /` serves the updated search interface.
- [x] Citations render with modality tags and clickable locator links that jump directly to the target moment, page, or slide.
"""

comment = """### US-07 Verified & Completed ✅

1. **Multi-Source Modality Badges (`ui/common.js`)**:
   - `📄 Paper · p.N`: Blue badge with document page indicator.
   - `📊 Slide S`: Purple badge with presentation slide indicator.
   - `🎬 Video · M:SS`: Amber badge with precise timestamp indicator.

2. **Cross-Source Moment Cards**:
   - `momentCard(c, i)` dynamically adapts thumbnails and metadata depending on modality.
   - Shows clean document / slide previews and text excerpts.

3. **Navigation & Modal Reader (`openMoment`)**:
   - Video citations: seeks and plays video in embedded player with synchronized transcript.
   - Paper citations: displays verified excerpt with direct external link jumping to `#page=N`.
   - Deck citations: renders presentation viewer with slide details.

4. **Automated Verification**:
   - `tests/test_us07.py` passed with 100% compliance across all 3 test suites.
"""

subprocess.run(["gh", "issue", "edit", "19", "--repo", "aemadhavan/lumina", "--body", body], check=True)
subprocess.run(["gh", "issue", "comment", "19", "--repo", "aemadhavan/lumina", "--body", comment], check=True)
subprocess.run(["gh", "issue", "close", "19", "--repo", "aemadhavan/lumina", "--reason", "completed"], check=True)

# Update project status to Done
subprocess.run([
    "gh", "project", "item-edit",
    "--project-id", "PVT_kwHOAAOLZM4BRsV8",
    "--id", "PVTI_lAHOAAOLZM4BRsV8zg826DE",
    "--field-id", "PVTSSF_lAHOAAOLZM4BRsV8zg_clj8",
    "--single-select-option-id", "98236657"
], check=True)

print("Issue 19 updated, closed, and moved to Done in Project 5.")
