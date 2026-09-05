Playwright Automation: Scenario-Based Foundations

Q1. How would you stabilize a flaky login test that fails only in CI?

Sample answer: I would not start by increasing timeout globally. I would compare local and CI traces, check whether the failure is timing, data, environment or auth-state related, and then fix the specific cause. For login, I normally avoid repeated UI login for every test and create a trusted authenticated storage state during setup.

• Use trace viewer, screenshots, console logs and network logs from CI artifacts.

• Check if the selector is stable and user-facing, for example getByRole or getByLabel.

• Move login to global setup or a worker-scoped fixture when the application allows it.

• Keep one or two UI login tests separately to still cover the login journey.

What not to say: “I will add waitForTimeout everywhere” sounds junior and usually creates slower flaky tests.

Q2. What locator strategy do you prefer for a large enterprise app?

Sample answer: My default order is user-facing locators first: role, label, placeholder and text where appropriate. If the UI is complex or dynamic, I ask the dev team to add stable data-testid attributes. I avoid brittle CSS chains and XPath unless there is a very specific reason.

• Role-based locators also make tests closer to how users and accessibility tools see the page.

• For reusable components, I prefer a small locator contract rather than random selectors scattered across tests.

• When text is dynamic or translated, data-testid is cleaner.

Q3. How do you test a flow where the UI triggers an API call and then updates the screen?

Sample answer: I usually wait on the user-visible result, not only the API response. When the API response is important, I capture it with waitForResponse and assert both the contract and the UI state. That gives confidence that the frontend and backend integration is actually working.

const responsePromise = page.waitForResponse(resp =>

  resp.url().includes('/orders') && resp.status() === 201);

await page.getByRole('button', { name: 'Place order' }).click();

const response = await responsePromise;

expect(await response.json()).toMatchObject({ status: 'CONFIRMED' });

await expect(page.getByText('Order confirmed')).toBeVisible();

Q4. How would you handle test data for an order creation scenario?

Sample answer: For a 10-year profile, I would expect controlled test data, not dependency on stale shared data. I prefer API-level setup, unique identifiers per run, and cleanup through API or database jobs where allowed. For critical data, I keep a clear ownership model so parallel runs do not collide.

• Generate unique data using timestamp, build number or UUID.

• Prefer API setup over UI setup unless the UI setup itself is under test.

• Clean up only what the test created; do not delete shared baseline records.

Q5. When is it okay to use page.waitForTimeout?

Sample answer: Almost never in regular tests. I may use it temporarily while debugging or in a rare case where the system has a real fixed-time behavior, but then I leave a comment explaining why. In normal automation, I use web-first assertions, locator auto-waiting, waitForResponse or waitForEvent.

What not to say: A blanket answer like “increase timeout to 60 seconds” usually indicates the candidate has not solved flakiness properly.

Q6. How do Playwright auto-waits help, and where do they not help?

Sample answer: Playwright waits for actionability before actions, which reduces a lot of Selenium-style timing code. But it does not automatically understand business completion. For example, a Save button may be clickable before the save operation is complete. For that, I still assert the success toast, response, persisted value or next screen state.

Q7. How do you validate responsive behavior?

Sample answer: I run the same scenario with project-level device profiles where it matters, not every test on every viewport. I choose smoke-critical flows for mobile and tablet, and I assert visible navigation patterns, not pixel-perfect layout unless the requirement demands it.

• Use Playwright projects for Chromium, Firefox, WebKit and selected devices.

• Keep visual checks separate from functional checks to avoid noise.

• Test major breakpoints and critical journeys, not all combinations blindly.

Q8. How would you test a file upload and file download feature?

Sample answer: For upload, I use setInputFiles and then validate that the application accepted the file. For download, I listen to the download event, save the file, and validate file name, size or content depending on the business need.

await page.setInputFiles('input[type=file]', 'fixtures/invoice.pdf');

await page.getByRole('button', { name: 'Upload' }).click();

await expect(page.getByText('Upload complete')).toBeVisible();



const downloadPromise = page.waitForEvent('download');

await page.getByRole('button', { name: 'Export' }).click();

const download = await downloadPromise;

expect(download.suggestedFilename()).toContain('export');

Playwright Automation: Command Accuracy Stress Test

Q9. What command do you use to run Playwright tests in headed mode?

Sample answer: I use npx playwright test --headed. If I want to debug step by step, I use --debug or PWDEBUG=1 depending on the situation.

npx playwright test --headed

npx playwright test --debug

Q10. How do you run only one spec file or one test title?

Sample answer: For one spec file, pass the file path. For a title match, use -g. I prefer title filters for quick local checks and tags for team-level selection.

npx playwright test tests/orders/create-order.spec.ts

