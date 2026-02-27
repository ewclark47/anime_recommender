const recommendationForm = document.querySelector("#recommendation-form");
const contentPanel = document.querySelector("#content-panel");
const userModePanel = document.querySelector("#user-mode-panel");
const userRecommendButton = document.querySelector("#user-recommend-button");
const titleInput = document.querySelector("#anime-title");
const submitButton = recommendationForm.querySelector("button[type='submit']");
const resultsSection = document.querySelector("#results");
const queryTitle = document.querySelector("#query-title");
const recommendationList = document.querySelector("#recommendation-list");
const scrollLeftButton = document.querySelector("#scroll-left");
const scrollRightButton = document.querySelector("#scroll-right");
const statusMessage = document.querySelector("#status-message");
const modePanel = document.querySelector("#mode-panel");

const recommendTab = document.querySelector("#recommend-tab");
const favoritesTab = document.querySelector("#favorites-tab");
const exploreTab = document.querySelector("#explore-tab");
const tabRecommendButton = document.querySelector("#tab-recommend");
const tabFavoritesButton = document.querySelector("#tab-favorites");
const tabExploreButton = document.querySelector("#tab-explore");

const usernameInput = document.querySelector("#auth-username");
const passwordInput = document.querySelector("#auth-password");
const registerButton = document.querySelector("#register-button");
const loginButton = document.querySelector("#login-button");
const signoutButton = document.querySelector("#signout-button");
const authForm = document.querySelector("#auth-form");
const authSignedIn = document.querySelector("#auth-signed-in");
const signedInLabel = document.querySelector("#signed-in-label");
const authMessage = document.querySelector("#auth-message");

const favoritesControls = document.querySelector("#favorites-controls");
const favoritesLoginNote = document.querySelector("#favorites-login-note");
const favoriteSearchInput = document.querySelector("#favorite-search");
const favoriteSearchButton = document.querySelector("#favorite-search-button");
const favoriteSearchResults = document.querySelector("#favorite-search-results");
const favoritesList = document.querySelector("#favorites-list");
const favoritesScrollLeft = document.querySelector("#favorites-scroll-left");
const favoritesScrollRight = document.querySelector("#favorites-scroll-right");

const topRatedList = document.querySelector("#top-rated-list");
const exploreScrollLeft = document.querySelector("#explore-scroll-left");
const exploreScrollRight = document.querySelector("#explore-scroll-right");
const summaryModal = document.querySelector("#summary-modal");
const summaryModalBackdrop = document.querySelector("#summary-modal-backdrop");
const summaryModalCloseButton = document.querySelector("#summary-modal-close");
const summaryModalTitle = document.querySelector("#summary-modal-title");
const summaryModalSource = document.querySelector("#summary-modal-source");
const summaryModalBody = document.querySelector("#summary-modal-body");

const API_BASE_URL = `${window.location.protocol}//${window.location.hostname}:8000`;
const USER_STORAGE_KEY = "anime_recommender_user";
const summaryCache = new Map();

let currentUser = null;
let activeTab = "recommend";
const RECOMMEND_FETCH_SIZE = 20;
const recommendationState = {
  mode: "content",
  query: "",
};

function setStatus(message, isError = false) {
  statusMessage.textContent = message;
  statusMessage.classList.toggle("error", isError);
}

function setAuthStatus(message, isError = false) {
  authMessage.textContent = message;
  authMessage.classList.toggle("error", isError);
}

function normalizeSummarySource(source) {
  if (source === "mal") {
    return "Source: MyAnimeList";
  }
  if (source === "wikipedia") {
    return "Source: Wikipedia";
  }
  return "Source: unavailable";
}

function closeSummaryModal() {
  summaryModal.classList.add("hidden");
}

async function openSummaryModal(title, animeId) {
  summaryModal.classList.remove("hidden");
  summaryModalTitle.textContent = title;
  summaryModalSource.textContent = "";
  summaryModalBody.classList.remove("error");
  summaryModalBody.textContent = "Loading summary...";

  try {
    const payload = await fetchAnimeSummary(title, animeId);
    summaryModalTitle.textContent = payload.title || title;
    summaryModalSource.textContent = normalizeSummarySource(payload.source);
    summaryModalBody.textContent = payload.summary || "No summary available.";
  } catch (error) {
    summaryModalSource.textContent = "Source: unavailable";
    summaryModalBody.classList.add("error");
    summaryModalBody.textContent = error.message || "Failed to load summary.";
  }
}

