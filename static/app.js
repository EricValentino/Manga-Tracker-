gsap.registerPlugin(ScrollTrigger);

function showTab(tabId) {
  document.querySelectorAll(".tab-content").forEach(tab => {
    tab.style.display = "none";
  });
  document.getElementById(tabId).style.display = "block";
}

let currentSearchResult = null;

async function searchManga() {
  try {
    const query = document.getElementById("searchBox").value;
    const response = await fetch("/search?title=" + query);
    const manga = await response.json();

    currentSearchResult = manga;

    const resultsDiv = document.getElementById("results");
    resultsDiv.innerHTML = `
      <div class="manga-card">
        <p><strong>${manga.title.english || manga.title.romaji}</strong></p>
        <p>${manga.genres.join(", ")}</p>
        <button onclick="saveManga()">Add to my list</button>
      </div>
    `;
  } catch (error) {
    document.getElementById("results").innerHTML = "<p>Search failed. Please try again.</p>";
    console.error(error);
  }
}

async function saveManga() {
  try {
    const manga = currentSearchResult;
    await fetch("/manga", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        title: manga.title.english || manga.title.romaji,
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
    const response = await fetch("/manga");
    const mangaList = await response.json();

    const progressResponse = await fetch("/progress");
    const progressList = await progressResponse.json();

    const listDiv = document.getElementById("myList");
    listDiv.innerHTML = mangaList.map(m => {
      const progress = progressList.find(p => p.manga_id === m.id);
      const currentStatus = progress ? progress.status : "reading";
      const currentChapter = progress ? progress.chapter : "";
      const currentRating = progress ? progress.rating : "";

      return `
        <div class="manga-card">
          <img src="${m.cover_image}" alt="${m.title}">
          <p>${m.title} — ${m.genre}</p>
          <button onclick="deleteManga(${m.id})">Delete</button>

          <div class="progress-form">
            <select id="status-${m.id}">
              <option value="reading" ${currentStatus === "reading" ? "selected" : ""}>Reading</option>
              <option value="completed" ${currentStatus === "completed" ? "selected" : ""}>Completed</option>
              <option value="plan to read" ${currentStatus === "plan to read" ? "selected" : ""}>Plan to Read</option>
            </select>
            <input type="number" id="chapter-${m.id}" placeholder="Chapter" value="${currentChapter}">
            <input type="number" id="rating-${m.id}" placeholder="Rating (1-10)" value="${currentRating}">
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
    await fetch("/manga/" + mangaId, {
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
    const response = await fetch("/recommendations");
    const recommendations = await response.json();

    const recDiv = document.getElementById("recommendations");
    recDiv.innerHTML = recommendations.map(r => `
      <div class="rec-card">
        <img src="${r.cover_image}" alt="${r.title}">
        <p><strong>${r.title}</strong></p>
        <p>${r.genre}</p>
        <p>${r.reason}</p>
      </div>
    `).join("");
  } catch (error) {
    document.getElementById("recommendations").innerHTML = "<p>Couldn't load recommendations. Please try again.</p>";
    console.error(error);
  }
}

async function saveProgress(mangaId, progressId) {
  try {
    const status = document.getElementById("status-" + mangaId).value;
    const chapter = Number(document.getElementById("chapter-" + mangaId).value);
    const rating = Number(document.getElementById("rating-" + mangaId).value);

    const body = {
      chapter: chapter,
      status: status,
      rating: rating,
      manga_id: mangaId
    };

    if (progressId) {
      await fetch("/progress/" + progressId, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body)
      });
    } else {
      await fetch("/progress", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body)
      });
    }

    loadMyList();
  } catch (error) {
    alert("Couldn't save your progress. Please try again.");
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

    const response = await fetch(url);
    const mangaList = await response.json();

    const rowId = "row-" + sort + endpoint + (country || "");

    const rowHtml = `
      <h3>${title}</h3>
      <div class="discover-row" id="${rowId}">
        ${mangaList.map(m => `
          <div class="manga-card" onclick="openDetails(${m.id}, '${mediaType}')">
            <img src="${m.coverImage.large}" alt="${m.title.english || m.title.romaji}">
            <p>${m.title.english || m.title.romaji}</p>
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
    const response = await fetch(`/details?id=${id}&type=${type}`);
    const details = await response.json();

    const progressLabel = type === "MANGA" ? "Chapters" : "Episodes";
    const progressValue = type === "MANGA" ? details.chapters : details.episodes;

    document.getElementById("modalBody").innerHTML = `
      <img src="${details.coverImage.large}" alt="${details.title.english || details.title.romaji}">
      <h2 style="margin-top:0; border:none; padding:0;">${details.title.english || details.title.romaji}</h2>
      <p><strong>Score:</strong> ${details.averageScore ?? "N/A"} &nbsp; <strong>${progressLabel}:</strong> ${progressValue ?? "Ongoing"}</p>
      <p><strong>Genres:</strong> ${details.genres.join(", ")}</p>
      <p>${details.description ? details.description.replace(/<br\s*\/?>/gi, " ") : "No description available."}</p>
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