npx playwright test -g "creates an order with valid payment"

npx playwright test --grep @smoke

Q11. How do you generate and open the HTML report?

Sample answer: After a run, Playwright can generate an HTML report based on the reporter configuration. I normally open it using npx playwright show-report, and in CI I publish the report as an artifact.

npx playwright show-report

Q12. What is the difference between test.only, test.skip and test.fixme?

Sample answer: test.only is for temporary local focus and should never be committed. test.skip intentionally skips a test under a condition. test.fixme documents a known broken test or missing feature, and the team should track it with an owner and expiry.

Q13. How do you capture a trace only on failure?

Sample answer: I configure trace: on-first-retry or retain-on-failure in playwright.config. In CI, on-first-retry is a good balance because it keeps artifacts useful without making every run too heavy.

use: {

  trace: 'on-first-retry',

  screenshot: 'only-on-failure',

  video: 'retain-on-failure'

}

Q14. How do retries differ from fixing flaky tests?

Sample answer: Retries are a safety net, not the solution. I use retries in CI to absorb very small environmental instability, but every retry failure should still be visible in the report. If a test passes only after retry often, it needs triage.

Q15. How do you mock an API response in Playwright?

Sample answer: I use page.route to intercept the request and fulfill a controlled response. I use it mainly for isolated UI behavior, error states or hard-to-create backend scenarios. For true integration coverage, I let the real API run.

await page.route('**/api/profile', async route => {

  await route.fulfill({

    status: 200,

    contentType: 'application/json',

    body: JSON.stringify({ name: 'Test User', plan: 'Premium' })

  });

});

Q16. What is the purpose of browser context?

Sample answer: A browser context is an isolated session inside the browser. Cookies, local storage and permissions are separated. I use contexts for parallel tests, multi-user scenarios and clean session boundaries.

Q17. How do you handle multiple tabs or popups?

Sample answer: I wait for the popup event before clicking the element that opens it. Then I assert the new page. The key is to create the promise first to avoid a race condition.

const popupPromise = page.waitForEvent('popup');

await page.getByRole('link', { name: 'Open invoice' }).click();

const popup = await popupPromise;

await expect(popup).toHaveURL(/invoice/);

Playwright Automation: Advanced Real-World Scenarios

Q18. How would you automate an MFA login flow?

Sample answer: I try not to automate real MFA for every test. In enterprise systems, I discuss a test-friendly path with security: pre-authenticated storage state, test bypass in lower environments, API token exchange, or mocked identity provider for non-security tests. I still keep dedicated security/MFA tests separate.

• Never weaken production security for automation convenience.

• Keep auditability: which test accounts, what bypass, which environments.

• UI tests should not depend on someone manually approving MFA.

Q19. How do you test a role-based access scenario?

Sample answer: I create separate authenticated states for each role and run the same business checks using role-specific fixtures. I validate both positive and negative access: what the user can see and what the user must not access directly by URL or API.

test.use({ storageState: 'auth/admin.json' });

test('admin can approve request', async ({ page }) => { /* ... */ });

Q20. What would you do if a third-party payment page is unstable?

Sample answer: I separate what we own from what the vendor owns. For most CI tests, I mock or sandbox the third-party boundary and assert our request and callback handling. I keep one scheduled integration test against the vendor sandbox if the business risk justifies it.

Q21. How do you test WebSocket or real-time notification behavior?

Sample answer: I start by checking if the notification can be triggered through API or controlled backend action. Then I assert the actual UI update. If real-time timing is noisy, I use event-based waiting and clear timeouts rather than fixed sleeps. I also test fallback behavior when the socket disconnects.

Q22. How would you debug a test that passes locally but fails only on WebKit?

Sample answer: I would not assume it is a Playwright bug. I would inspect the trace, browser console and network behavior in that project. Common causes are unsupported browser behavior, different focus handling, CSS/layout differences, or app code that accidentally assumes Chromium.

• Run the specific test with --project=webkit.

• Check if the issue reproduces manually in that browser.

• If the app has a browser compatibility bug, raise it as a product defect, not an automation defect.

Q23. How do you test emails generated by the application?

Sample answer: I avoid depending on a real mailbox where possible. I prefer a test email service, local mail capture, API endpoint or database event table exposed for lower environments. The test should assert subject, key body content and links without being blocked by delivery delays.

Q24. How would you approach visual regression testing?

Sample answer: I keep visual tests focused and controlled. I freeze test data, viewport, theme and animations, and I run visual checks for stable components or core pages. I do not mix visual assertions into every functional test because that creates noisy failures.

Q25. How do you handle localization in Playwright tests?