function summaryCacheKey(title, animeId) {
  if (animeId !== undefined && animeId !== null) {
    return `id:${animeId}`;
  }
  return `title:${String(title || "").trim().toLowerCase()}`;
}

async function fetchAnimeSummary(title, animeId) {
  const key = summaryCacheKey(title, animeId);
  if (summaryCache.has(key)) {
    return summaryCache.get(key);
  }

  const params = new URLSearchParams();
  params.set("title", title);
  if (animeId !== undefined && animeId !== null) {
    params.set("anime_id", String(animeId));
  }
  const payload = await apiRequest(`/anime/summary?${params.toString()}`);
  summaryCache.set(key, payload);
  return payload;
}

function getMode() {
  const selected = document.querySelector("input[name='mode']:checked");
  return selected ? selected.value : "content";
}

window.setActiveTab = function setActiveTab(tab) {
  activeTab = tab;
  recommendTab.classList.toggle("hidden", tab !== "recommend");
  favoritesTab.classList.toggle("hidden", tab !== "favorites");
  exploreTab.classList.toggle("hidden", tab !== "explore");

  tabRecommendButton.classList.toggle("active", tab === "recommend");
  tabFavoritesButton.classList.toggle("active", tab === "favorites");
  tabExploreButton.classList.toggle("active", tab === "explore");
};

function updateModeVisibility() {
  if (!currentUser) {
    modePanel.classList.add("hidden");
    contentPanel.classList.remove("hidden");
    userModePanel.classList.add("hidden");
    favoritesControls.classList.add("hidden");
    favoritesLoginNote.classList.remove("hidden");
    return;
  }

  modePanel.classList.remove("hidden");
  favoritesControls.classList.remove("hidden");
  favoritesLoginNote.classList.add("hidden");

  if (getMode() === "user") {
    contentPanel.classList.add("hidden");
    userModePanel.classList.remove("hidden");
  } else {
    contentPanel.classList.remove("hidden");
    userModePanel.classList.add("hidden");
  }
}

function setButtonsDisabled(disabled) {
  submitButton.disabled = disabled;
  userRecommendButton.disabled = disabled;
  registerButton.disabled = disabled;
  loginButton.disabled = disabled;
  signoutButton.disabled = disabled;
  favoriteSearchButton.disabled = disabled;
  scrollLeftButton.disabled = disabled;
  scrollRightButton.disabled = disabled;
  if (!disabled) {
    updateRecommendationScrollButtons();
  }
}

function updateRecommendationScrollButtons() {
  updateShelfScrollButtons(recommendationList, scrollLeftButton, scrollRightButton);
}

function updateShelfScrollButtons(container, leftButton, rightButton) {
  const maxScrollLeft = Math.max(0, container.scrollWidth - container.clientWidth);
  const atLeftEdge = container.scrollLeft <= 1;
  const atRightEdge = maxScrollLeft <= 1 || container.scrollLeft >= maxScrollLeft - 1;
  leftButton.disabled = atLeftEdge;
  rightButton.disabled = atRightEdge;
}

function getStoredUser() {
  const raw = window.localStorage.getItem(USER_STORAGE_KEY);
  if (!raw) {
    return null;
  }
  try {
    return JSON.parse(raw);
  } catch {
    return null;
  }
}

function storeUser(user) {
  currentUser = user;
  if (user) {
    window.localStorage.setItem(USER_STORAGE_KEY, JSON.stringify(user));
    authForm.classList.add("hidden");
    authSignedIn.classList.remove("hidden");
    signedInLabel.textContent = `Signed in as ${user.username}`;
    passwordInput.value = "";
  } else {
    window.localStorage.removeItem(USER_STORAGE_KEY);
    authForm.classList.remove("hidden");
    authSignedIn.classList.add("hidden");
    signedInLabel.textContent = "Signed in";
    favoriteSearchResults.innerHTML = "";
    favoritesList.innerHTML = "";
    updateShelfScrollButtons(favoritesList, favoritesScrollLeft, favoritesScrollRight);
    const contentModeRadio = document.querySelector("input[name='mode'][value='content']");
    if (contentModeRadio) {
      contentModeRadio.checked = true;
    }
  }
  updateModeVisibility();
}

async function apiRequest(path, options = {}) {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });

  let payload = null;
  try {
    payload = await response.json();
  } catch {
    payload = null;
  }

  if (!response.ok) {
    let message = "Request failed";
    if (typeof payload?.detail === "string") {
      message = payload.detail;
    } else if (Array.isArray(payload?.detail)) {
      message = payload.detail.map((item) => item?.msg || JSON.stringify(item)).join("; ");
    } else if (payload?.detail) {
      message = JSON.stringify(payload.detail);
    }
    throw new Error(message);
  }

  return payload;
}

