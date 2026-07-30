# Playwright E2E Tests for Graph Editor and Asset Generation

## Overview

This directory contains comprehensive end-to-end tests for the graph editor and asset generation pages using Playwright.

## Test File

- `graph.spec.ts` - Complete E2E test suite covering all major functionality

## Test Coverage

### 1. Graph Editor Basic Functionality (6 tests)
- ✓ Page loading and initialization
- ✓ Adding new nodes
- ✓ Editing node information  
- ✓ Connecting nodes to create edges
- ✓ Deleting nodes and edges

### 2. LLM Extraction Functionality (4 tests)
- ✓ Input scene description trigger extraction
- ✓ Dialog open/close functionality
- ✓ Validation error handling
- ✓ API failure handling

### 3. Graph Validation and Saving (4 tests)
- ✓ Valid graph validation
- ✓ Cycle detection and warnings
- ✓ Successful graph saving
- ✓ Save failure with cycles

### 4. Asset Generation Page (9 tests)
- ✓ Page loading
- ✓ Graph selection and loading
- ✓ Serial generation triggering
- ✓ Generation progress display
- ✓ Wave order verification
- ✓ Status badge display
- ✓ Prompt preview functionality

### 5. Responsive Design (4 tests)
- ✓ Tablet viewport adaptation
- ✓ Mobile viewport adaptation
- ✓ Mobile basic functionality
- ✓ Landscape mobile orientation

**Total: 27 test cases across 6 browser/device configurations**

## Running Tests

### First-Time Setup

```bash
cd frontend
npx playwright install
```

### Run All Tests

```bash
cd frontend
npx playwright test graph.spec.ts
```

### Run Specific Test Suite

```bash
# Graph Editor tests only
npx playwright test graph.spec.ts --grep "Graph Editor Basic Functionality"

# Asset Generation tests only
npx playwright test graph.spec.ts --grep "Asset Generation Page"
```

### Run in Specific Browser

```bash
# Chromium only
npx playwright test graph.spec.ts --project=chromium

# Mobile viewport only
npx playwright test graph.spec.ts --project="Mobile Chrome"
```

### Run with UI (headed mode)

```bash
npx playwright test graph.spec.ts --headed
```

### Generate Test Report

```bash
npx playwright test graph.spec.ts --reporter=html
```

Then open `playwright-report/index.html` in your browser.

## Test Utilities

The test suite includes helper functions:

- `gotoGraphEditor(page)` - Navigate to graph editor and verify initialization
- `gotoAssetReview(page)` - Navigate to asset generation page and verify initialization  
- `addNode(page, options)` - Fill and submit the add node form
- `openExtractDialog(page, description)` - Open AI extraction dialog with input

## Configuration

Tests are configured in `playwright.config.ts`:

- **Base URL**: `http://localhost:5173` (Vite dev server)
- **Timeout**: 30 seconds per test
- **Browsers**: Chromium, Firefox, WebKit, Mobile Chrome, Mobile Safari, Tablet
- **Auto-server**: Automatically starts Vite dev server before tests

## API Mocking

Tests use `page.route()` to mock backend API responses for:

- Graph extraction (`/api/graph/extract`)
- Graph validation (`/api/graph/validate`)  
- Graph saving (`/api/graph/save`)
- Graph loading (`/api/graph/{scene_id}`)
- Graph generation (`/api/graph/generate`)

This ensures tests run reliably without requiring a live backend.

## Expected Test Results

All 27 tests should PASS when:
1. Frontend is built correctly
2. Vite dev server runs on port 5173
3. All React components render properly
4. API mocking handles all backend interactions

## Troubleshooting

### Tests fail with "Executable doesn't exist"
Run: `npx playwright install`

### Tests fail with connection refused
Ensure Vite server is running: `npm run dev`

### Tests timeout
Increase timeout in `playwright.config.ts` if needed

### Flaky tests
Some tests may require increased wait times for React Flow rendering

## Coverage Report

These E2E tests provide coverage for:

- ✅ User workflows and acceptance criteria
- ✅ Cross-browser compatibility  
- ✅ Responsive design
- ✅ Error handling
- ✅ State management
- ✅ UI interactions

Not covered (intentional):
- Unit testing (use Vitest for that)
- Backend logic (covered by integration tests)
- Performance testing (separate suite needed)

## Maintenance

When adding new features:
1. Update test helpers if needed
2. Add test cases for new functionality
3. Update API mocking for new endpoints
4. Run full test suite to verify no regressions

## Notes

- Tests are independent and can run in parallel
- Each test has clear setup/teardown
- Screenshots captured automatically on failure
- Videos recorded for failed tests
- Trace files available for debugging