Sample answer: I avoid hardcoding English text everywhere if the product is localized. Depending on the app, I use locale-specific test projects, stable test ids, and verify key translated messages from resource files or business-approved text. I also check date, number and currency formatting for important flows.

Playwright Automation: Framework & Architecture Decisions

Q26. How would you design a Playwright framework for a team of 20 QA and developers?

Sample answer: I would keep the framework boring and maintainable. A clear folder structure, shared fixtures, typed page/action classes, tagging strategy, environment config, reporting and CI conventions matter more than clever abstractions. The goal is that a new team member can add a reliable test without asking five people.

• Separate test intent from low-level UI operations.

• Use fixtures for login, test data, API clients and common setup.

• Keep utilities small and reviewed. Framework code should have the same quality standard as application code.

Q27. Page Object Model or not?

Sample answer: I use page objects when they reduce duplication and clarify business actions. I avoid turning them into huge classes full of every locator on the page. For complex products, I prefer component objects plus service/API helpers. The test should still be readable as a business scenario.

Q28. How do you avoid over-engineering the automation framework?

Sample answer: I add abstraction only after repetition is real, not imagined. If three flows use the same stable behavior, I extract it. If a helper hides important test logic or makes debugging harder, I do not use it. Framework maturity should follow product maturity.

Q29. How do you manage environment-specific configuration?

Sample answer: I keep environment URLs, credentials references, feature flags and timeouts outside the test logic. Secrets come from a secure store or CI variables, not committed files. The same test should point to QA, staging or preview environments with minimal config changes.

const baseURL = process.env.BASE_URL ?? 'https://qa.example.com';

export default defineConfig({

  use: { baseURL },

  retries: process.env.CI ? 2 : 0

});

Q30. What tagging strategy do you recommend?

Sample answer: I use simple tags that map to execution purpose: @smoke, @regression, @api, @visual, @critical, maybe domain tags like @orders. I avoid too many tags because they become unreliable. Tags should drive CI selection and release gates.

Q31. How do you structure API and UI tests in the same repo?

Sample answer: I keep them close enough to share test data and domain helpers, but separate enough that UI tests do not become API tests accidentally. API setup helpers are fine; API assertions inside UI tests should be intentional and limited to integration checks.

Q32. How do you review automation code in pull requests?

Sample answer: I review selectors, test independence, data strategy, assertion quality and failure diagnostics. I also ask whether the test adds meaningful coverage or duplicates an existing scenario. A green test that no one can debug at 2 a.m. is not good automation.

Q33. How do you decide what should be automated?

Sample answer: I prioritize stable, repeatable, high-risk and high-frequency scenarios. Smoke and regression paths are obvious candidates. I am careful with features still changing every day, one-off validations, or cases where automation cost is higher than risk reduction.

Playwright Automation: CI/CD, Debugging & Failure Analysis

Q34. How do you integrate Playwright into a CI pipeline?

Sample answer: I usually create separate jobs for install, lint/unit tests, API tests and Playwright smoke/regression. I cache dependencies carefully, install browsers deterministically, run tests in parallel, and publish HTML report, traces, videos and screenshots as artifacts.

npx playwright install --with-deps

npx playwright test --reporter=html,junit

Q35. What artifacts do you publish for failed UI tests?

Sample answer: At minimum: trace, screenshot, video for failed or retried tests, console logs, network logs where useful, and JUnit XML for CI integration. The purpose is that a developer can diagnose the failure without rerunning locally first.

Q36. How do you reduce Playwright pipeline time?

Sample answer: I look at test selection first, then parallelism and sharding. I split smoke from full regression, avoid UI setup repetition, use API setup, and remove duplicate flows. If a suite is slow because tests are doing too much, adding more workers only hides the problem for a while.

Q37. How do you handle flaky tests in CI?

Sample answer: I track flaky tests separately from product defects. If a test is flaky, it gets an owner, root cause, and target date. I may quarantine it from release gating, but I do not silently delete it unless the coverage is no longer valuable.

• Classify as test issue, environment issue, product timing issue or data issue.

• Use retry rate and failure signature to prioritize.

• Keep leadership visibility if flakiness impacts release confidence.

Q38. Explain your failure analysis process after a nightly regression failure.

Sample answer: I check whether the failure is new or recurring, then inspect trace, screenshot and network. I compare build changes, environment changes and test data changes. Once I identify a likely cause, I either raise a product defect with evidence or fix the automation with a narrow change and add a note to prevent repeat issues.

Q39. How would you test in pull requests without slowing developers?

Sample answer: I run a fast smoke pack on every PR and reserve broader regression for merge, nightly or release branches. I also use changed-area mapping where practical. The PR gate should catch high-confidence failures quickly, not become a two-hour blocker for every small CSS change.

Q40. What metrics do you report for automation health?