function buildCard({ title, score, imageUrl, animeId, actionLabel, onAction }) {
  const card = document.createElement("div");
  card.className = "recommendation-card recommendation-item";

  const poster = document.createElement("div");
  poster.className = "poster-placeholder";
  const fallback = document.createElement("span");
  fallback.className = "poster-fallback";
  fallback.textContent = "Thumbnail";
  poster.appendChild(fallback);

  if (imageUrl) {
    const image = document.createElement("img");
    image.className = "poster-image";
    image.src = imageUrl;
    image.alt = `${title} thumbnail`;
    image.loading = "lazy";
    image.referrerPolicy = "no-referrer";
    image.addEventListener("load", () => {
      fallback.classList.add("hidden");
    });
    image.addEventListener("error", () => {
      image.remove();
      fallback.classList.remove("hidden");
    });
    poster.appendChild(image);
  }

  const meta = document.createElement("div");
  meta.className = "card-meta";

  const titleEl = document.createElement("p");
  titleEl.className = "card-title";
  titleEl.textContent = title;

  meta.appendChild(titleEl);
  if (score !== undefined && score !== null && score !== "") {
    const scoreEl = document.createElement("p");
    scoreEl.className = "card-score";
    scoreEl.textContent = score;
    meta.appendChild(scoreEl);
  }

  const actions = document.createElement("div");
  actions.className = "card-actions";

  if (actionLabel && onAction) {
    const actionButton = document.createElement("button");
    actionButton.className = "card-action";
    actionButton.type = "button";
    actionButton.textContent = actionLabel;
    actionButton.addEventListener("click", onAction);
    actions.appendChild(actionButton);
  }

  const summaryButton = document.createElement("button");
  summaryButton.className = "card-action";
  summaryButton.type = "button";
  summaryButton.textContent = "See summary";

  summaryButton.addEventListener("click", () => openSummaryModal(title, animeId));
  actions.appendChild(summaryButton);

  meta.appendChild(actions);

  card.appendChild(poster);
  card.appendChild(meta);
  return card;
}

function enforceShelfLayout(container) {
  container.classList.add("recommendation-row");
  container.style.display = "grid";
  container.style.gridAutoFlow = "column";
  container.style.gridAutoColumns = "calc((100% - (4 * 0.8rem)) / 5)";
  container.style.overflowX = "auto";
  container.style.overflowY = "hidden";
  container.style.gap = "0.8rem";
}

function renderRecommendationShelf(query, recommendations) {
  queryTitle.textContent = query;
  recommendationList.innerHTML = "";
  enforceShelfLayout(recommendationList);

  recommendations.forEach((entry) => {
    const card = buildCard({
      title: entry.title,
      imageUrl: entry.image_url,
      animeId: entry.anime_id,
    });
    recommendationList.appendChild(card);
  });

  recommendationList.scrollLeft = 0;
  resultsSection.hidden = false;
  updateRecommendationScrollButtons();
}

function renderFavoriteSearchResults(items) {
  favoriteSearchResults.innerHTML = "";
  enforceShelfLayout(favoriteSearchResults);
  items.forEach((item) => {
    const card = buildCard({
      title: item.name,
      score: `ID ${item.id}`,
      imageUrl: item.image_url,
      animeId: item.id,
      actionLabel: "Add",
      onAction: () => addFavorite(item.id),
    });
    favoriteSearchResults.appendChild(card);
  });
}

function renderFavorites(items) {
  favoritesList.innerHTML = "";
  enforceShelfLayout(favoritesList);
  if (!items.length) {
    updateShelfScrollButtons(favoritesList, favoritesScrollLeft, favoritesScrollRight);
    return;
  }

  items.forEach((item) => {
    const card = buildCard({
      title: item.title,
      imageUrl: item.image_url,
      animeId: item.anime_id,
      actionLabel: "Remove",
      onAction: () => removeFavorite(item.anime_id),
    });
    favoritesList.appendChild(card);
  });
  updateShelfScrollButtons(favoritesList, favoritesScrollLeft, favoritesScrollRight);
}

