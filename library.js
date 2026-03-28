const token = localStorage.getItem("pkv_token");
const authStatus = document.getElementById("library-auth-status");
const serverTime = document.getElementById("server-time");
const feed = document.getElementById("library-feed");
const booksGrid = document.getElementById("books-grid");
const searchInput = document.getElementById("search-books");
const bookForm = document.getElementById("book-form");

let booksCache = [];

function setSessionState() {
  authStatus.textContent = token ? "Authenticated" : "Sign in required";
}

async function callLibraryApi(path, options = {}) {
  const request = { ...options, headers: { ...(options.headers || {}) } };

  if (token) {
    request.headers.Authorization = `Bearer ${token}`;
  }

  if (request.body && typeof request.body === "object") {
    request.headers["Content-Type"] = "application/json";
    request.body = JSON.stringify(request.body);
  }

  const response = await fetch(path, request);
  if (!response.ok) {
    const text = await response.text();
    throw new Error(text || response.statusText);
  }

  return response.json();
}

function renderStats(stats = {}) {
  document.getElementById("stat-titles").textContent = stats.titles ?? 0;
  document.getElementById("stat-available").textContent = stats.available_now ?? 0;
  document.getElementById("stat-borrowed").textContent = stats.borrowed_now ?? 0;
  document.getElementById("stat-categories").textContent = stats.categories ?? 0;
}

function renderFeed(payload) {
  feed.textContent = JSON.stringify(
    {
      stats: payload.stats,
      server_time: payload.server_time,
      latest_titles: payload.books.slice(0, 3).map((book) => ({
        title: book.title,
        available: book.available,
        borrowed: book.borrowed,
        updated_at: book.updated_at,
      })),
    },
    null,
    2
  );
}

function makeBorrowersMarkup(book) {
  if (!book.borrowers.length) {
    return '<div class="empty-state">No borrowers for this title right now.</div>';
  }

  return `<div class="borrowers-list">${book.borrowers
    .map(
      (borrower) =>
        `<div class="borrower-chip">${borrower.name} borrowed at ${borrower.borrowed_at}</div>`
    )
    .join("")}</div>`;
}

function renderBooks() {
  const query = searchInput.value.trim().toLowerCase();
  const filteredBooks = booksCache.filter((book) =>
    [book.title, book.author, book.category].some((value) =>
      String(value).toLowerCase().includes(query)
    )
  );

  if (!filteredBooks.length) {
    booksGrid.innerHTML =
      '<div class="empty-state">No books match your current search. Try a different title, author, or category.</div>';
    return;
  }

  booksGrid.innerHTML = filteredBooks
    .map(
      (book) => `
        <article class="book-card">
          <div class="book-title-row">
            <div>
              <h3>${book.title}</h3>
              <div class="book-meta">by ${book.author}<br>Updated ${book.updated_at}</div>
            </div>
            <div class="book-badges">
              <span class="mini-pill category">${book.category}</span>
              <span class="mini-pill available">Available ${book.available}/${book.copies}</span>
              <span class="mini-pill borrowed">Borrowed ${book.borrowed}</span>
            </div>
          </div>

          <div class="inline-editor">
            <input data-edit-title="${book.id}" value="${book.title}">
            <input data-edit-author="${book.id}" value="${book.author}">
            <input data-edit-category="${book.id}" value="${book.category}">
            <input data-edit-copies="${book.id}" type="number" min="${Math.max(book.borrowed, 1)}" value="${book.copies}">
          </div>

          <div class="book-actions">
            <button class="hero-btn small" data-save="${book.id}">Save Changes</button>
            <button class="ghost-btn" data-borrow="${book.id}">Borrow Copy</button>
            <button class="ghost-btn" data-return="${book.id}">Return Copy</button>
            <button class="danger-btn" data-delete="${book.id}">Remove Book</button>
          </div>

          ${makeBorrowersMarkup(book)}
        </article>
      `
    )
    .join("");
}

async function loadLibrary() {
  try {
    const payload = await callLibraryApi("/api/library/books");
    booksCache = payload.books;
    serverTime.textContent = payload.server_time || "--";
    renderStats(payload.stats);
    renderFeed(payload);
    renderBooks();
  } catch (error) {
    feed.textContent = `Error: ${error.message}`;
    booksGrid.innerHTML =
      `<div class="empty-state">${error.message.includes("401") ? "Please sign in on the main dashboard first." : error.message}</div>`;
  }
}

async function addBook(event) {
  event.preventDefault();

  const payload = {
    title: document.getElementById("book-title").value.trim(),
    author: document.getElementById("book-author").value.trim(),
    category: document.getElementById("book-category").value.trim(),
    copies: Number(document.getElementById("book-copies").value),
  };

  try {
    await callLibraryApi("/api/library/books", { method: "POST", body: payload });
    bookForm.reset();
    document.getElementById("book-copies").value = 3;
    await loadLibrary();
  } catch (error) {
    alert(error.message);
  }
}

async function saveBook(bookId) {
  const payload = {
    title: document.querySelector(`[data-edit-title="${bookId}"]`).value.trim(),
    author: document.querySelector(`[data-edit-author="${bookId}"]`).value.trim(),
    category: document.querySelector(`[data-edit-category="${bookId}"]`).value.trim(),
    copies: Number(document.querySelector(`[data-edit-copies="${bookId}"]`).value),
  };

  await callLibraryApi(`/api/library/books/${bookId}`, { method: "PATCH", body: payload });
  await loadLibrary();
}

async function borrowBook(bookId) {
  const borrower = prompt("Borrower name");
  if (!borrower) return;

  await callLibraryApi(`/api/library/books/${bookId}/borrow`, {
    method: "POST",
    body: { borrower },
  });
  await loadLibrary();
}

async function returnBook(bookId) {
  const borrower = prompt("Borrower name to return");
  if (!borrower) return;

  await callLibraryApi(`/api/library/books/${bookId}/return`, {
    method: "POST",
    body: { borrower },
  });
  await loadLibrary();
}

async function deleteBook(bookId) {
  if (!confirm("Remove this book from the library?")) return;

  await callLibraryApi(`/api/library/books/${bookId}`, { method: "DELETE" });
  await loadLibrary();
}

document.getElementById("refresh-library").addEventListener("click", loadLibrary);
searchInput.addEventListener("input", renderBooks);
bookForm.addEventListener("submit", addBook);

booksGrid.addEventListener("click", async (event) => {
  const saveId = event.target.dataset.save;
  const borrowId = event.target.dataset.borrow;
  const returnId = event.target.dataset.return;
  const deleteId = event.target.dataset.delete;

  try {
    if (saveId) await saveBook(saveId);
    if (borrowId) await borrowBook(borrowId);
    if (returnId) await returnBook(returnId);
    if (deleteId) await deleteBook(deleteId);
  } catch (error) {
    alert(error.message);
  }
});

setSessionState();
loadLibrary();
setInterval(loadLibrary, 3000);