Sample answer: I report pass rate, retry rate, flaky test count, average duration, top failing areas, escaped defects linked to automated coverage, and time saved in regression. I avoid vanity metrics like only number of scripts because 1,000 unstable scripts are not useful.

Q41. How do you manage browsers in CI?

Sample answer: I pin Playwright versions, install matching browsers in the build, and use container images where appropriate. I do not rely on whatever browser happens to be available on the agent. For cross-browser coverage, I run selected suites across Chromium, Firefox and WebKit based on product risk.

Playwright Automation: Architect-Level Decision Simulation

Q42. Your organization is moving from Selenium to Playwright. How would you plan the migration?

Sample answer: I would not rewrite everything at once. I would start with a pilot on a high-value but manageable module, build the framework baseline, prove CI stability, then migrate priority suites. Old Selenium tests continue only where they still provide value. The migration plan needs milestones, ownership and a retirement strategy.

• Inventory existing tests and classify by value, stability and duplication.

• Create coding standards and sample tests before scaling.

• Train developers and QA together so ownership is not limited to one automation team.

Q43. How do you decide whether to use Playwright for API testing?

Sample answer: Playwright APIRequestContext is excellent for setup, teardown and moderate API checks, especially when combined with UI flows. For deep contract testing, performance testing or large API suites, I may use a dedicated API tool or contract framework. The decision depends on scale and maintainability, not tool fashion.

Q44. How would you set quality gates for release?

Sample answer: I would define gates by risk level. For every release, smoke must pass, critical regression must be clean or have approved exceptions, severe defects must be addressed, and automation quality must be visible. I also keep manual exploratory testing for new or high-risk areas because automation alone is not a release strategy.

Q45. How do you balance mocked tests and true end-to-end tests?

Sample answer: I use a testing pyramid mindset. End-to-end tests should cover the most important customer journeys and integrations. Mocked tests help cover error states and edge cases quickly. If everything is mocked, we lose integration confidence. If everything is end-to-end, the suite becomes slow and fragile.

Q46. How would you convince engineering leadership to invest in test automation architecture?

Sample answer: I would talk in business terms: release confidence, regression cycle time, defect leakage, developer feedback time and cost of flaky tests. I would show current pain with data, propose a staged roadmap, and commit to measurable outcomes rather than just asking for time to build a framework.

Q47. What governance would you put around a shared Playwright framework?

Sample answer: I would define coding standards, review rules, ownership, release notes for framework changes, versioning, and examples. A shared framework should not become a dumping ground. It needs a small maintainer group but broad contribution from feature teams.

Q48. A team wants 100% automation. How do you respond?

Sample answer: I would reframe the goal. The goal is not 100% automation; it is the right confidence at the right cost. Some areas are better covered by unit tests, contract tests, monitoring or exploratory testing. I would push for risk-based coverage and measurable release outcomes.

Q49. How do you bring observability into test automation?

Sample answer: I connect automation failures with application logs, request IDs, build metadata and environment health. If a UI test fails because an API returned 500, the report should help find that backend error quickly. Mature automation is not only asserting; it is also producing useful diagnostic signals.

Quick MCQ-Style Drill: Playwright Commands and Concepts

MCQ 1. Which locator is usually preferred for an accessible button?

Answer: getByRole("button", { name: "Save" })  |  Why: It mirrors user intent and accessibility semantics.

MCQ 2. Which option is commonly used to run tests in headed mode?

Answer: --headed  |  Why: Useful for local observation, not normally for CI.

MCQ 3. Which trace mode is a balanced CI default?

Answer: on-first-retry  |  Why: It collects trace when a failure is being retried, keeping artifact size manageable.

MCQ 4. What is the better alternative to waitForTimeout for UI completion?

Answer: Web-first assertion or event wait  |  Why: Example: expect(locator).toBeVisible() or waitForResponse.

MCQ 5. Which Playwright concept isolates cookies and local storage?

Answer: Browser context  |  Why: Each context behaves like a clean independent session.

MCQ 6. What should not be committed after local debugging?

Answer: test.only  |  Why: It limits execution and can accidentally skip the suite in CI.

MCQ 7. Which command opens the Playwright HTML report?

Answer: npx playwright show-report  |  Why: Assumes the report has already been generated.

MCQ 8. What is the best way to test a hard-to-create API error state in UI?

Answer: Route interception/mock  |  Why: Use real integration separately for critical paths.

MCQ 9. Which artifact is most useful for step-by-step failure debugging?

Answer: Trace  |  Why: Trace viewer shows actions, snapshots, network and console details.

MCQ 10. What is the main risk of overusing retries?

Answer: It hides real instability  |  Why: Retries should make instability visible, not invisible.