function renderTopRated(items) {
  topRatedList.innerHTML = "";
  enforceShelfLayout(topRatedList);
  items.forEach((item) => {
    const rating = typeof item.rating === "number" ? item.rating.toFixed(2) : "n/a";
    const card = buildCard({
      title: item.name,
      score: `Score ${rating}`,
      imageUrl: item.image_url,
      animeId: item.id,
    });
    topRatedList.appendChild(card);
  });
  updateShelfScrollButtons(topRatedList, exploreScrollLeft, exploreScrollRight);
}

async function refreshFavorites() {
  if (!currentUser) {
    favoritesList.innerHTML = "";
    updateShelfScrollButtons(favoritesList, favoritesScrollLeft, favoritesScrollRight);
    return;
  }
  const payload = await apiRequest(`/users/${currentUser.id}/favorites`);
  renderFavorites(payload.favorites || []);
}

async function loadExplore() {
  try {
    const items = await apiRequest("/anime/top?limit=10");
    renderTopRated(Array.isArray(items) ? items : []);
  } catch {
    topRatedList.innerHTML = "";
    updateShelfScrollButtons(topRatedList, exploreScrollLeft, exploreScrollRight);
  }
}

async function addFavorite(animeId) {
  if (!currentUser) {
    setAuthStatus("Login first to manage favorites.", true);
    return;
  }
  try {
    await apiRequest(`/users/${currentUser.id}/favorites`, {
      method: "POST",
      body: JSON.stringify({ anime_id: animeId }),
    });
    await refreshFavorites();
    setAuthStatus("Favorite added.");
  } catch (error) {
    setAuthStatus(error.message, true);
  }
}

async function removeFavorite(animeId) {
  if (!currentUser) {
    return;
  }
  try {
    await apiRequest(`/users/${currentUser.id}/favorites/${animeId}`, {
      method: "DELETE",
    });
    await refreshFavorites();
    setAuthStatus("Favorite removed.");
  } catch (error) {
    setAuthStatus(error.message, true);
  }
}

async function handleAuth(action) {
  const username = usernameInput.value.trim();
  const password = passwordInput.value;

  if (!username || !password) {
    setAuthStatus("Username and password are required.", true);
    return;
  }

  try {
    const payload = await apiRequest(`/auth/${action}`, {
      method: "POST",
      body: JSON.stringify({ username, password }),
    });
    storeUser(payload.user);
    setAuthStatus(`Logged in as ${payload.user.username}`);
    await refreshFavorites();
  } catch (error) {
    setAuthStatus(error.message, true);
  }
}

async function fetchRecommendationsPage() {
  if (recommendationState.mode === "content") {
    const payload = await apiRequest(
      `/recommend?title=${encodeURIComponent(recommendationState.query)}&limit=${RECOMMEND_FETCH_SIZE}&offset=0`
    );
    const rows = Array.isArray(payload.recommendations) ? payload.recommendations : [];
    if (!rows.length) {
      setStatus("No recommendations found.");
      return;
    }
    renderRecommendationShelf(payload.query_title || recommendationState.query, rows);
    setStatus("");
    return;
  }

  if (!currentUser) {
    setStatus("Login first to use user-similarity recommendations.", true);
    return;
  }

  const payload = await apiRequest(
    `/recommend/user/${currentUser.id}?limit=${RECOMMEND_FETCH_SIZE}&offset=0`
  );
  const rows = Array.isArray(payload.recommendations) ? payload.recommendations : [];
  if (!rows.length) {
    setStatus("No user-similarity recommendations yet. Add more favorites.");
    return;
  }
  renderRecommendationShelf(`User #${currentUser.id}`, rows);
  setStatus("");
}

favoriteSearchButton.addEventListener("click", async () => {
  const q = favoriteSearchInput.value.trim();
  if (!q) {
    return;
  }

  try {
    const items = await apiRequest(`/anime/search?q=${encodeURIComponent(q)}&limit=10`);
    renderFavoriteSearchResults(items || []);
    if (!items?.length) {
      setAuthStatus("No anime found for search.");
    }
  } catch (error) {
    setAuthStatus(error.message, true);
  }
});

registerButton.addEventListener("click", () => handleAuth("register"));
loginButton.addEventListener("click", () => handleAuth("login"));
signoutButton.addEventListener("click", () => {
  storeUser(null);
  setAuthStatus("");
  setStatus("Signed out.");
});

tabRecommendButton.addEventListener("click", () => window.setActiveTab("recommend"));
tabFavoritesButton.addEventListener("click", () => window.setActiveTab("favorites"));
tabExploreButton.addEventListener("click", () => window.setActiveTab("explore"));

