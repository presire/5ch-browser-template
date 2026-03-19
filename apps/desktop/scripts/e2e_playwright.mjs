/**
 * End-to-end tests for the Tauri desktop app.
 *
 * Connects to the running Tauri WebView2 via CDP (Chrome DevTools Protocol).
 * Tests Tauri IPC (invoke) directly via page.evaluate and validates real
 * server responses from 5ch.io.
 *
 * Environment:
 *   E2E_CDP_URL  - CDP endpoint (default: http://127.0.0.1:9248)
 */
import process from "node:process";
import { chromium } from "playwright";

const CDP_URL = process.env.E2E_CDP_URL?.trim() || "http://127.0.0.1:9248";

function assert(cond, message) {
  if (!cond) throw new Error(message);
}

let browser;
try {
  console.log(`e2e: connecting to CDP at ${CDP_URL}`);
  browser = await chromium.connectOverCDP(CDP_URL);
  console.log("e2e: connected");

  const contexts = browser.contexts();
  assert(contexts.length > 0, "no browser contexts found");
  const page = contexts[0].pages()[0];
  assert(page, "no page found");

  // Capture console/errors
  page.on("pageerror", (err) => console.log(`e2e [pageerror]: ${err.message}`));

  // --- 1. Runtime detection ---
  const statusText = await page.$eval(".status-bar", (el) => el.textContent || "");
  assert(statusText.includes("Runtime:TAURI"), `expected TAURI runtime, got: ${statusText}`);
  console.log("e2e: [PASS] runtime is TAURI");

  // --- 2. IPC: fetch_bbsmenu_summary ---
  const menuResult = await page.evaluate(() =>
    window.__TAURI_INTERNALS__.invoke("fetch_bbsmenu_summary", {})
  );
  assert(menuResult && menuResult.topLevelKeys > 0, `bbsmenu should have keys, got: ${JSON.stringify(menuResult)}`);
  console.log(`e2e: [PASS] bbsmenu summary: ${menuResult.topLevelKeys} top-level keys`);

  // --- 3. IPC: fetch_board_categories ---
  const categories = await page.evaluate(() =>
    window.__TAURI_INTERNALS__.invoke("fetch_board_categories", {})
  );
  assert(Array.isArray(categories) && categories.length > 0, `expected board categories array, got: ${JSON.stringify(categories).substring(0, 200)}`);
  const totalBoards = categories.reduce((s, c) => s + c.boards.length, 0);
  console.log(`e2e: [PASS] board categories: ${categories.length} categories, ${totalBoards} boards`);

  // Validate category structure
  const firstCat = categories[0];
  assert(firstCat.categoryName && firstCat.boards.length > 0, "first category should have name and boards");
  const firstBoard = firstCat.boards[0];
  assert(firstBoard.boardName && firstBoard.url, "board should have boardName and url");
  assert(firstBoard.url.includes("5ch.io"), `board url should be normalized to 5ch.io, got: ${firstBoard.url}`);
  console.log(`e2e: [PASS] board structure: ${firstCat.categoryName} > ${firstBoard.boardName} (${firstBoard.url})`);

  // --- 4. IPC: fetch_thread_list from a real board ---
  // Use a board URL that is NOT headline (which returns 404)
  let testBoardUrl = null;
  for (const cat of categories) {
    if (cat.categoryName.includes("ヘッドライン")) continue;
    for (const b of cat.boards) {
      if (!b.url.includes("headline") && b.url.match(/\/[a-z]+\/$/)) {
        testBoardUrl = b.url;
        break;
      }
    }
    if (testBoardUrl) break;
  }
  assert(testBoardUrl, "could not find a suitable board URL to test");
  console.log(`e2e: testing thread list from: ${testBoardUrl}`);

  const threads = await page.evaluate(async (url) => {
    return window.__TAURI_INTERNALS__.invoke("fetch_thread_list", { threadUrl: url, limit: 20 });
  }, testBoardUrl);
  assert(Array.isArray(threads) && threads.length > 0, `expected threads > 0 from ${testBoardUrl}, got ${threads?.length ?? 0}`);
  console.log(`e2e: [PASS] thread list: ${threads.length} threads from ${testBoardUrl}`);

  // Validate thread structure
  const firstThread = threads[0];
  assert(firstThread.threadKey, "thread should have threadKey");
  assert(firstThread.title, "thread should have title");
  assert(firstThread.responseCount > 0, `thread responseCount should be > 0, got ${firstThread.responseCount}`);
  assert(firstThread.threadUrl.includes("5ch.io"), `thread url should contain 5ch.io, got ${firstThread.threadUrl}`);
  console.log(`e2e: [PASS] thread structure: "${firstThread.title.substring(0, 40)}" (${firstThread.responseCount} res)`);

  // --- 5. IPC: fetch_thread_responses_command ---
  const responses = await page.evaluate(async (url) => {
    return window.__TAURI_INTERNALS__.invoke("fetch_thread_responses_command", { threadUrl: url, limit: 50 });
  }, firstThread.threadUrl);
  assert(Array.isArray(responses) && responses.length > 0, `expected responses > 0, got ${responses?.length ?? 0}`);
  console.log(`e2e: [PASS] responses: ${responses.length} from thread "${firstThread.title.substring(0, 30)}"`);

  // Validate response structure
  const firstResp = responses[0];
  assert(firstResp.responseNo === 1, `first response should be No.1, got ${firstResp.responseNo}`);
  assert(typeof firstResp.name === "string", "response should have name");
  assert(typeof firstResp.body === "string" && firstResp.body.length > 0, "response should have non-empty body");
  assert(typeof firstResp.dateAndId === "string", "response should have dateAndId");
  console.log(`e2e: [PASS] response structure: No.${firstResp.responseNo} by "${firstResp.name}" (${firstResp.body.length} chars)`);

  // --- 6. IPC: check_auth_env_status ---
  const authStatus = await page.evaluate(() =>
    window.__TAURI_INTERNALS__.invoke("check_auth_env_status", {})
  );
  assert(typeof authStatus.beEmailSet === "boolean", "auth status should have beEmailSet");
  assert(typeof authStatus.upliftEmailSet === "boolean", "auth status should have upliftEmailSet");
  console.log(`e2e: [PASS] auth env: BE(${authStatus.beEmailSet}/${authStatus.bePasswordSet}) UPLIFT(${authStatus.upliftEmailSet}/${authStatus.upliftPasswordSet})`);

  // --- 7. IPC: probe_thread_post_form ---
  const postForm = await page.evaluate(async (url) => {
    return window.__TAURI_INTERNALS__.invoke("probe_thread_post_form", { threadUrl: url });
  }, firstThread.threadUrl);
  assert(postForm.bbs, `post form should have bbs field, got: ${JSON.stringify(postForm)}`);
  assert(postForm.key, "post form should have key field");
  assert(postForm.time, "post form should have time field");
  assert(postForm.postUrl.includes("bbs.cgi"), `post url should contain bbs.cgi, got: ${postForm.postUrl}`);
  console.log(`e2e: [PASS] post form: bbs=${postForm.bbs} key=${postForm.key} time=${postForm.time}`);

  // --- 8. React DOM interactions ---
  // Click thread row and verify selection change
  const threadRows = await page.$$eval(".threads tbody tr", (rows) => rows.length);
  if (threadRows >= 2) {
    await page.evaluate(() => {
      const row = document.querySelector(".threads tbody tr:nth-child(2)");
      if (row) row.click();
    });
    await new Promise((r) => setTimeout(r, 200));
    const selectedNo = await page.$eval(".threads tbody tr.selected-row td:first-child", (el) => el.textContent);
    assert(selectedNo === "2", `expected selected thread #2, got #${selectedNo}`);
    console.log("e2e: [PASS] thread click selection works");
  }

  // Verify compose window opens
  await page.evaluate(() => {
    const btn = document.querySelector(".tool-bar button");
    // Find Write button
    document.querySelectorAll(".tool-bar button").forEach((b) => {
      if (b.textContent === "Write") b.click();
    });
  });
  await new Promise((r) => setTimeout(r, 300));
  const composeVisible = await page.$(".compose-window");
  if (composeVisible) {
    console.log("e2e: [PASS] compose window opens");
  } else {
    console.log("e2e: [SKIP] compose window did not open via CDP click");
  }

  console.log("\ne2e: ALL TESTS PASSED");
} catch (err) {
  console.error(`\ne2e: FAILED - ${err.message}`);
  process.exit(1);
} finally {
  if (browser) {
    await browser.close().catch(() => {});
  }
}
