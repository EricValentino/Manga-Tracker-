gsap.registerPlugin(ScrollTrigger);

// ---------- Helpers ----------

// Escape text before interpolating it into HTML. Titles, genres and AI-generated
// reasons come from external services, so they must never be injected as markup.
function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>"']/g, ch => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"
  })[ch]);
}

// AniList descriptions contain HTML. Parse it inertly and keep only the text.
function htmlToText(html) {
  const doc = new DOMParser().parseFromString(String(html ?? "").replace(/<br\s*\/?>/gi, " "), "text/html");
  return doc.body.textContent || "";
}

// fetch() only rejects on network errors; treat HTTP errors as failures too.
async function fetchJson(url, options) {
  const response = await fetch(url, options);
  const body = await response.json().catch(() => null);
  if (!response.ok) {
    const error = new Error((body && body.detail) || `Request failed (${response.status})`);
    error.status = response.status;
    throw error;
  }
  return body;
}

function displayTitle(media) {
  return media.title.english || media.title.romaji;
}

function showTab(tabId) {
  document.querySelectorAll(".tab-content").forEach(tab => {
    tab.style.display = "none";
  });
  document.getElementById(tabId).style.display = "block";
}

let currentSearchResult = null;

async function searchManga() {
  try {
    const query = document.getElementById("searchBox").value.trim();
    if (!query) return;
    const manga = await fetchJson("/search?title=" + encodeURIComponent(query));

    currentSearchResult = manga;

    const resultsDiv = document.getElementById("results");
    resultsDiv.innerHTML = `
      <div class="manga-card">
        <p><strong>${escapeHtml(displayTitle(manga))}</strong></p>
        <p>${escapeHtml(manga.genres.join(", "))}</p>
        <button onclick="saveManga()">Add to my list</button>
      </div>
    `;
  } catch (error) {
    const message = error.status === 404 ? "No manga found with that title." : "Search failed. Please try again.";
    document.getElementById("results").innerHTML = `<p>${message}</p>`;
    console.error(error);
  }
}

async function saveManga() {
  try {
    const manga = currentSearchResult;
    await fetchJson("/manga", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        title: displayTitle(manga),
        genre: manga.genres.join(", "),
        total_chapters: manga.chapters,
        cover_image: manga.coverImage?.large,
        average_score: manga.averageScore
      })
    });
    loadMyList();
  } catch (error) {
    alert("Couldn't save this manga. Please try again.");
    console.error(error);
  }
}

async function loadMyList() {
  try {
    const [mangaList, progressList] = await Promise.all([
      fetchJson("/manga"),
      fetchJson("/progress")
    ]);

    const listDiv = document.getElementById("myList");
    listDiv.innerHTML = mangaList.map(m => {
      const progress = progressList.find(p => p.manga_id === m.id);
      const currentStatus = progress ? progress.status : "reading";
      const currentChapter = progress ? progress.chapter : "";
      const currentRating = progress && progress.rating != null ? progress.rating : "";

      return `
        <div class="manga-card">
          <img src="${escapeHtml(m.cover_image)}" alt="${escapeHtml(m.title)}">
          <p>${escapeHtml(m.title)} — ${escapeHtml(m.genre)}</p>
          <button onclick="deleteManga(${m.id})">Delete</button>

          <div class="progress-form">
            <select id="status-${m.id}">
              <option value="reading" ${currentStatus === "reading" ? "selected" : ""}>Reading</option>
              <option value="completed" ${currentStatus === "completed" ? "selected" : ""}>Completed</option>
              <option value="plan to read" ${currentStatus === "plan to read" ? "selected" : ""}>Plan to Read</option>
            </select>
            <input type="number" min="0" id="chapter-${m.id}" placeholder="Chapter" value="${currentChapter}">
            <input type="number" min="1" max="10" id="rating-${m.id}" placeholder="Rating (1-10)" value="${currentRating}">
            <button onclick="saveProgress(${m.id}, ${progress ? progress.id : null})">Save Progress</button>
          </div>
        </div>
      `;
    }).join("");

    gsap.from(".manga-card", { opacity: 0, y: 20, duration: 0.5, stagger: 0.1 });
  } catch (error) {
    document.getElementById("myList").innerHTML = "<p>Couldn't load your list. Please refresh.</p>";
    console.error(error);
  }
}

async function deleteManga(mangaId) {
  try {
    await fetchJson("/manga/" + mangaId, {
      method: "DELETE"
    });
    loadMyList();
  } catch (error) {
    alert("Couldn't delete this manga. Please try again.");
    console.error(error);
  }
}

async function getRecommendations() {
  try {
    const recommendations = await fetchJson("/recommendations");

    const recDiv = document.getElementById("recommendations");
    recDiv.innerHTML = recommendations.map(r => `
      <div class="rec-card">
        ${r.cover_image ? `<img src="${escapeHtml(r.cover_image)}" alt="${escapeHtml(r.title)}">` : ""}
        <p><strong>${escapeHtml(r.title)}</strong></p>
        <p>${escapeHtml(r.genre)}</p>
        <p>${escapeHtml(r.reason)}</p>
      </div>
    `).join("");
  } catch (error) {
    const message = error.status === 503
      ? "Recommendations are unavailable: the server has no OpenAI API key configured."
      : "Couldn't load recommendations. Please try again.";
    document.getElementById("recommendations").innerHTML = `<p>${message}</p>`;
    console.error(error);
  }
}