document.querySelectorAll("input[name='mode']").forEach((el) => {
  el.addEventListener("change", () => {
    updateModeVisibility();
    setStatus("");
  });
});

recommendationForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  if (getMode() !== "content") {
    return;
  }

  const userTitle = titleInput.value.trim();
  if (!userTitle) {
    setStatus("Enter an anime title for content-based mode.", true);
    return;
  }

  recommendationState.mode = "content";
  recommendationState.query = userTitle;

  setButtonsDisabled(true);
  setStatus("Fetching recommendations...");
  resultsSection.hidden = true;
  recommendationList.innerHTML = "";
  try {
    await fetchRecommendationsPage();
  } catch (error) {
    setStatus(error.message || "Request failed.", true);
  } finally {
    setButtonsDisabled(false);
  }
});

userRecommendButton.addEventListener("click", async () => {
  recommendationState.mode = "user";
  recommendationState.query = "";

  setButtonsDisabled(true);
  setStatus("Fetching recommendations...");
  resultsSection.hidden = true;
  recommendationList.innerHTML = "";
  try {
    await fetchRecommendationsPage();
  } catch (error) {
    setStatus(error.message || "Request failed.", true);
  } finally {
    setButtonsDisabled(false);
  }
});

function scrollRecommendationShelf(delta) {
  const viewportX = window.scrollX;
  const viewportY = window.scrollY;
  recommendationList.scrollBy({ left: delta, behavior: "smooth" });
  requestAnimationFrame(() => {
    window.scrollTo(viewportX, viewportY);
  });
}

scrollLeftButton.addEventListener("mousedown", (event) => event.preventDefault());
scrollRightButton.addEventListener("mousedown", (event) => event.preventDefault());
scrollLeftButton.addEventListener("click", () => scrollRecommendationShelf(-420));
scrollRightButton.addEventListener("click", () => scrollRecommendationShelf(420));
recommendationList.addEventListener("scroll", () => {
  updateRecommendationScrollButtons();
});

favoritesScrollLeft.addEventListener("click", () => favoritesList.scrollBy({ left: -420, behavior: "smooth" }));
favoritesScrollRight.addEventListener("click", () => favoritesList.scrollBy({ left: 420, behavior: "smooth" }));
favoritesList.addEventListener("scroll", () => {
  updateShelfScrollButtons(favoritesList, favoritesScrollLeft, favoritesScrollRight);
});

function scrollExploreShelf(delta) {
  const viewportX = window.scrollX;
  const viewportY = window.scrollY;
  topRatedList.scrollBy({ left: delta, behavior: "smooth" });
  requestAnimationFrame(() => {
    window.scrollTo(viewportX, viewportY);
  });
}

exploreScrollLeft.addEventListener("mousedown", (event) => event.preventDefault());
exploreScrollRight.addEventListener("mousedown", (event) => event.preventDefault());
exploreScrollLeft.addEventListener("click", () => scrollExploreShelf(-420));
exploreScrollRight.addEventListener("click", () => scrollExploreShelf(420));
topRatedList.addEventListener("scroll", () => {
  updateShelfScrollButtons(topRatedList, exploreScrollLeft, exploreScrollRight);
});
window.addEventListener("resize", () => {
  updateRecommendationScrollButtons();
  updateShelfScrollButtons(favoritesList, favoritesScrollLeft, favoritesScrollRight);
  updateShelfScrollButtons(topRatedList, exploreScrollLeft, exploreScrollRight);
});

function initialize() {
  window.setActiveTab("recommend");
  updateRecommendationScrollButtons();
  updateShelfScrollButtons(favoritesList, favoritesScrollLeft, favoritesScrollRight);
  updateShelfScrollButtons(topRatedList, exploreScrollLeft, exploreScrollRight);
  modePanel.classList.add("hidden");
  authForm.classList.remove("hidden");
  authSignedIn.classList.add("hidden");

  const user = getStoredUser();
  if (user) {
    storeUser(user);
    usernameInput.value = user.username;
    setAuthStatus(`Logged in as ${user.username}`);
    refreshFavorites().catch(() => {
      setAuthStatus("Stored session invalid. Please log in again.", true);
      storeUser(null);
    });
  } else {
    updateModeVisibility();
  }

  loadExplore();
}

summaryModalCloseButton.addEventListener("click", closeSummaryModal);
summaryModalBackdrop.addEventListener("click", closeSummaryModal);
window.addEventListener("keydown", (event) => {
  if (event.key === "Escape" && !summaryModal.classList.contains("hidden")) {
    closeSummaryModal();
  }
});

initialize();