async function saveProgress(mangaId, progressId) {
  try {
    const status = document.getElementById("status-" + mangaId).value;
    const chapter = Number(document.getElementById("chapter-" + mangaId).value) || 0;
    const ratingRaw = document.getElementById("rating-" + mangaId).value;
    // An empty rating means "not rated" (null), not zero.
    const rating = ratingRaw === "" ? null : Number(ratingRaw);

    const body = {
      chapter: chapter,
      status: status,
      rating: rating,
      manga_id: mangaId
    };

    if (progressId) {
      await fetchJson("/progress/" + progressId, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body)
      });
    } else {
      await fetchJson("/progress", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body)
      });
    }

    loadMyList();
  } catch (error) {
    alert(error.status === 422
      ? "Please enter a chapter of 0 or more and a rating from 1 to 10."
      : "Couldn't save your progress. Please try again.");
    console.error(error);
  }
}

async function loadDiscoverRow(title, sort, targetDivId, endpoint = "/discover", country = null) {
  try {
    const mediaType = endpoint === "/discover-anime" ? "ANIME" : "MANGA";

    let url = endpoint + "?sort=" + sort;
    if (country) {
      url += "&country=" + country;
    }

    const mangaList = await fetchJson(url);

    const rowId = "row-" + sort + endpoint + (country || "");

    const rowHtml = `
      <h3>${escapeHtml(title)}</h3>
      <div class="discover-row" id="${rowId}">
        ${mangaList.map(m => `
          <div class="manga-card" onclick="openDetails(${Number(m.id)}, '${mediaType}')">
            <img src="${escapeHtml(m.coverImage?.large)}" alt="${escapeHtml(displayTitle(m))}">
            <p>${escapeHtml(displayTitle(m))}</p>
          </div>
        `).join("")}
      </div>
    `;

    document.getElementById(targetDivId).insertAdjacentHTML("beforeend", rowHtml);

    gsap.from(`#${rowId} .manga-card`, {
      opacity: 0,
      x: 30,
      duration: 0.5,
      stagger: 0.05
    });
  } catch (error) {
    console.error(error);
  }
}

async function openDetails(id, type) {
  try {
    const details = await fetchJson(`/details?id=${encodeURIComponent(id)}&type=${encodeURIComponent(type)}`);

    const progressLabel = type === "MANGA" ? "Chapters" : "Episodes";
    const progressValue = type === "MANGA" ? details.chapters : details.episodes;

    document.getElementById("modalBody").innerHTML = `
      <img src="${escapeHtml(details.coverImage?.large)}" alt="${escapeHtml(displayTitle(details))}">
      <h2 style="margin-top:0; border:none; padding:0;">${escapeHtml(displayTitle(details))}</h2>
      <p><strong>Score:</strong> ${escapeHtml(details.averageScore ?? "N/A")} &nbsp; <strong>${progressLabel}:</strong> ${escapeHtml(progressValue ?? "Ongoing")}</p>
      <p><strong>Genres:</strong> ${escapeHtml(details.genres.join(", "))}</p>
      <p>${details.description ? escapeHtml(htmlToText(details.description)) : "No description available."}</p>
    `;

    document.getElementById("detailModal").classList.add("active");
  } catch (error) {
    console.error(error);
  }
}

function closeModal(event) {
  if (event.target.id === "detailModal" || event.target.classList.contains("modal-close")) {
    document.getElementById("detailModal").classList.remove("active");
  }
}

function loadAllDiscoverRows() {
  loadDiscoverRow("Trending Manga", "TRENDING_DESC", "discoverSections");
  setTimeout(() => loadDiscoverRow("Top Ranked Manga", "SCORE_DESC", "discoverSections"), 500);
  setTimeout(() => loadDiscoverRow("Popular Manga", "POPULARITY_DESC", "discoverSections"), 1000);
  setTimeout(() => loadDiscoverRow("Popular Manhwa", "POPULARITY_DESC", "discoverSections", "/discover", "KR"), 1500);
  setTimeout(() => loadDiscoverRow("Trending Anime", "TRENDING_DESC", "animeDiscoverSections", "/discover-anime"), 2000);
  setTimeout(() => loadDiscoverRow("Top Ranked Anime", "SCORE_DESC", "animeDiscoverSections", "/discover-anime"), 2500);
  setTimeout(() => loadDiscoverRow("Popular Anime", "POPULARITY_DESC", "animeDiscoverSections", "/discover-anime"), 3000);
}

const introTimeline = gsap.timeline();
introTimeline
  .from("h1", { opacity: 0, y: -20, duration: 0.6 })
  .from("#searchBox, button", { opacity: 0, y: -10, duration: 0.4, stagger: 0.05 }, "-=0.3");

loadAllDiscoverRows();
showTab("mangaTab");
loadMyList();